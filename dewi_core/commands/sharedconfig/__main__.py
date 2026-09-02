# Copyright 2015-2022 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

import sys

from dewi_core.application import Application


def main():
    app = Application('shared-config-sample')
    app.load_plugin('dewi_core.commands.sharedconfig.SharedConfigPlugin')
    app.run(sys.argv[1:])


if __name__ == '__main__':
    main()
