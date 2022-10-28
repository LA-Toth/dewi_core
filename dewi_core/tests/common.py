# Copyright 2015-2022 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

import os

from dewi_core.loader.context import Context
from dewi_core.loader.plugin import Plugin

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data'))


class EmptyPlugin(Plugin):
    """Default plugin which does nothing"""

    def load(self, c: Context):
        pass


class TestEnv:

    def __init__(self):
        self.entries: list[str] = []

    def add_entry(self, entry: str):
        self.entries.append(entry)

    def reset_entries(self):
        self.entries.clear()


test_env = TestEnv()
