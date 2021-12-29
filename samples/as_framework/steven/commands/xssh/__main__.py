# Copyright 2020-2021 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

import sys

from dewi_core.application import Application
from steven.commands.xssh import XSshCommand


def main():
    app = Application('steven-ssh', XSshCommand)
    app.run(sys.argv[1:])


if __name__ == '__main__':
    main()
