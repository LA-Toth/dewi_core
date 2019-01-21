# Copyright 2017-2019 Laszlo Attila Toth
# Distributed under the terms of the GNU Lesser General Public License v3

from dewi_core.loader.context import Context
from dewi_core.loader.plugin import Plugin

from steven.commands.xssh import XSshCommand


class CommandsPlugin(Plugin):
    def get_description(self) -> str:
        return "Steven: A set of tools"

    def load(self, c: Context):
        self._r(c, XSshCommand)
