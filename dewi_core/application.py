# Copyright 2015-2021 Laszlo Attila Toth
# Distributed under the terms of the GNU Lesser General Public License v3

import argparse
import os
import sys
import typing

from dewi_core.command import Command
from dewi_core.command import register_subcommands
from dewi_core.commandregistry import CommandRegistry
from dewi_core.loader.loader import PluginLoader
from dewi_core.logger import LogLevel
from dewi_core.logger import log_debug, create_logger_from_config, LoggerConfig
from dewi_core.utils.exception import print_backtrace
from dewi_core.utils.levenshtein import get_similar_names_to


def get_command_from_plugin_ns(plugin_name: str, ns: argparse.Namespace) -> typing.Type[Command]:
    """
    Returns the command  class specified in the ns namespace via its running_command_
    and running_subcommands_ members.

    The ns comes from an already parsed namespace, especially via
    dewi_core.remoting.serialize_argparse_namespace and deserialize_argparse_namespace methods.

    The command must exist.

    :param plugin_name: The command plugin or app plugin containing the command referred by ns.running_command_
    :param ns: the prepared Namespace object
    :return: the command class based on ns.
    """
    command_registry = CommandRegistry()
    loader = PluginLoader(command_registry)
    ctx = loader.load([plugin_name])
    cmd_class = command_registry.get_command_class_descriptor(ns.running_command_).get_class()

    if 'running_subcommands_' in ns and ns.running_subcommands_:
        for sub_cmd_name in ns.running_subcommands_:
            for cc in cmd_class.subcommand_classes:
                if cc.name == sub_cmd_name:
                    cmd_class = cc

    ns.cmd_class_ = cmd_class

    return cmd_class


def run_command_from_plugin_ns(plugin_name: str, ns: argparse.Namespace) -> typing.Optional[int]:
    """
    Runs the command returned by get_command_from_plugin_ns(). See that function.
    """
    return get_command_from_plugin_ns(plugin_name, ns)().run(ns)


def _list_commands(prog_name: str, command_registry: CommandRegistry, *, all_commands: bool = False):
    commands = dict()
    max_length = 0
    infix = '  - alias of '

    for name in command_registry.get_command_names():
        command_name, description = _get_command_name_and_description(command_registry, name)

        if name == command_name:
            cmdname = name
        else:
            if not all_commands:
                continue

            cmdname = (name, command_name)

        if len(name) > max_length:
            max_length = len(name)

        commands[name] = (cmdname, description)

    if all_commands:
        format_str = "  {0:<" + str(max_length * 2 + len(infix)) + "}   -- {1}"
    else:
        format_str = "  {0:<" + str(max_length) + "}   -- {1}"

    alias_format_str = "{0:<" + str(max_length) + "}" + infix + "{1}"

    print(f'Available {prog_name.capitalize()} Commands.')
    for name in sorted(commands):
        cmdname, description = commands[name]
        if isinstance(cmdname, tuple):
            cmdname = alias_format_str.format(*cmdname)
        print(format_str.format(cmdname, description))


def _get_command_name_and_description(command_registry, name):
    desc = command_registry.get_command_class_descriptor(name)
    description = desc.get_class().description
    command_name = desc.get_name()
    return command_name, description


class _ListAllCommand(Command):
    name = 'list-all'
    description = 'Lists all available command with aliases'

    def run(self, args: argparse.Namespace):
        _list_commands(args.program_name_, args.command_registry_, all_commands=True)


class _ListCommand(Command):
    name = 'list'
    description = 'Lists all available command with their names only'

    def run(self, args: argparse.Namespace):
        _list_commands(args.program_name_, args.command_registry_)


class Application:
    def __init__(self, program_name: str,
                 command_class: typing.Optional[typing.Type[Command]] = None,
                 *,
                 enable_short_debug_option: bool = False,
                 ):
        self._program_name = program_name
        self._command_class = command_class
        self._enable_short_debug_option = enable_short_debug_option if command_class is not None else True
        self._command_registry = CommandRegistry()
        self._command_classes = set()

        if command_class:
            self._command_classes.add(command_class)
            self._command_registry.register_class(command_class)

    def add_command_class(self, command_class: typing.Type[Command]):
        self._command_classes.add(command_class)
        self._command_registry.register_class(command_class)

    def add_command_classes(self, command_classes: typing.List[typing.Type[Command]]):
        for command_class in command_classes:
            self.add_command_class(command_class)

    def load_plugin(self, name: str):
        self.load_plugins([name])

    def load_plugins(self, names: typing.List[str]):
        loader = PluginLoader(self._command_registry)
        loader.load(names)

    def run(self, args: typing.List[str]):
        if self._command_class and len(self._command_classes) == 1:
            return self.run_single_command(args)
        else:
            return self._run_with_multi_commands(args)

    def run_single_command(self, args: typing.List[str]):
        ns = argparse.Namespace()
        ns.print_backtraces_ = False
        ns.wait = False
        try:
            command = self._command_class()
            parser = self._create_command_parser(command, self._program_name, register_app_args=True)
            ns = self._create_command_ns(parser, args, command.name, single_command=True)
            ns.cmd_class_ = self._command_class

            self._process_debug_opts(ns)
            if self._process_logging_options(ns):
                sys.exit(1)

            if ns.cwd:
                os.chdir(ns.cwd)

            log_debug('Starting command', name=self._command_class.name)
            sys.exit(command.run(ns))

        except SystemExit:
            self._wait_for_termination_if_needed(ns)
            raise
        except BaseException as exc:
            self._print_exception(ns.print_backtraces_, exc)
            self._wait_for_termination_if_needed(ns)
            sys.exit(1)

    def _run_with_multi_commands(self, args: typing.List[str]):
        parser = argparse.ArgumentParser(
            prog=self._program_name,
            usage='%(prog)s [options] [command [command-args]]')
        self._register_app_args(parser)

        parser.add_argument('command', nargs='?', help='Command to be run', default='list')
        parser.add_argument(
            'commandargs', nargs=argparse.REMAINDER, help='Additonal options and arguments of the specified command',
            default=[], )
        app_ns = parser.parse_args(args)

        self._process_debug_opts(app_ns)
        if self._process_logging_options(app_ns):
            sys.exit(1)

        try:
            if app_ns.cwd:
                os.chdir(app_ns.cwd)
            command_name = app_ns.command
            self._command_registry.register_class(_ListAllCommand)
            self._command_registry.register_class(_ListCommand)
            prog = '{} {}'.format(self._program_name, command_name)

            if command_name in self._command_registry:
                command_class = self._command_registry.get_command_class_descriptor(command_name).get_class()
                command = command_class()

                parser = self._create_command_parser(command, prog)
                ns = self._create_command_ns(parser, app_ns.commandargs, command.name,
                                             self._command_class is not None)
                ns.debug_ = app_ns.debug_
                ns.cmd_class_ = command_class

                log_debug('Starting command', name=command_name)
                sys.exit(command.run(ns))

            else:
                print(f"ERROR: The command '{command_name}' is not known.\n")
                similar_names = get_similar_names_to(command_name, sorted(self._command_registry.get_command_names()))

                print('Similar names - firstly based on command name length:')
                for name in similar_names:
                    print('  {:30s}   -- {}'.format(
                        name,
                        self._command_registry.get_command_class_descriptor(name).get_class().description))
                sys.exit(1)

        except SystemExit:
            self._wait_for_termination_if_needed(app_ns)
            raise
        except BaseException as exc:
            self._print_exception(app_ns.print_backtraces_, exc)
            self._wait_for_termination_if_needed(app_ns)
            sys.exit(1)

    def _create_command_ns(self, parser: argparse.ArgumentParser,
                           args: typing.List[str], command_name: str,
                           single_command: bool) -> argparse.Namespace:
        ns = parser.parse_args(args)
        ns.running_command_ = command_name
        ns.parser_ = parser
        ns.command_registry_ = self._command_registry
        ns.program_name_ = self._program_name
        ns.single_command_ = single_command
        return ns

    def _register_app_args(self, parser: argparse.ArgumentParser):
        parser.add_argument('--cwd', dest='cwd', help='Change to specified directory')
        parser.add_argument('--wait', action='store_true', help='Wait for user input before terminating application')
        parser.add_argument(
            '--print-backtraces', action='store_true', dest='print_backtraces_',
            help='Print backtraces of the exceptions')

        debug_opts = ['--debug']
        if self._enable_short_debug_option:
            debug_opts.append('-d')
        parser.add_argument(*debug_opts, dest='debug_', action='store_true', help='Enable print/log debug messages')

        logging = parser.add_argument_group('Logging')
        logging.add_argument('--log-level', dest='log_level', help='Set log level, default: warning',
                             choices=[i.name.lower() for i in LogLevel], default='info')
        logging.add_argument('--log-syslog', dest='log_syslog', action='store_true',
                             help='Log to syslog. Can be combined with other log targets')
        logging.add_argument('--log-console', '--log-stdout', dest='log_console', action='store_true',
                             help='Log to STDOUT, the console. Can be combined with other targets.'
                                  'If no target is specified, this is used as default.')
        logging.add_argument('--log-file', dest='log_file', action='append',
                             help='Log to a file. Can be specified multiple times and '
                                  'can be combined with other options.')
        logging.add_argument('--no-log', '-l', dest='log_none', action='store_true',
                             help='Disable logging. If this is set, other targets are invalid.')

    def _process_debug_opts(self, ns: argparse.Namespace):
        if ns.debug_ or os.environ.get('DEWI_DEBUG', 0) == '1':
            ns.print_backtraces_ = True
            ns.log_level = 'debug'
            ns.debug_ = True

    def _process_logging_options(self, args: argparse.Namespace):
        return create_logger_from_config(
            LoggerConfig.create(self._program_name, args.log_level, args.log_none, args.log_syslog, args.log_console,
                                args.log_file))

    def _create_command_parser(self, command: Command, prog: str, *, register_app_args: bool = False):
        parser = argparse.ArgumentParser(
            description=command.description,
            prog=prog)
        parser.set_defaults(running_subcommands_=[])
        if register_app_args:
            self._register_app_args(parser)
        command.register_arguments(parser)
        if command.subcommand_classes:
            register_subcommands([], command, parser)

        return parser

    def _wait_for_termination_if_needed(self, app_ns):
        if app_ns.wait:
            print("\nPress ENTER to continue")
            input("")

    def _print_exception(self, print_bt: bool, exc: BaseException):
        if print_bt or os.environ.get('DEWI_DEBUG', 0) == '1':
            print_backtrace()
        print(f'Exception: {exc} (type: {type(exc).__name__})', file=sys.stderr)
