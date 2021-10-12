# Copyright 2015-2021 Laszlo Attila Toth
# Distributed under the terms of the GNU Lesser General Public License v3

import argparse
import os.path
import re
import typing
from unittest.mock import patch

import dewi_core.testcase
from dewi_core.application import Application
from dewi_core.command import Command
from dewi_core.context_managers import redirect_outputs
from dewi_core.tests.common import test_env, DATA_DIR


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


@patch.dict(os.environ, {}, clear=True)
class ApplicationTest(InvokableAppWithCommandTest):

    @patch.dict(os.environ, {}, clear=True)
    def set_up(self):
        self.application = Application(self.APP_NAME)
        self.application.add_command_class(FakeCommand)

    def test_help_option(self):
        self.assert_help_option()

    def test_that_a_command_name_is_requiredto_run(self):
        self.assert_list_command()

    def test_list_command(self):
        self.assert_list_command()

    def test_list_all_command(self):
        self.assert_list_all_command()

    def test_command_run_method_is_called(self):
        self.assert_fake_command_run(['fake'])

    def test_command_run_method_exception_is_handled(self):
        redirect = self._invoke_application_redirected(
            ['fake', 'ERROR'],
            expected_exit_value=1)
        self.assert_equal('', redirect.stdout.getvalue())
        self.assert_in('Fake Command Error', redirect.stderr.getvalue())

    def test_command_run_method_exception_is_handled_in_debug_mode(self):
        redirect = self._invoke_application_redirected(
            ['-d', 'fake', 'ERROR'],
            expected_exit_value=1)

        self.assert_in('Exception occurred:\n', redirect.stdout.getvalue())
        self.assert_in(' Type: RuntimeError\n', redirect.stdout.getvalue())
        self.assert_in(' Message: Fake Command Error\n', redirect.stdout.getvalue())
        self.assert_in('/dewi_core/tests/test_application.py:XX in run\n',
                       re.sub(r'dewi_core/tests/test_application.py:([0-9]+)', 'dewi_core/tests/test_application.py:XX',
                              redirect.stdout.getvalue()))
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
            ['unknown-name'],
            expected_exit_value=1)
        self.assert_equal('', redirect.stderr.getvalue())

        output = redirect.stdout.getvalue()
        self.assert_in("ERROR: The command 'unknown-name' is not known.\n", output)
        self.assert_in("Similar names - firstly based on command name length:\n", output)
        self.assert_not_in(" list-all ", output)
        self.assert_in(" not-so-fake ", output)

    def test_run_help_of_command(self):
        redirect = self._invoke_application_redirected(
            ['fake', '-h'],
            expected_exit_value=0)
        self.assert_in(f'{self.APP_NAME} fake [-h]', redirect.stdout.getvalue())
        self.assert_equal('', redirect.stderr.getvalue())


@patch.dict(os.environ, {}, clear=True)
class SingleCommandApplicationTest(InvokableAppWithCommandTest):

    @patch.dict(os.environ, {}, clear=True)
    def set_up(self):
        self.application = Application(self.APP_NAME, FakeCommand)

    def test_help_option(self):
        self.assert_help_option(suffix='[-h] [--cwd CWD] [--wait]')

    def test_command_run_method_is_called(self):
        self.assert_fake_command_run([])


@patch.dict(os.environ, {}, clear=True)
class ApplicationWithEnvsTest(InvokableAppWithCommandTest):

    @patch.dict(os.environ, {}, clear=True)
    def set_up(self):
        test_env.reset_entries()
        self.application = Application(InvokableApplicationTest.APP_NAME, FakeCommand)

    def _register_dir(self, directory: str):
        self.application.register_config_directory(os.path.join(DATA_DIR, 'cfgdirs', directory))

    def _register_dirs(self):
        self._register_dir('dir1')
        self._register_dir('dir2')
        self._register_dir('dir3')

    def _asssert_env_after_run(self, expected_list: typing.List[str], env_name: str = None):
        self._invoke_application(['-e', env_name or 'foobar', 'fake'], expected_exit_value=42)
        self._asssert_env(expected_list)

    def _asssert_env(self, expected_list: typing.List[str]):
        self.assert_equal(expected_list, test_env.entries, 'Mismatching list of env strings in test_env')

    def test_all_env_with_name_foobar(self):
        self._register_dirs()
        self._asssert_env_after_run(['dir1-common', 'dir2-common', 'dir2-foobar', 'dir3-foobar'])

    def test_all_env_with_name_test(self):
        self._register_dirs()
        self._asssert_env_after_run(['dir1-common', 'dir2-common', 'dir2-test'], 'test')

    def test_all_env_with_default_env(self):
        self.assert_equal('development', self.application._env_config.current_env)
        self._register_dirs()
        self._invoke_application(['fake'], expected_exit_value=42)
        self.assert_equal('development', self.application._env_config.current_env)
        self._asssert_env(['dir1-common', 'dir2-common', 'dir2-dev'])

    @patch.dict(os.environ, {'DEWI_ENV': 'production'}, )
    def test_all_env_with_env_var(self):
        self.application = Application(InvokableApplicationTest.APP_NAME, FakeCommand)
        self.assert_equal('production', self.application._env_config.current_env)
        self._register_dirs()
        self._invoke_application(['fake'], expected_exit_value=42)
        self.assert_equal('production', self.application._env_config.current_env)
        self._asssert_env(['dir1-common', 'dir2-common', 'dir2-prod'])
