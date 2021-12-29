# Copyright 2015-2021 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

from dewi_core.loader.tests import TestLoadable


class TestPlugin(TestLoadable):
    def test_plugin(self):
        self.assert_loadable('dewi_core.tests.common.EmptyPlugin')
