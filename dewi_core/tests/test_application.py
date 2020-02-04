# Copyright 2015-2018 Laszlo Attila Toth
# Distributed under the terms of the GNU Lesser General Public License v3

import argparse
import typing

import dewi_core.testcase
from dewi_core.application import Application, SimpleApplication, SinglePluginApplication, SingleCommandApplication
from dewi_core.command import Command
from dewi_core.commandplugin import CommandPlugin
from dewi_core.context_managers import redirect_outputs
from dewi_core.loader.context import Context
from dewi_core.loader.loader import PluginLoader


class FakeCommand(Command):
    name = 'fake'
    aliases = ['not-so-fake']
    description = 'A fake command for tests'
    arguments = None

    def __init__(self):
        FakeCommand.arguments = None

    def register_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument('arguments', nargs='*')

    def run(self, args: argparse.Namespace) -> int:
        arguments = args.arguments

        if arguments and arguments[0] == 'ERROR':
            raise RuntimeError("Fake Command Error")

        FakeCommand.arguments = list(arguments)
        return 42


class FakePluginLoader(PluginLoader):
    def __init__(self, command):
        # super() is not wanted to call here, its interface is overridden
        self.loaded = []
        self.command = command

    def load(self, plugins):
        context = Context()

        self.loaded.extend(plugins)

        context.commands.register_class(self.command)

        return context


FakePlugin = CommandPlugin.create(FakeCommand)
FakePlugin.name_str_ = f'{__name__}.FakePlugin'


class InvokableApplicationTest(dewi_core.testcase.TestCase):
    APP_NAME = 'myprogram'
    UPPER_APP_NAME = 'Myprogram'

    def _invoke_application(self, args, *, expected_exit_value=1):
        with self.assert_raises(SystemExit) as context:
            self.application.run(args)

        self.assert_equal(expected_exit_value, context.exception.code)

    def _invoke_application_redirected(self, *args, **kwargs):
        with redirect_outputs() as redirection:
            self._invoke_application(*args, **kwargs)

        return redirection

    def assert_fake_command_run(self, prefix_args: typing.Optional[typing.List[str]] = None):
        redirect = self._invoke_application_redirected(
            (prefix_args or []) + ['something', 'another'],
            expected_exit_value=42)
        self.assert_equal('', redirect.stdout.getvalue())
        self.assert_equal('', redirect.stderr.getvalue())
        self.assert_equal(['something', 'another'], FakeCommand.arguments)


class InvokableAppWithCommandTest(InvokableApplicationTest):
    def assert_help_option(self, *, suffix: typing.Optional[str] = None):
        suffix = suffix or '[options] [command [command-args]]'
        redirect = self._invoke_application_redirected(['-h'], expected_exit_value=0)
        self.assert_in(f'{self.APP_NAME} {suffix}', redirect.stdout.getvalue())
        self.assert_equal('', redirect.stderr.getvalue())

    def assert_list_command(self, *, include_fake_command: bool = True):
        redirect = self._invoke_application_redirected(['list'], expected_exit_value=None)
        self.assert_list_command_(redirect, include_fake_command=include_fake_command)

    def assert_no_args(self, *, include_fake_command: bool = True):
        redirect = self._invoke_application_redirected([], expected_exit_value=None)
        self.assert_list_command_(redirect, include_fake_command=include_fake_command)

    def assert_list_command_(self, redirect, *, include_fake_command: bool = True):
        self.assert_equal('', redirect.stderr.getvalue())
        self.assert_in(f'Available {self.UPPER_APP_NAME} Commands.\n', redirect.stdout.getvalue())
        self.assert_in('\n  list ', redirect.stdout.getvalue())
        self.assert_in('\n  list-all ', redirect.stdout.getvalue())
        (self.assert_in if include_fake_command else self.assert_not_in)('\n  fake ', redirect.stdout.getvalue())
        self.assert_not_in('\n  not-so-fake ', redirect.stdout.getvalue())

    def assert_list_all_command(self, *, include_fake_command: bool = True):
        redirect = self._invoke_application_redirected(['list-all'], expected_exit_value=None)
        assert_fake_in = (self.assert_in if include_fake_command else self.assert_not_in)
        self.assert_equal('', redirect.stderr.getvalue())
        self.assert_in(f'Available {self.UPPER_APP_NAME} Commands.\n', redirect.stdout.getvalue())
        self.assert_in('\n  list ', redirect.stdout.getvalue())
        self.assert_in('\n  list-all ', redirect.stdout.getvalue())
        assert_fake_in('\n  fake ', redirect.stdout.getvalue())
        assert_fake_in('\n  not-so-fake ', redirect.stdout.getvalue())


class TestApplication(InvokableAppWithCommandTest):
    def set_up(self):
        self.command = FakeCommand()
        self.loader = FakePluginLoader(FakeCommand)
        self.application = Application(self.loader, self.APP_NAME, fallback_to_plugin_name='fallback')

    def test_help_option(self):
        self.assert_help_option()
        self.assert_equal(set(), set(self.loader.loaded))

    def test_loading_plugins_requires_a_command_to_run(self):
        self.assert_list_command()
        self.assert_equal({'fallback'}, set(self.loader.loaded))

    def test_list_command(self):
        self.assert_list_command()
        self.assert_equal({'fallback'}, set(self.loader.loaded))

    def test_list_all_command(self):
        self.assert_list_all_command()
        self.assert_equal({'fallback'}, set(self.loader.loaded))

    def test_command_run_method_is_called(self):
        self.assert_fake_command_run(['-p', 'test', 'fake'])
        self.assert_equal({'test'}, set(self.loader.loaded))

    def test_command_run_method_exception_is_handled(self):
        redirect = self._invoke_application_redirected(
            ['-p', 'test', 'fake', 'ERROR'],
            expected_exit_value=1)
        self.assert_equal('', redirect.stdout.getvalue())
        self.assert_in('Fake Command Error', redirect.stderr.getvalue())

    def test_command_run_method_exception_is_handled_in_debug_mode(self):
        redirect = self._invoke_application_redirected(
            ['-p', 'test', '-d', 'fake', 'ERROR'],
            expected_exit_value=1)

        self.assert_in('An exception occurred:\n', redirect.stdout.getvalue())
        self.assert_in(' Type: RuntimeError\n', redirect.stdout.getvalue())
        self.assert_in(' Message: Fake Command Error\n', redirect.stdout.getvalue())
        self.assert_in('/dewi_core/tests/test_application.py:32 in run\n', redirect.stdout.getvalue())
        self.assert_in('Fake Command Error', redirect.stderr.getvalue())

    def test_unknown_command(self):
        """
        Test that the output is something like the following,
        without checking the exact space character count between the command name (fake)
        and the description (- A fake command for tests).

        ---8<---
        ERROR: The command 'unknown-name' is not known.

        Available commands and aliases:
        fake                             - A fake command for tests
        --->8---
        """

        redirect = self._invoke_application_redirected(
            ['-p', 'test', 'unknown-name'],
            expected_exit_value=1)
        self.assert_equal('', redirect.stderr.getvalue())

        output = redirect.stdout.getvalue()
        self.assert_in("ERROR: The command 'unknown-name' is not known.\n", output)
        self.assert_in("Similar names - firstly based on command name length:\n", output)
        self.assert_not_in(" list-all ", output)
        self.assert_in(" not-so-fake ", output)

    def test_run_help_of_command(self):
        redirect = self._invoke_application_redirected(
            ['-p', 'test', 'fake', '-h'],
            expected_exit_value=0)
        self.assert_in(f'{self.APP_NAME} fake [-h]', redirect.stdout.getvalue())
        self.assert_equal('', redirect.stderr.getvalue())
        self.assert_equal({'test'}, set(self.loader.loaded))


class TestApplicationWithDefaultFallbackPlugin(InvokableAppWithCommandTest):
    def set_up(self):
        self.command = FakeCommand()
        self.loader = FakePluginLoader(FakeCommand)
        self.application = Application(self.loader, self.APP_NAME)

    def test_loading_plugins_requires_a_command_to_run(self):
        self.assert_list_command()
        self.assert_equal({'dewi_core.application.EmptyPlugin'}, set(self.loader.loaded))

    def test_list_command(self):
        self.assert_list_command()
        self.assert_equal({'dewi_core.application.EmptyPlugin'}, set(self.loader.loaded))

    def test_list_all_command(self):
        self.assert_list_all_command()
        self.assert_equal({'dewi_core.application.EmptyPlugin'}, set(self.loader.loaded))


class TestSinglePluginApplication(InvokableAppWithCommandTest):
    def set_up(self):
        self.application = SinglePluginApplication(self.APP_NAME, FakePlugin.name_str_)

    def test_help_option(self):
        self.assert_help_option()

    def test_run_no_args_is_the_list_command(self):
        self.assert_no_args()

    def test_list_command(self):
        self.assert_list_command()

    def test_list_all_command(self):
        self.assert_list_all_command()

    def test_command_run_method_is_called(self):
        self.assert_fake_command_run(['fake'])


class TestSingleCommndApplication(InvokableAppWithCommandTest):
    def set_up(self):
        self.application = SingleCommandApplication(self.APP_NAME, FakeCommand)

    def test_help_option(self):
        self.assert_help_option(suffix='[-h] [arguments [arguments ...]]')

    def test_command_run_method_is_called(self):
        self.assert_fake_command_run([])
