# Copyright 2015-2022 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

"""
Tests of the shared-config sample, and of the plumbing it depends on.

The plumbing is the point: a plugin's load() may register shared state in the
Context, and the commands read it from ctx.plugin_context afterwards. The
context used to be created by the loader and dropped by Application, so
nothing a plugin registered could ever be read.
"""

import io
import json
import os.path
import tempfile
from contextlib import redirect_stdout

import dewi_core.testcase
from dewi_core.appcontext import ApplicationContext
from dewi_core.commandregistry import CommandRegistry
from dewi_core.commands.sharedconfig import (CONTEXT_ENTRY, SharedConfig,
                                             SharedConfigCommand, SharedConfigPlugin)
from dewi_core.config_env import ConfigDirRegistry
from dewi_core.loader.context import Context, ContextEntryAlreadyRegistered
from dewi_core.loader.loader import PluginLoader


class _WithConfigFile(dewi_core.testcase.TestCase):
    def set_up(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = self._tmpdir.name
        self.set_up_case()

    def set_up_case(self):
        pass

    def tear_down(self):
        self._tmpdir.cleanup()

    def config_file(self, content: dict) -> str:
        path = os.path.join(self.root, 'config.json')
        with open(path, 'wt', encoding='UTF-8') as f:
            json.dump(content, f)
        return path

    def missing_file(self) -> str:
        return os.path.join(self.root, 'not-there.json')


class SharedConfigTest(_WithConfigFile):
    """
    The accessor: load once, reload when the file changes.

    Registering the loaded value instead would be a global variable -- right
    until the process outlives the file, which is what an interactive session
    does.
    """

    def test_that_a_missing_file_gives_the_defaults(self):
        self.assert_equal('<defaults>', SharedConfig(self.missing_file()).get()['source'])

    def test_that_an_existing_file_is_read(self):
        shared = SharedConfig(self.config_file({'greeting': 'hi there'}))

        self.assert_equal('hi there', shared.get()['greeting'])

    def test_that_the_source_names_the_file(self):
        path = self.config_file({'greeting': 'hi'})

        self.assert_equal(path, SharedConfig(path).get()['source'])

    def test_that_a_tilde_is_expanded(self):
        self.assert_equal('<defaults>', SharedConfig('~/nowhere-at-all.json').get()['source'])

    def test_that_nothing_is_read_before_the_first_get(self):
        """A command that never asks pays nothing."""
        shared = SharedConfig(self.config_file({'greeting': 'hi'}))

        self.assert_equal(0, shared.load_count)

    def test_that_the_file_is_read_once_for_repeated_gets(self):
        shared = SharedConfig(self.config_file({'greeting': 'hi'}))
        for _ in range(5):
            shared.get()

        self.assert_equal(1, shared.load_count)

    def test_that_a_changed_file_is_reloaded(self):
        """The interactive case: somebody else edits the file mid-session."""
        path = self.config_file({'greeting': 'first'})
        shared = SharedConfig(path)
        self.assert_equal('first', shared.get()['greeting'])

        os.utime(path, (0, 0))                      # a different timestamp
        self.config_file({'greeting': 'second'})

        self.assert_equal('second', shared.get()['greeting'])

    def test_that_a_reload_counts_as_a_second_read(self):
        path = self.config_file({'greeting': 'first'})
        shared = SharedConfig(path)
        shared.get()
        os.utime(path, (0, 0))
        self.config_file({'greeting': 'second'})
        shared.get()

        self.assert_equal(2, shared.load_count)

    def test_that_an_unchanged_file_is_not_reloaded(self):
        shared = SharedConfig(self.config_file({'greeting': 'hi'}))
        shared.get()
        shared.get()

        self.assert_equal(1, shared.load_count)

    def test_that_invalidate_forces_a_reread(self):
        shared = SharedConfig(self.config_file({'greeting': 'hi'}))
        shared.get()
        shared.invalidate()
        shared.get()

        self.assert_equal(2, shared.load_count)

    def test_that_a_file_appearing_later_is_picked_up(self):
        path = self.missing_file()
        shared = SharedConfig(path)
        self.assert_equal('<defaults>', shared.get()['source'])

        with open(path, 'wt', encoding='UTF-8') as f:
            json.dump({'greeting': 'now here'}, f)

        self.assert_equal('now here', shared.get()['greeting'])


class PluginTest(_WithConfigFile):
    def load_plugin(self, config_file: str | None = None) -> Context:
        SharedConfigPlugin.config_file = config_file or self.missing_file()
        try:
            registry = CommandRegistry()
            loader = PluginLoader(registry, ConfigDirRegistry([]))
            return loader.load(['dewi_core.commands.sharedconfig.SharedConfigPlugin'])
        finally:
            SharedConfigPlugin.config_file = '~/.config/dewi/shared-config.json'

    def test_that_the_config_is_registered(self):
        self.assert_in(CONTEXT_ENTRY, self.load_plugin())

    def test_that_an_accessor_is_registered(self):
        self.assert_is_instance(self.load_plugin()[CONTEXT_ENTRY], SharedConfig)

    def test_that_the_accessor_reads_the_file(self):
        path = self.config_file({'greeting': 'from the file'})

        context = self.load_plugin(path)

        self.assert_equal('from the file', context[CONTEXT_ENTRY].get()['greeting'])

    def test_that_loading_the_plugin_reads_nothing(self):
        """Loading a plugin must not cost a file read nobody asked for."""
        context = self.load_plugin(self.config_file({'greeting': 'hi'}))

        self.assert_equal(0, context[CONTEXT_ENTRY].load_count)

    def test_that_the_command_is_registered(self):
        context = self.load_plugin()

        self.assert_in('shared-config', context.commands.get_command_names())

    def test_that_the_alias_is_registered(self):
        context = self.load_plugin()

        self.assert_in('shared-cfg', context.commands.get_command_names())

    def test_that_the_commands_share_one_accessor(self):
        """One read serves every command, which is the point of the Context."""
        context = self.load_plugin(self.config_file({'greeting': 'hi'}))
        shared = context[CONTEXT_ENTRY]

        shared.get()
        shared.get()

        self.assert_equal(1, shared.load_count)


class ContextSharingTest(dewi_core.testcase.TestCase):
    """The loader can load into a context the caller owns, so calls accumulate."""

    def loader(self) -> PluginLoader:
        return PluginLoader(CommandRegistry(), ConfigDirRegistry([]))

    def test_that_a_context_is_made_when_none_is_given(self):
        self.assert_is_not_none(self.loader().load([]))

    def test_that_a_given_context_is_used(self):
        context = Context(CommandRegistry(), ConfigDirRegistry([]))

        self.assert_is(context, self.loader().load([], context))

    def test_that_entries_survive_a_second_load(self):
        context = self.loader().load([])
        context.register('first', 1)

        again = self.loader().load([], context)

        self.assert_equal(1, again['first'])

    def test_that_a_name_cannot_be_registered_twice(self):
        context = self.loader().load([])
        context.register('thing', 1)

        with self.assert_raises(ContextEntryAlreadyRegistered):
            context.register('thing', 2)


class CommandTest(_WithConfigFile):
    def context_with(self, config: dict | None) -> ApplicationContext:
        ctx = ApplicationContext()
        ctx.args.key = None
        if config is not None:
            ctx.plugin_context = Context(CommandRegistry(), ConfigDirRegistry([]))
            ctx.plugin_context.register(CONTEXT_ENTRY,
                                        SharedConfig(self.config_file(config)))
        return ctx

    def run_command(self, ctx) -> tuple[int | None, str]:
        output = io.StringIO()
        with redirect_stdout(output):
            result = SharedConfigCommand().run(ctx)
        return result, output.getvalue()

    def test_that_every_entry_is_printed(self):
        _result, out = self.run_command(self.context_with({'a': 1, 'b': 2}))

        self.assert_in('a: 1', out)
        self.assert_in('b: 2', out)

    def test_that_the_entries_are_sorted(self):
        _result, out = self.run_command(self.context_with({'b': 2, 'a': 1}))

        self.assert_less(out.index('a: 1'), out.index('b: 2'))

    def test_that_it_succeeds(self):
        result, _out = self.run_command(self.context_with({'a': 1}))

        self.assert_equal(0, result)

    def test_that_one_entry_can_be_selected(self):
        ctx = self.context_with({'a': 1, 'b': 2})
        ctx.args.key = 'b'

        _result, out = self.run_command(ctx)

        self.assert_equal('2\n', out)

    def test_that_an_unknown_entry_is_refused(self):
        ctx = self.context_with({'a': 1})
        ctx.args.key = 'nope'

        result, out = self.run_command(ctx)

        self.assert_equal(1, result)
        self.assert_in('No such entry', out)

    def test_that_a_missing_plugin_context_is_reported(self):
        """The command may be started without its plugin."""
        result, out = self.run_command(self.context_with(None))

        self.assert_equal(1, result)
        self.assert_in('No plugin context', out)

    def test_that_a_context_without_the_entry_is_reported(self):
        ctx = self.context_with({'a': 1})
        ctx.plugin_context.unregister(CONTEXT_ENTRY)

        result, _out = self.run_command(ctx)

        self.assert_equal(1, result)


class ApplicationPublishesTheContextTest(dewi_core.testcase.TestCase):
    """
    Application used to drop the context the loader returned.

    Everything a plugin registered was thrown away, which is why nothing ever
    used the feature: a command had no way to reach it.
    """

    def application(self):
        from dewi_core.application import Application

        return Application('sample')

    def test_that_a_fresh_application_has_no_context(self):
        self.assert_is_none(self.application()._plugin_context)

    def test_that_loading_a_plugin_keeps_the_context(self):
        app = self.application()
        app.load_plugin('dewi_core.commands.sharedconfig.SharedConfigPlugin')

        self.assert_is_not_none(app._plugin_context)

    def test_that_what_the_plugin_registered_is_in_it(self):
        app = self.application()
        app.load_plugin('dewi_core.commands.sharedconfig.SharedConfigPlugin')

        self.assert_in(CONTEXT_ENTRY, app._plugin_context)

    def test_that_a_second_load_shares_the_same_context(self):
        app = self.application()
        app.load_plugin('dewi_core.commands.sharedconfig.SharedConfigPlugin')
        first = app._plugin_context
        app.load_plugins([])

        self.assert_is(first, app._plugin_context)

    def test_that_the_context_reaches_a_command(self):
        """End to end: what load() shared is what run() reads."""
        app = self.application()
        app.load_plugin('dewi_core.commands.sharedconfig.SharedConfigPlugin')

        ctx = ApplicationContext()
        ctx.plugin_context = app._plugin_context
        ctx.args.key = 'greeting'

        output = io.StringIO()
        with redirect_stdout(output):
            result = SharedConfigCommand().run(ctx)

        self.assert_equal(0, result)
        self.assert_equal('hello\n', output.getvalue())


if __name__ == '__main__':
    import unittest

    unittest.main()
