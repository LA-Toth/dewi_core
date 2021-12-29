# Copyright 2021 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

import os

from dewi_core.application import Application
from . import ReviewCommand


def main():
    if int(os.environ.get('DEWI_CORE_DEV_WITH_PLUGINS', '0')) == 1:
        app = Application('dewi-review')
        app.load_plugin('dewi_core.commands.review.ReviewPlugin')
    else:
        app = Application('dewi-review', ReviewCommand)
    app.run()


if __name__ == '__main__':
    main()
