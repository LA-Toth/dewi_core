# Copyright 2017-2021 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

import collections

from dewi_core.loader.context import Context
from dewi_core.loader.plugin import Plugin


class StevenPlugin(Plugin):
    """Steven: An example application using DEWI"""

    def get_dependencies(self) -> collections.Iterable:
        return {
            #'dewi_commands.commands.CommandsPlugin',
            'steven.commands.CommandsPlugin',
        }

    def load(self, c: Context):
        pass
