# Copyright 2015-2021 Laszlo Attila Toth
# Distributed under the terms of the GNU Lesser General Public License v3

import os
import typing

from dewi_core.loader.context import Context
from dewi_core.loader.plugin import Plugin

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data'))


class EmptyPlugin(Plugin):
    """Default plugin which does nothing"""

    def load(self, c: Context):
        pass


class TestEnv:

    def __init__(self):
        self.entries: typing.List[str] = []

    def add_entry(self, entry: str):
        self.entries.append(entry)

    def reset_entries(self):
        self.entries.clear()


test_env = TestEnv()
