# Copyright 2021 Laszlo Attila Toth
# Distributed under the terms of the GNU Lesser General Public License v3

import typing

from dewi_core.config.node import SealableNode, Node


class ApplicationContext(SealableNode):
    def __init__(self):
        from .commandregistry import CommandRegistry
        # args: similar to argparse.Namespace: a single mapping containing all options.
        # It may have conflicting keys, so latest subcommand wins
        self.args = Node()
        # Each command has its own args (options), this contains them separately
        # The app (top-level cmd) belongs to the '__main__' key, the first-level subcommand
        # into the 'subcmd-name', second-level: 'subcmd-name subcmd2-name2'
        self.commands_args = Node()
        self.current_args = Node()
        self.program_name = ''
        self.command_registry: CommandRegistry = None
        self.single_command_mode: bool = False
        # top-level command name, in single command mode it's that command, otherwise first subcommand
        self.running_command: str = ''
        # the remaining commands within running_subcommand
        self.running_subcommands: typing.List[str] = []
        # both running_command and running_subcommands
        self.running_full_command: typing.List[str] = []
        # for the currently running command the invoked subcommand (eg. in the run() of ReviewCommand may be 'change')
        self.invoked_subcommand: typing.Optional[str] = None
        self.config_directories: typing.List[str] = []
        self.environment: str = ''
        # A generic context for subcommands, may pass data to their subcommands
        self.command_context = Node()
        self._seal()

    def add_arg(self, key: str, value):
        setattr(self.args, key, value)

    def add_cmd_args(self, cmd: str, args: typing.Dict):
        if cmd == '__main__':
            self.commands_args[cmd] = Node.create_from(args)
        else:
            if not self.running_command:
                self.running_command = cmd
            else:
                self.running_subcommands.append(cmd)
            self.running_full_command.append(cmd)

            self.commands_args[' '.join(self.running_full_command)] = Node.create_from(args)
