# Copyright 2015-2021 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

import re
import subprocess

import click

from dewi_core.appcontext import ApplicationContext
from dewi_core.command import Command
from dewi_core.commandplugin import CommandPlugin
from dewi_core.optioncontext import OptionContext


def convert_to_vim_args(args):
    result = []
    if len(args) == 1:
        match = re.match(r'(.*?):([[0-9]+)(:[0-9]+)?:?$', args[0])
        if match:
            result.append(match.group(1))
            result.append('+' + match.group(2))
        else:
            result.append(args[0])
    elif len(args) > 1:
        result = ['-p'] + args

    return result


class EditCommand(Command):
    name = 'edit'
    aliases = ['ed']
    description = 'Calls vim with the file names and line numbers parsed from argument list.'

    @staticmethod
    def register_arguments(c: OptionContext):
        c.add_argument('file_list', nargs=-1, type=click.Path(), help='Files to open')

    def run(self, ctx: ApplicationContext):
        args = ['vim'] + convert_to_vim_args(ctx.args.file_list)
        pipe = subprocess.Popen(args)
        pipe.communicate()


EditPlugin = CommandPlugin.create(EditCommand)
