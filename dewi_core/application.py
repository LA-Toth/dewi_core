# Copyright 2015-2020 Laszlo Attila Toth
# Distributed under the terms of the GNU Lesser General Public License v3

import argparse
import os
import shlex
import sys
import traceback
import typing

from dewi_core.command import Command
from dewi_core.commandregistry import CommandRegistry
from dewi_core.loader.context import Context
from dewi_core.loader.loader import PluginLoader
from dewi_core.loader.plugin import Plugin
from dewi_core.logger import create_logger, LoggerType, LogLevel, log_debug
from dewi_core.utils.levenstein import get_similar_names_to


class EmptyPlugin(Plugin):
    """Default plugin which does nothing"""

    def load(self, c: Context):
        pass


def _list_commands(prog_name: str, command_registry: CommandRegistry, *, all_commands: bool = False):
    commands = dict()
    max_length = 0
    infix = '  - alias of '
    infix_len = len(infix)

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

    format_str = "  {0:<" + str(max_length * 2 + infix_len) + "}   -- {1}"
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
        context: Context = args.context_
        _list_commands(args.program_name_, context.command_registry, all_commands=True)


class _ListCommand(Command):
    name = 'list'
    description = 'Lists all available command with their names only'

    def run(self, args: argparse.Namespace):
        context: Context = args.context_
        _list_commands(args.program_name_, context.command_registry)


class Application:
    def __init__(self, loader: PluginLoader, program_name: str, *,
                 fallback_to_plugin_name: typing.Optional[str] = None,
                 disable_plugins_from_cmdline: typing.Optional[bool] = None,
                 command_class: typing.Optional[typing.Type[Command]] = None
                 ):
        self._loader = loader
        self._program_name = program_name
        self._fallback_plugin_name = fallback_to_plugin_name or 'dewi_core.application.EmptyPlugin'
        self._disable_plugins_from_cmdline = disable_plugins_from_cmdline
        self._command_class = command_class

    def _parse_app_args(self, args: typing.List[str]):
        parser = argparse.ArgumentParser(
            prog=self._program_name,
            usage='%(prog)s [options] [command [command-args]]')

        if not self._disable_plugins_from_cmdline:
            parser.add_argument(
                '-p', '--plugin', help='Load this plugin. This option can be specified more than once.',
                default=[], action='append')

        parser.add_argument('--wait', action='store_true', help='Wait for user input before terminating application')
        parser.add_argument(
            '--print-backtraces', action='store_true',
            help='Print backtraces of the exceptions')
        parser.add_argument('--debug', '-d', action='store_true', help='Enable print/log debug messages')

        logging = parser.add_argument_group('Logging')
        logging.add_argument('-v', '--log-level', dest='log_level', help='Set log level, default: warning',
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

        parser.add_argument('command', nargs='?', help='Command to be run', default='list')
        parser.add_argument(
            'commandargs', nargs=argparse.REMAINDER, help='Additonal options and arguments of the specified command',
            default=[], )
        return parser.parse_args(args)

    def run(self, args: typing.List[str]):
        if self._command_class:
            args = self._update_args_from_custom_env_var(args)

            self._disable_plugins_from_cmdline = True

        app_ns = self._parse_app_args(args)
        self._process_debug_opts(app_ns)

        if self._process_logging_options(app_ns):
            sys.exit(1)

        try:
            log_debug('Loading plugins')
            context = self._loader.load(set(self._get_plugin_names(app_ns)))
            command_name = app_ns.command

            if self._command_class:
                context.commands.register_class(self._command_class)
                prog = self._program_name
            else:
                context.commands.register_class(_ListAllCommand)
                context.commands.register_class(_ListCommand)
                prog = '{} {}'.format(self._program_name, command_name)

            if command_name in context.command_registry:

                command_class = context.command_registry.get_command_class_descriptor(command_name).get_class()
                command = command_class()

                parser = self._create_command_parser(command, prog)
                ns = parser.parse_args(app_ns.commandargs)
                ns.running_command_ = command_name
                ns.debug_ = app_ns.debug
                ns.print_backtraces_ = app_ns.print_backtraces
                ns.parser_ = parser
                ns.context_ = context
                ns.program_name_ = self._program_name

                log_debug('Starting command', name=command_name)
                sys.exit(command.run(ns))

            else:
                print(f"ERROR: The command '{command_name}' is not known.\n")
                similar_names = get_similar_names_to(command_name, sorted(context.command_registry.get_command_names()))

                print('Similar names - firstly based on command name length:')
                for name in similar_names:
                    print('  {:30s}   -- {}'.format(
                        name,
                        context.command_registry.get_command_class_descriptor(name).get_class().description))
                sys.exit(1)

        except SystemExit:
            self._wait_for_termination_if_needed(app_ns)
            raise
        except BaseException as exc:
            if app_ns.print_backtraces:
                self._print_backtrace()
            print(exc, file=sys.stderr)
            self._wait_for_termination_if_needed(app_ns)
            sys.exit(1)

    def _process_debug_opts(self, app_ns: argparse.Namespace):
        if app_ns.debug or os.environ.get('DEWI_DEBUG', 0) == 1:
            app_ns.print_backtraces = True
            app_ns.log_level = 'debug'
            app_ns.debug = True

    def _update_args_from_custom_env_var(self, args: typing.List[str]):
        args_ = []
        env_var_name = f'{self._program_name.replace("-", "_").upper()}_ARGS'
        if env_var_name in os.environ:
            args_ = shlex.split(os.environ[env_var_name])
        args_ += [self._command_class.name] + args
        args = args_
        return args

    def _process_logging_options(self, args: argparse.Namespace):
        if args.log_none:
            if args.log_syslog or args.log_file or args.log_console:
                print('ERROR: --log-none cannot be used any other log target,')
                print('ERROR: none of: --log-file, --log-console, --log-syslog')
                return 1
            create_logger(self._program_name, LoggerType.NONE, args.log_level, filenames=[])
        else:
            logger_types = []
            if args.log_console:
                logger_types.append(LoggerType.CONSOLE)
            if args.log_file:
                logger_types.append(LoggerType.FILE)
            if args.log_syslog:
                logger_types.append(LoggerType.SYSLOG)

            if not logger_types:
                # Using default logger
                logger_types = LoggerType.CONSOLE

            create_logger(self._program_name, logger_types, args.log_level, filenames=args.log_file)

        return 0

    def _get_plugin_names(self, app_ns: argparse.Namespace):
        if self._disable_plugins_from_cmdline:
            plugins = [self._fallback_plugin_name]
        else:
            plugins = app_ns.plugin or [self._fallback_plugin_name]
        return plugins

    def _create_command_parser(self, command: Command, prog: str):
        parser = argparse.ArgumentParser(
            description=command.description,
            prog=prog)
        parser.set_defaults(running_subcommands_=[])
        command.register_arguments(parser)
        if command.subcommand_classes:
            self._register_subcommands([], command, parser)

        return parser

    def _register_subcommands(self, prev_command_names: typing.List[str], command: Command,
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
                self._register_subcommands(prev_command_names + [subcommand.name], subcommand, subparser,
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

    def _print_backtrace(self):
        einfo = sys.exc_info()
        tbs = traceback.extract_tb(einfo[2])
        tb_str = 'An exception occurred:\n  Type: %s\n  Message: %s\n\n' % \
                 (einfo[0].__name__, einfo[1])
        for tb in tbs:
            tb_str += '  File %s:%s in %s\n    %s\n' % (tb.filename, tb.lineno, tb.name, tb.line)
        print(tb_str)

    def _wait_for_termination_if_needed(self, app_ns):
        if app_ns.wait:
            print("\nPress ENTER to continue")
            input("")


class SimpleApplication(Application):
    def __init__(self, program_name: str, default_plugin_name: str):
        super().__init__(PluginLoader(), program_name, fallback_to_plugin_name=default_plugin_name)


class SinglePluginApplication(Application):
    def __init__(self, program_name: str, plugin_name: str):
        super().__init__(PluginLoader(), program_name, fallback_to_plugin_name=plugin_name,
                         disable_plugins_from_cmdline=True)


class SingleCommandApplication(Application):
    def __init__(self, program_name: str, command_class: typing.Type[Command]):
        super().__init__(PluginLoader(), program_name, command_class=command_class)
