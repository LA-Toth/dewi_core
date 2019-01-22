#!/usr/bin/env python3
# Copyright 2017 Laszlo Attila Toth
# Distributed under the terms of the GNU Lesser General Public License v3


import os.path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..'))

from dewi_core.application import MainApplication
from dewi_core.loader.loader import PluginLoader


def main():
    args = ['-p', 'steven.StevenPlugin'] + sys.argv[1:]

    loader = PluginLoader()
    app = MainApplication(loader, 'steven')
    app.run(args)


if __name__ == '__main__':
    main()
