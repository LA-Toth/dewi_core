# Copyright 2015-2019 Laszlo Attila Toth
# Distributed under the terms of the GNU Lesser General Public License v3

from dewi_core.loader.tests import TestLoadable


class TestPlugin(TestLoadable):
    def test_plugin(self):
        self.assert_loadable('dewi_core.application.EmptyPlugin')
