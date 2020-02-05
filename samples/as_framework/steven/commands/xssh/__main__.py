# Copyright 2020 Laszlo Attila Toth
# Distributed under the terms of the GNU Lesser General Public License v3

import sys

from dewi_core.application import SingleCommandApplication
from steven.commands.xssh import XSshCommand


def main():
    app = SingleCommandApplication('steven-ssh', XSshCommand)
    app.run(sys.argv[1:])


if __name__ == '__main__':
    main()
