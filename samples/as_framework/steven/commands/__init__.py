# Copyright 2017-2021 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

from dewi_core.loader.context import Context
from dewi_core.loader.plugin import Plugin

from steven.commands.xssh import XSshCommand


class CommandsPlugin(Plugin):
    """Steven: A set of tools"""

    def load(self, c: Context):
        self._r(c, XSshCommand)
