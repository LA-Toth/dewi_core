# Copyright 2021 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

from dewi_core.application import Application


def main():
    app = Application('dewi-edit-or-review')
    app.load_plugin('dewi_core.commands.edit.edit.EditPlugin')
    app.load_plugin('dewi_core.commands.review.ReviewPlugin')
    app.load_plugin('dewi_core.commands.editreview.EditReviewPlugin')
    app.run()


if __name__ == '__main__':
    main()
