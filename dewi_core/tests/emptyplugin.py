# Copyright 2015-2021 Laszlo Attila Toth
# Distributed under the terms of the GNU Lesser General Public License v3


from dewi_core.loader.context import Context
from dewi_core.loader.plugin import Plugin


class EmptyPlugin(Plugin):
    """Default plugin which does nothing"""

    def load(self, c: Context):
        pass
