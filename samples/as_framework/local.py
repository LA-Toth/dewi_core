#!/usr/bin/env python3
# Copyright 2017-2020 Laszlo Attila Toth
# Distributed under the terms of the GNU Lesser General Public License v3


import os.path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..'))

from dewi_core.application import SimpleApplication


def main():
    app = SimpleApplication('steven', 'steven.StevenPlugin')
    app.run(sys.argv[1:])

    if __name__ == '__main__':
        main()
