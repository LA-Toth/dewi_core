# Copyright 2020 Laszlo Attila Toth
# Distributed under the terms of the GNU Lesser General Public License v3

import sys

from dewi_core.application import SinglePluginApplication


def main():
    app = SinglePluginApplication('steven', 'steven.StevenPlugin')
    app.run(sys.argv[1:])


if __name__ == '__main__':
    main()
