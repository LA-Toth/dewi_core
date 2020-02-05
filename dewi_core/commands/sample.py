# Copyright 2015-2020 Laszlo Attila Toth
# Distributed under the terms of the GNU Lesser General Public License v3

import argparse

from dewi_core.command import Command
from dewi_core.loader.context import Context
from dewi_core.loader.plugin import Plugin


class SampleCommand(Command):
    name = 'sample'

    def run(self, ns: argparse.ArgumentParser):
        return 42


class SamplePlugin(Plugin):
    """plugin description"""

    def load(self, c: Context):
        c.commands.register_class(SampleCommand)
