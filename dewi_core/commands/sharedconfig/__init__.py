# Copyright 2015-2022 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

"""
A sample: state shared by a plugin with its commands.

This is the part of the plugin system a plain list of command classes cannot
do. A plugin's load() runs before any command does, so what it registers in the
Context is there for every command afterwards, and for plugins loaded later,
since the loader loads them in dependency order.

    app = Application('sample')
    app.load_plugin('dewi_core.commands.sharedconfig.SharedConfigPlugin')

What is registered is an accessor, not the loaded value. The difference matters
once an application runs for more than one command:

* A single-shot run loads the file at most once, and not at all if no command
  asks for it -- the cost is paid by the commands that need it.
* An interactive session may run for hours, and the file can be changed by
  somebody else in the meantime. The accessor notices and reloads.

Registering the value itself is the tempting shortcut, and it is a global
variable with all that implies: correct until the process outlives the file.
"""

import collections.abc
import json
import os.path
import threading

from dewi_core.appcontext import ApplicationContext
from dewi_core.command import Command
from dewi_core.loader.context import Context
from dewi_core.loader.plugin import Plugin
from dewi_core.optioncontext import OptionContext

#: The name the accessor is registered under; the commands look it up by this.
CONTEXT_ENTRY = 'shared_config'

DEFAULT_CONFIG_FILE = '~/.config/dewi/shared-config.json'

DEFAULTS = {'source': '<defaults>', 'greeting': 'hello'}


class SharedConfig:
    """
    The configuration, loaded once and reloaded when the file changes.

    Stands in for whatever is expensive or awkward to build repeatedly: a
    parsed XML configuration, a database handle, a connection pool.
    """

    def __init__(self, filename: str):
        self.filename = os.path.expanduser(filename)
        self.load_count = 0
        self._config: dict | None = None
        self._loaded_mtime: float | None = None
        self._lock = threading.Lock()

    def get(self) -> dict:
        """
        The current configuration.

        Read on the first call, and again whenever the file's timestamp has
        moved since the last read.
        """
        with self._lock:
            mtime = self._mtime()
            if self._config is None or mtime != self._loaded_mtime:
                self._config = self._read()
                self._loaded_mtime = mtime
                self.load_count += 1

            return self._config

    def invalidate(self):
        """Force the next get() to read the file again."""
        with self._lock:
            self._config = None
            self._loaded_mtime = None

    def _mtime(self) -> float | None:
        try:
            return os.path.getmtime(self.filename)
        except OSError:
            return None

    def _read(self) -> dict:
        if not os.path.exists(self.filename):
            return dict(DEFAULTS)

        with open(self.filename, encoding='UTF-8') as f:
            config = json.load(f)

        config['source'] = self.filename
        return config


class SharedConfigCommand(Command):
    """Prints the configuration the plugin shared."""

    name = 'shared-config'
    aliases = ['shared-cfg']
    description = 'Show the configuration shared by the plugin'

    @staticmethod
    def register_arguments(c: OptionContext):
        c.add_option('-k', '--key', dest='key', help='Print only this entry')

    def run(self, ctx: ApplicationContext) -> int | None:
        shared = self.shared_config(ctx)
        if shared is None:
            print('No plugin context: this command was not started through a plugin')
            return 1

        config = shared.get()

        if ctx.args.key:
            if ctx.args.key not in config:
                print(f'No such entry: {ctx.args.key}')
                return 1

            print(config[ctx.args.key])
            return 0

        for key in sorted(config):
            print(f'{key}: {config[key]}')

        return 0

    @staticmethod
    def shared_config(ctx: ApplicationContext) -> SharedConfig | None:
        """
        The accessor the plugin registered, or None if no plugin was loaded.

        A command can be run without its plugin -- Application.add_command_class
        takes a class directly -- so the entry is not assumed to be there.
        """
        if ctx.plugin_context is None or CONTEXT_ENTRY not in ctx.plugin_context:
            return None

        return ctx.plugin_context[CONTEXT_ENTRY]


class SharedConfigPlugin(Plugin):
    """Shares the configuration, then registers the command that reads it."""

    #: Overridden by the tests, and by whoever wants a different file.
    config_file = DEFAULT_CONFIG_FILE

    def get_dependencies(self) -> collections.abc.Iterable[str]:
        return ()

    def load(self, c: Context):
        # Registered before any command runs, so every command of every plugin
        # loaded afterwards can reach it. register() refuses to overwrite, so a
        # second plugin claiming the name is an error here rather than a
        # surprise later.
        #
        # Nothing is read from disk yet: the accessor loads on first use.
        c.register(CONTEXT_ENTRY, SharedConfig(self.config_file))
        self._r(c, SharedConfigCommand)
