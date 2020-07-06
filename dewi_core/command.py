# Copyright 2015-2018 Laszlo Attila Toth
# Distributed under the terms of the GNU Lesser General Public License v3

import argparse
import typing


class Command:
    name = ''
    aliases = list()
    description = ''
    subcommand_classes = []

    def register_arguments(self, parser: argparse.ArgumentParser) -> None:
        pass

    def run(self, args: argparse.Namespace) -> typing.Optional[int]:
        raise NotImplementedError()


class SubCommand(Command):
    def run(self, args: argparse.Namespace) -> typing.Optional[int]:
        field = f"running_subcommand__{'_'.join(args.running_subcommands_)}_"
        if vars(args)[field] is None:
            progname = args.program_name_
            if not args.single_command_:
                progname += f' {args.running_command_}'
            print("Missing subcommand.")
            print("Try help:")
            print(f"{progname} {' '.join(args.running_subcommands_)} --help")
        else:
            raise NotImplementedError()

        return 1
