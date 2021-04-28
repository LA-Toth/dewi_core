# Copyright 2015-2021 Laszlo Attila Toth
# Distributed under the terms of the GNU Lesser General Public License v3

import argparse
import typing

from dewi_core.logger import log_error


class Command:
    name = ''
    aliases = list()
    description = ''
    subcommand_classes = []
    man_page_file: str = ''  # relative to the command's file

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
            log_error(f"Missing subcommand for {progname} {' '.join(args.running_subcommands_)}")
        else:
            raise NotImplementedError()

        return 1


def register_subcommands(prev_command_names: typing.List[str], command: Command,
                         parser: argparse.ArgumentParser,
                         last_command_name: typing.Optional[str] = None):
    last_command_name = last_command_name or ''
    dest_name = 'running_subcommand_'
    if last_command_name:
        dest_name += f'{last_command_name}_'
    parsers = parser.add_subparsers(dest=dest_name)

    for subcommand_class in command.subcommand_classes:
        subcommand: Command = subcommand_class()
        subparser = parsers.add_parser(subcommand.name, help=subcommand.description, aliases=subcommand.aliases)
        subcommand.register_arguments(subparser)

        if subcommand.subcommand_classes:
            subcommand_name = f'{last_command_name}_{subcommand.name}'
            register_subcommands(prev_command_names + [subcommand.name], subcommand, subparser,
                                 subcommand_name)

        subparser.set_defaults(running_subcommands_=prev_command_names + [subcommand.name],
                               func=subcommand.run)

    command._orig_saved_run_method = command.run

    def run(ns: argparse.Namespace):
        if vars(ns)[dest_name] is not None:
            return ns.func(ns)
        else:
            return command._orig_saved_run_method(ns)

    command.run = run
