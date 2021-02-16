# Copyright 2015-2021 Laszlo Attila Toth
# Distributed under the terms of the GNU Lesser General Public License v3

import argparse
import os
import sys
import typing

from dewi_core.command import Command, register_subcommands
from dewi_core.loader.context import Context
from dewi_core.logger import log_debug, LogLevel, create_logger_from_config, LoggerConfig
from dewi_core.utils.exception import print_backtrace


class ApplicationBase:
    def __init__(self, program_name: str,
                 command_class: typing.Optional[typing.Type[Command]],
                 *,
                 enable_short_debug_option: bool = False,
                 ):
        self._program_name = program_name
        self._command_class = command_class
        self._enable_short_debug_option = enable_short_debug_option

    def run(self, args: typing.List[str]):
        raise NotImplementedError()

    def _create_command_ns(self, parser: argparse.ArgumentParser,
                           args: typing.List[str], command_name: str,
                           context: typing.Optional[Context],
                           single_command: bool) -> argparse.Namespace:
        ns = parser.parse_args(args)
        ns.running_command_ = command_name
        ns.parser_ = parser
        ns.context_ = context
        ns.program_name_ = self._program_name
        ns.single_command_ = single_command
        return ns

    def _register_base_app_args(self, parser: argparse.ArgumentParser):
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
            self._register_base_app_args(parser)
        command.register_arguments(parser)
        if command.subcommand_classes:
            register_subcommands([], command, parser)

        return parser

    def _wait_for_termination_if_needed(self, app_ns):
        if app_ns.wait:
            print("\nPress ENTER to continue")
            input("")

    def _print_exception(self, print_bt: bool, exc: BaseException):
        if print_bt:
            print_backtrace()
        else:
            print(f'Exception: {exc} (type: {type(exc).__name__})', file=sys.stderr)


class Application(ApplicationBase):
    def __init__(self, program_name: str,
                 command_class: typing.Optional[typing.Type[Command]],
                 *,
                 enable_short_debug_option: bool = False,
                 ):
        super().__init__(program_name, command_class, enable_short_debug_option=enable_short_debug_option)

    def run(self, args: typing.List[str]):
        ns = argparse.Namespace()
        ns.print_backtraces_ = False
        ns.wait = False
        try:
            command = self._command_class()
            parser = self._create_command_parser(command, self._program_name, register_app_args=True)
            ns = self._create_command_ns(parser, args, command.name, None, single_command=True)

            self._process_debug_opts(ns)
            if self._process_logging_options(ns):
                sys.exit(1)

            log_debug('Starting command', name=self._command_class.name)
            sys.exit(command.run(ns))

        except SystemExit:
            self._wait_for_termination_if_needed(ns)
            raise
        except BaseException as exc:
            self._print_exception(ns.print_backtraces_, exc)
            self._wait_for_termination_if_needed(ns)
            sys.exit(1)


# For compatibility with the 'application' module
SingleCommandApplication = Application
