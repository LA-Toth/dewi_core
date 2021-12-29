# Copyright 2021 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

from dewi_core.command import Command
from dewi_core.commandplugin import CommandPlugin
from dewi_core.commands.edit.edit import EditCommand
from dewi_core.commands.review import ReviewCommand


class EditOrReviewCommand(Command):
    name = 'edit-review'
    aliases = ['er']
    description = 'Example of command with subcommands from other loaded plugins'
    subcommand_classes = [
        EditCommand,
        ReviewCommand
    ]


EditReviewPlugin = CommandPlugin.create(EditOrReviewCommand)
