# Copyright 2015-2021 Laszlo Attila Toth
# Distributed under the terms of the GNU Lesser General Public License v3

import argparse
import os
import sys
import typing

from dewi_core.command import Command, register_subcommands
from dewi_core.logger import LogLevel, log_debug, create_logger_from_config, LoggerConfig
from dewi_core.utils.exception import print_backtrace


class Application:
    def __init__(self, program_name: str,
                 command_class: typing.Optional[typing.Type[Command]],
                 *,
                 enable_short_debug_option: bool = False,
                 ):
        self._program_name = program_name
        self._command_class = command_class
        self._enable_short_debug_option = enable_short_debug_option

    def run(self, args: typing.List[str]):
        ns = argparse.Namespace()
        ns.print_backtraces_ = False
        ns.wait = False
        try:
            command = self._command_class()

            parser = self._create_command_parser(command)
            ns = parser.parse_args(args)
            ns.running_command_ = self._command_class.name
            ns.parser_ = parser
            ns.context_ = None
            ns.program_name_ = self._program_name
            ns.single_command_ = True

            self._process_debug_opts(ns)
            if self._process_logging_options(ns):
                sys.exit(1)

            log_debug('Starting command', name=self._command_class.name)
            sys.exit(command.run(ns))

        except SystemExit:
            self._wait_for_termination_if_needed(ns)
            raise
        except BaseException as exc:
            if ns.print_backtraces_:
                print_backtrace()
            print(f'Exception: {exc} (type: {type(exc).__name__})', file=sys.stderr)
            self._wait_for_termination_if_needed(ns)
            sys.exit(1)

    def _register_app_args(self, parser: argparse.ArgumentParser):
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

    def _create_command_parser(self, command: Command):
        parser = argparse.ArgumentParser(
            description=command.description,
            prog=self._program_name)
        parser.set_defaults(running_subcommands_=[])
        self._register_app_args(parser)
        command.register_arguments(parser)
        if command.subcommand_classes:
            register_subcommands([], command, parser)

        return parser

    def _wait_for_termination_if_needed(self, app_ns):
        if app_ns.wait:
            print("\nPress ENTER to continue")
            input("")


# For compatibility with the 'application' module
SingleCommandApplication = Application
