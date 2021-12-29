# Copyright 2017-2021 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

import types
import typing

from dewi_core.command import Command
from dewi_core.loader.context import Context
from dewi_core.loader.plugin import Plugin


class CommandPlugin(Plugin):
    command: typing.Type[Command]

    def load(self, c: Context):
        c.commands.register_class(self.command)

    @classmethod
    def create(cls, command: typing.Type[Command]) -> typing.Type[Plugin]:
        class_name = command.__name__
        if class_name.endswith('Command'):
            class_name = class_name[:-len('Command')]
        class_name += 'Plugin'

        cls_dict = {
            'command': command
        }

        return types.new_class(class_name, (CommandPlugin,), {}, lambda ns: ns.update(cls_dict))
