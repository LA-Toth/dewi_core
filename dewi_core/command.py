# Copyright 2015-2021 Laszlo Attila Toth
# Distributed under the terms of the GNU Lesser General Public License v3

import typing

from dewi_core.appcontext import ApplicationContext
from dewi_core.optioncontext import OptionContext


class Command:
    name = ''
    aliases = list()
    description = ''
    subcommand_classes = []
    man_page_file: str = ''  # relative to the command's file

    @staticmethod
    def register_arguments(c: OptionContext):
        # can also be @classmethod
        pass

    def run(self, ctx: ApplicationContext) -> typing.Optional[int]:
        pass
