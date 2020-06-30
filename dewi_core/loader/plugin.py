# Copyright 2015-2017 Laszlo Attila Toth
# Distributed under the terms of the GNU Lesser General Public License v3

import typing

from dewi_core.command import Command
from dewi_core.loader.context import Context


class Plugin:
    """
    A plugin is an extension of DEWI.
    """

    def get_dependencies(self) -> typing.Iterable[str]:
        return ()

    def load(self, c: Context):
        raise NotImplementedError

    @staticmethod
    def _r(c: Context, t: typing.Type[Command]):
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
