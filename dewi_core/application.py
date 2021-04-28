# Copyright 2015-2021 Laszlo Attila Toth
# Distributed under the terms of the GNU Lesser General Public License v3

import argparse
import os
import shlex
import sys
import typing

from dewi_core.command import Command
from dewi_core.commandregistry import CommandRegistry
from dewi_core.loader.context import Context
from dewi_core.loader.loader import PluginLoader
from dewi_core.loader.plugin import Plugin
from dewi_core.logger import log_debug, create_logger_from_config, LoggerConfig
from dewi_core.miniapp import ApplicationBase
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
    loader = PluginLoader()
    ctx = loader.load([plugin_name])
    cmd_class = ctx.command_registry.get_command_class_descriptor(ns.running_command_).get_class()

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


class EmptyPlugin(Plugin):
    """Default plugin which does nothing"""

    def load(self, c: Context):
        pass


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
        context: Context = args.context_
        _list_commands(args.program_name_, context.command_registry, all_commands=True)


class _ListCommand(Command):
    name = 'list'
    description = 'Lists all available command with their names only'

    def run(self, args: argparse.Namespace):
        context: Context = args.context_
        _list_commands(args.program_name_, context.command_registry)


class Application(ApplicationBase):
    def __init__(self, loader: PluginLoader, program_name: str, *,
                 fallback_to_plugin_name: typing.Optional[str] = None,
                 disable_plugins_from_cmdline: typing.Optional[bool] = None,
                 command_class: typing.Optional[typing.Type[Command]] = None
                 ):
        super().__init__(program_name, command_class, enable_short_debug_option=True)
        self._loader = loader
        self._fallback_plugin_name = fallback_to_plugin_name or 'dewi_core.application.EmptyPlugin'
        self._disable_plugins_from_cmdline = disable_plugins_from_cmdline

    def _parse_app_args(self, args: typing.List[str]):
        parser = argparse.ArgumentParser(
            prog=self._program_name,
            usage='%(prog)s [options] [command [command-args]]')

        if not self._disable_plugins_from_cmdline:
            parser.add_argument(
                '-p', '--plugin', help='Load this plugin. This option can be specified more than once.',
                default=[], action='append')

        self._register_base_app_args(parser)

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
                ns = self._create_command_ns(parser, app_ns.commandargs, command.name, context,
                                             self._command_class is not None)
                ns.debug_ = app_ns.debug_
                ns.cmd_class_ = command_class

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
            self._print_exception(app_ns.print_backtraces_, exc)
            self._wait_for_termination_if_needed(app_ns)
            sys.exit(1)

    def _update_args_from_custom_env_var(self, args: typing.List[str]):
        args_ = []
        env_var_name = f'{self._program_name.replace("-", "_").upper()}_ARGS'
        if env_var_name in os.environ:
            args_ = shlex.split(os.environ[env_var_name])
        args_ += [self._command_class.name] + args
        args = args_
        return args

    def _process_logging_options(self, args: argparse.Namespace):
        return create_logger_from_config(
            LoggerConfig.create(self._program_name, args.log_level, args.log_none, args.log_syslog, args.log_console,
                                args.log_file))

    def _get_plugin_names(self, app_ns: argparse.Namespace):
        if self._disable_plugins_from_cmdline:
            plugins = [self._fallback_plugin_name]
        else:
            plugins = app_ns.plugin or [self._fallback_plugin_name]
        return plugins


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
