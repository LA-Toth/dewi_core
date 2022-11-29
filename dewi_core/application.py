#  Copyright 2015-2022, Laszlo Attila Toth
#  Distributed under the terms of the Apache License, Version 2.0

import os
import sys
import time

import click

from dewi_core.appcontext import ApplicationContext
from dewi_core.command import Command
from dewi_core.commandregistry import CommandRegistry
from dewi_core.config.node import Node
from dewi_core.config_env import ConfigDirRegistry, EnvConfig
from dewi_core.loader.loader import PluginLoader
from dewi_core.logger import LogLevel, LoggerConfig, log_debug, set_global_logger_from_config
from dewi_core.optioncontext import OptionContext
from dewi_core.utils.exception import print_backtrace
from dewi_core.utils.levenshtein import get_similar_names_to
from dewi_core.utils.time import humanize_time

try:
    from click._unicodefun import _verify_python_env


    def _dummy():
        pass


    # the UTF-8 check is buggy, ignore it
    _verify_python_env.__code__ = _dummy.__code__
except ImportError:
    pass

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


class AliasedGroup(click.Group):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._command_registry: CommandRegistry = CommandRegistry()

    def get_command(self, ctx, cmd_name):
        if cmd_name in self._command_registry:
            ctx.invoked_subcommand_ = cmd_name
            return super().get_command(ctx,
                                       self._command_registry.get_command_class_descriptor(cmd_name).get_class().name)
        elif not self._command_registry.get_command_count():
            rv = super().get_command(ctx, cmd_name)
            if rv is not None:
                return rv
            else:
                ctx.fail(f'Unknown command name {cmd_name}')

        print(f"ERROR: The command '{cmd_name}' is not known.\n")
        similar_names = get_similar_names_to(cmd_name, sorted(self._command_registry.get_command_names()))

        print('Similar names - firstly based on command name length:')
        for name in similar_names:
            print('  {:30s}   -- {}'.format(
                name,
                self._command_registry.get_command_class_descriptor(name).get_class().description))

        return click.core.Command('dummy', callback=lambda: sys.exit(1))

    def resolve_command(self, ctx, args):
        # always return the full command name
        _, cmd, args = super().resolve_command(ctx, args)
        return cmd.name, cmd, args

    def add_command(self, cmd, name=None):
        if hasattr(cmd.callback, 'command_class'):
            self._command_registry.register_class(cmd.callback.command_class)

        super().add_command(cmd, name)


def _wait_for_termination_if_needed(ctx: ApplicationContext):
    if 'wait' in ctx.args and ctx.args.wait:
        print("\nPress ENTER to continue")
        input("")


def _print_exception(ctx: ApplicationContext, exc: BaseException):
    print_bt = 'print_backtraces' in ctx.args and ctx.args.print_backtraces
    if print_bt or os.environ.get('DEWI_DEBUG', 0) == '1':
        print_backtrace()
    print(f'Exception: {exc} (type: {type(exc).__name__})', file=sys.stderr)


def _app_main(parent_cls):
    def app_main(self, *args, **kwargs):
        start = end = 0

        def print_run_time():
            nonlocal end
            end = time.time()
            if os.environ.get('DEWI_SHOW_RUN_TIME', '0') == '1':
                diff = int((end - start) * 100) / 100
                print(f'Runtime: {humanize_time(end - start, format=True)} ({diff:2} seconds)')

        start = time.time()
        try:
            parent_cls.main(self, *args, **kwargs)
        except SystemExit:
            print_run_time()
            _wait_for_termination_if_needed(self.callback.app_context)
            raise
        except BaseException as exc:
            print_run_time()
            _print_exception(self.callback.app_context, exc)
        _wait_for_termination_if_needed(self.callback.app_context)
        sys.exit(1)

    return app_main


class AppGroup(AliasedGroup):
    main = _app_main(AliasedGroup)


class AppCommand(click.Command):
    main = _app_main(click.Command)


def get_invoked_subommand(ctx: click.Context):
    if hasattr(ctx, 'invoked_subcommand_'):
        return ctx.invoked_subcommand_
    else:
        return ctx.invoked_subcommand


def get_command_from_plugin_appcontext(plugin_name: str, ctx: ApplicationContext) -> type[Command]:
    """
    Returns the command  class specified in the ctx ApplicationContext via its running_command_
    and running_subcommands_ members.

    The ns comes from an already parsed namespace, especially via
    dewi_core.remoting.serialize_argparse_namespace and deserialize_argparse_namespace methods.

    The command must exist.

    :param plugin_name: The command plugin or app plugin containing the command referrered in ctx
    :param ctx: the prepared ApplicationContext object
    :return: the command class based on ctx.
    """
    command_registry = CommandRegistry()
    cfg_dir_registry = ConfigDirRegistry(EnvConfig(ctx.environment))
    cfg_dir_registry.register_config_directories(ctx.config_directories)
    loader = PluginLoader(command_registry, cfg_dir_registry)
    loader.load([plugin_name])
    cfg_dir_registry.load_env()
    cmd_class = command_registry.get_command_class_descriptor(ctx.command_names.command).get_class()

    if ctx.command_names.subcommands:
        for sub_cmd_name in ctx.command_names.subcommands:
            for cc in cmd_class.subcommand_classes:
                if cc.name == sub_cmd_name:
                    cmd_class = cc

    return cmd_class


def run_command_from_appcontext(plugin_name: str, ctx: ApplicationContext) -> int | None:
    """
    Runs the command returned by get_command_from_plugin_appcontext(). See that function.
    """
    return get_command_from_plugin_appcontext(plugin_name, ctx)().run(ctx)


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

    def run(self, ctx: ApplicationContext):
        _list_commands(ctx.program_name, ctx.command_registry, all_commands=True)


class _ListCommand(Command):
    name = 'list'
    description = 'Lists all available command with their names only'

    def run(self, ctx: ApplicationContext):
        _list_commands(ctx.program_name, ctx.command_registry)


class Application:
    _program_name: str
    _command_class: type[Command] | None
    _description: str | None
    _enable_short_debug_option: bool | None
    _enable_env_options: bool | None
    _version: str | None
    _command_registry: CommandRegistry
    _command_classes: set[type[Command]]
    _env_config: EnvConfig
    _config_dir_registry: ConfigDirRegistry
    DEFAULT_ENV = 'development'

    def __init__(self, program_name: str,
                 command_class: type[Command] | None = None,
                 *,
                 description: str | None = None,
                 enable_short_debug_option: bool = False,
                 enable_env_options: bool = True,
                 version: str | None = None
                 ):
        self._program_name = program_name
        self._command_class = command_class
        self._description = description
        self._enable_short_debug_option = enable_short_debug_option if command_class is not None else True
        self._enable_env_options = enable_env_options if command_class is not None else True
        self._version = version
        self._command_registry = CommandRegistry()
        self._command_classes = set()
        self._env_config = EnvConfig(os.environ.get('DEWI_ENV', self.DEFAULT_ENV))
        self._config_dir_registry = ConfigDirRegistry(self._env_config)

        if command_class:
            self._command_classes.add(command_class)
            self._command_registry.register_class(command_class)

    def add_command_class(self, command_class: type[Command]):
        self._command_classes.add(command_class)
        self._command_registry.register_class(command_class)

    def add_command_classes(self, command_classes: list[type[Command]]):
        for command_class in command_classes:
            self.add_command_class(command_class)

    def load_plugin(self, name: str):
        self.load_plugins([name])

    def load_plugins(self, names: list[str]):
        try:
            loader = PluginLoader(self._command_registry, self._config_dir_registry)
            loader.load(names)
        except BaseException as exc:
            _print_exception(ApplicationContext(), exc)
            sys.exit(1)

    def register_config_directory(self, directory: str):
        self.register_config_directories([directory])

    def register_config_directories(self, directories: list[str]):
        self._config_dir_registry.register_config_directories(directories)

    def run(self, args: list[str] | None = None):
        single_command_mode = bool(self._command_class and len(self._command_classes) == 1)

        app_context = ApplicationContext()
        app_context.single_command_mode = single_command_mode
        app_context.config_directories = list(self._config_dir_registry.config_directories)
        app_context.environment = self._env_config.current_env

        @click.pass_context
        def app_run(ctx: click.Context, *args, **kwargs):
            app_context.add_cmd_args('__main__', ctx.params, self._command_class.name if single_command_mode else '')
            app_context.command_names.invoked_subcommand = get_invoked_subommand(ctx)
            app_context.command_names.invoked_subcommand_primary_name = ctx.invoked_subcommand
            app_context.current_args = Node.create_from(ctx.params)
            ctx.obj = app_context
            ctx.obj.command_registry = self._command_registry
            ctx.obj.program_name = self._program_name
            for k, v in kwargs.items():
                ctx.obj.add_arg(k, v)
            self._process_debug_opts(ctx.obj.args)
            if self._process_logging_options(ctx.obj.args):
                sys.exit(1)

            if self._enable_env_options and ctx.obj.args.environment:
                self._env_config.set_current_env(ctx.obj.args.environment)

            self._load_env()

            if app_context.args.cwd:
                os.chdir(app_context.args.cwd)

            if single_command_mode:
                app_context.command_names.current = self._command_class.name
                res = self._command_class().run(app_context)
                if ctx.invoked_subcommand is None or res:
                    ctx.exit(res)

        app_run.app_context = app_context

        app_opt_ctx = OptionContext()
        app_opt_ctx.register_args(self._register_app_args)
        if single_command_mode:
            app_opt_ctx.register_args(self._command_class.register_arguments)

        try:
            app_run = app_opt_ctx.add_args_to_func(app_run)
        except Exception as e:
            if single_command_mode:
                suffix = f'for command `{self._command_class.name}`'
            else:
                suffix = 'for the application'
            print(f'Error occurred while registering args {suffix}: {e}')
            raise

        if single_command_mode:
            has_classes = len(self._command_class.subcommand_classes) > 0
            app_run = (click.group if has_classes else click.command)(
                self._program_name,
                help=self._description or self._command_class.description,
                context_settings=CONTEXT_SETTINGS,
                cls=(AppGroup if has_classes else AppCommand))(app_run)
            self._register_subcommands(self._command_class.subcommand_classes, app_run, app_context)
        else:
            self._command_registry.register_class(_ListAllCommand)
            self._command_registry.register_class(_ListCommand)

            app_run = click.group(self._program_name, cls=AppGroup,
                                  help=self._description,
                                  context_settings=CONTEXT_SETTINGS,
                                  )(app_run)
            self._register_subcommands(self._command_registry._command_classes, app_run, app_context)

        return app_run(args, self._program_name)

    def _register_subcommands(self, command_classes, parent_run_cmd, app_context: ApplicationContext):
        for command_class in command_classes:
            def wrapper():
                c = command_class

                @click.pass_context
                def r(ctx: click.Context, *_, **kwargs):
                    app_context.add_cmd_args(ctx.info_name, ctx.params)
                    app_context.command_names.current = get_invoked_subommand(ctx.parent)
                    app_context.command_names.invoked_subcommand = get_invoked_subommand(ctx)
                    app_context.command_names.invoked_subcommand_primary_name = ctx.invoked_subcommand
                    app_context.current_args = Node.create_from(ctx.params)
                    for k, v in kwargs.items():
                        ctx.obj.add_arg(k, v)

                    log_debug('Starting command', name=c.name)
                    res = c().run(ctx.obj)
                    if ctx.invoked_subcommand is None or res:
                        ctx.exit(res)

                r.command_class = c

                return r

            try:
                cmd_opt_ctx = OptionContext()
                cmd_opt_ctx.register_args(command_class.register_arguments)
                cls = AliasedGroup if command_class.subcommand_classes else click.core.Command
                cmd_run = parent_run_cmd.command(name=command_class.name, help=command_class.description, cls=cls,
                                                 context_settings=CONTEXT_SETTINGS)(
                    cmd_opt_ctx.add_args_to_func(wrapper()))
                self._register_subcommands(command_class.subcommand_classes, cmd_run, app_context)
            except Exception as e:
                print(f'Error occurred while registering args for command `{command_class.name}`: {e}')
                raise

    def _register_app_args(self, h: OptionContext):
        if self._version:
            h.add_custom_decorator(lambda: click.version_option(self._version))

        h.add_option('--cwd', dest='cwd', help='Change to specified directory')
        h.add_option('--wait', is_flag=True, help='Wait for user input before terminating application')
        h.add_option(
            '--print-backtraces', dest='print_backtraces', is_flag=True,
            help='Print backtraces of the exceptions')

        debug_opts = ['--debug']
        if self._enable_short_debug_option:
            debug_opts.insert(0, '-d')
        h.add_option(*debug_opts, dest='debug', is_flag=True, help='Enable print/log debug messages')
        if self._enable_env_options:
            h.add_option('-e', '--environment', dest='environment',
                         help=f'Specifies the environment to run the app '
                              f'under ({"/".join(sorted(self._env_config.available_envs))})')

        logging = h.add_group('Logging')
        logging.add_option('--log-level', dest='log_level', help='Set log level, default: warning',
                           type=click.Choice([i.name.lower() for i in LogLevel]), default='info')
        logging.add_option('--log-syslog', dest='log_syslog', is_flag=True,
                           help='Log to syslog. Can be combined with other log targets')
        logging.add_option('--log-console', '--log-stdout', dest='log_console', is_flag=True,
                           help='Log to STDOUT, the console. Can be combined with other targets.'
                                'If no target is specified, this is used as default.')
        logging.add_option('--log-file', dest='log_file', multiple=True,
                           help='Log to a file. Can be specified multiple times and '
                                'can be combined with other options.')
        logging.add_option('--no-log', '-l', dest='log_none', is_flag=True,
                           help='Disable logging. If this is set, other targets are invalid.')

    def _process_debug_opts(self, ns: Node):
        if ns.debug or os.environ.get('DEWI_DEBUG', 0) == '1':
            ns.print_backtraces = True
            ns.log_level = 'debug'
            ns.debug_ = True

    def _process_logging_options(self, args: Node):
        return set_global_logger_from_config(
            LoggerConfig.create(name=self._program_name, level=args.log_level,
                                log_none=args.log_none, log_syslog=args.log_syslog,
                                log_console=args.log_console, log_file=args.log_file))

    def _load_env(self):
        self._config_dir_registry.load_env()
