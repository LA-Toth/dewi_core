# Copyright 2020-2021 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

import os
import sys

from dewi_core.application import Application
from dewi_core.commands.edit.edit import EditCommand


def main():
    if int(os.environ.get('DEWI_CORE_DEV_WITH_PLUGINS', '0')) == 1:
        app = Application('dewi-edit')
        app.load_plugin('dewi_core.commands.edit.edit.EditPlugin')
    else:
        app = Application('dewi-edit', EditCommand)
    app.run(sys.argv[1:])


if __name__ == '__main__':
    main()
