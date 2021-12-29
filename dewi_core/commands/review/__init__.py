# Copyright 2021 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

from dewi_core.command import Command
from dewi_core.commandplugin import CommandPlugin
from .commands import GerritChangeReviewer, GerritChangeChainReviewer, register_global_args_in_review_cmd
from ...optioncontext import OptionContext


class ReviewCommand(Command):
    name = 'review'
    aliases = ['r', 'rw']
    description = "Example command which could be for Gerrit review"
    subcommand_classes = [
        GerritChangeChainReviewer,
        GerritChangeReviewer,
    ]

    @classmethod
    def register_arguments(cls, c: OptionContext):
        register_global_args_in_review_cmd(c)


ReviewPlugin = CommandPlugin.create(ReviewCommand)
