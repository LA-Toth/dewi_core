#!/usr/bin/env python3
# Copyright 2017-2021 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

import os.path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..'))

from dewi_core.application import Application


def main():
    app = Application('steven')
    app.load_plugin('steven.StevenPlugin')
    app.run(sys.argv[1:])

    if __name__ == '__main__':
        main()
