# Copyright 2015-2022 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

import collections.abc

from dewi_core.command import Command
from dewi_core.loader.context import Context


class Plugin:
    """
    A plugin is an extension of DEWI.
    """

    def get_dependencies(self) -> collections.abc.Iterable[str]:
        return ()

    def load(self, c: Context):
        raise NotImplementedError

    @staticmethod
    def _r(c: Context, t: type[Command]):
        """
        Registers a Command type into commommandregistry.

        >> from dewi_core.commands.sample import SampleCommand
        >> from dewi_core.context import Context
        >> from dewi_core.loader.plugin import Plugin
        >>
        >>
        >>  class SamplePlugin(Plugin):
        >>      '''Provides "sample" command'''
        >>
        >>      def load(self, c: Context):
        >>          self._r(c, SampleCommand)
        >>
        """
        c.commands.register_class(t)

    @staticmethod
    def _register_config_dir(c: Context, d: str):
        c.config_dir_registry.register_config_directory(d)
