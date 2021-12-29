# Copyright 2018-2021 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

import enum
import logging
import logging.handlers
import sys
import typing

from dewi_core.config.node import Node
from dewi_core.utils.dictionaries import sort_dict


class LoggerType(enum.Enum):
    SYSLOG = enum.auto()
    CONSOLE = enum.auto()
    FILE = enum.auto()
    NONE = enum.auto()


class LogLevel(enum.Enum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL

    def __str__(self):
        return self.name.lower()

    @staticmethod
    def from_string(s: str):
        try:
            return LogLevel[s.upper()]
        except KeyError as exc:
            raise ValueError(exc)


class LoggerConfig(Node):
    def __init__(self):
        self.name: str = ''
        self.level: str = ''
        self.log_none: bool = False
        self.log_syslog: bool = False
        self.log_console: bool = False
        self.log_file: typing.Optional[typing.List[str]] = []

    @classmethod
    def create(cls, name: str, level: str, log_none: bool, log_syslog: bool, log_console: bool,
               log_file: typing.Optional[typing.List[str]]):
        c = cls()
        c.name = name
        c.level = level
        c.log_none = log_none
        c.log_syslog = log_syslog
        c.log_console = log_console
        c.log_file = log_file
        return c


class _Handlers:
    CONSOLE_FORMAT = '%(asctime)s %(name)s %(levelname)s %(message)s'
    SYSLOG_FORMAT = '%(name)s[%(process)d]: %(message)s'
    DATE_FIELD_FORMAT = '%Y-%m-%dT%H:%M:%S%z'

    @classmethod
    def create_syslog_handler(cls):
        if sys.platform == "darwin":
            address = "/var/run/syslog"
        else:
            address = ('localhost', 514)

        handler = logging.handlers.SysLogHandler(
            address=address,
            facility=logging.handlers.SysLogHandler.LOG_LOCAL0,
        )

        handler.setFormatter(logging.Formatter(cls.SYSLOG_FORMAT, datefmt=cls.DATE_FIELD_FORMAT))

        return handler

    @classmethod
    def create_console_handler(cls):
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(cls.CONSOLE_FORMAT, datefmt=cls.DATE_FIELD_FORMAT))

        return handler

    @classmethod
    def create_file_handler(cls, filename: str):
        handler = logging.FileHandler(filename)
        handler.setFormatter(logging.Formatter(cls.CONSOLE_FORMAT, datefmt=cls.DATE_FIELD_FORMAT))

        return handler

    @classmethod
    def create_null_handler(cls):
        return logging.NullHandler()

    @classmethod
    def create_handler(cls, logger_type: LoggerType, *, filename: typing.Optional[str] = None):
        if logger_type == LoggerType.CONSOLE:
            return cls.create_console_handler()
        if logger_type == LoggerType.SYSLOG:
            return cls.create_syslog_handler()
        if logger_type == LoggerType.FILE:
            return cls.create_file_handler(filename)
        # same as: logger_type == LoggerType.NONE:
        return cls.create_null_handler()


def _format_message(message: str, args: typing.Dict) -> str:
    if not args:
        return message + ';'

    return '{}; {}'.format(message, ', '.join(f'{k}={v!r}' for k, v in args.items()))


class Logger:
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR

    CRITICAL = logging.CRITICAL

    def __init__(self, name: str, logger_types: typing.List[LoggerType], *, filenames: typing.List[str] = None):
        self._logger = logging.getLogger(name)

        if LoggerType.NONE in logger_types:
            self._logger.addHandler(_Handlers.create_handler(LoggerType.NONE))
        else:
            for lt in logger_types:
                if lt == LoggerType.FILE:
                    for filename in filenames:
                        self._logger.addHandler(_Handlers.create_handler(LoggerType.FILE, filename=filename))
                else:
                    self._logger.addHandler(_Handlers.create_handler(lt))

    def set_level(self, level: LogLevel):
        self._logger.setLevel(level.value)

    def log(self, level: int, message: str, *args, **kwargs):
        if args:
            kwargs.update(args[0])
        args = sort_dict(kwargs)
        message_with_args = _format_message(message, args)
        self._logger.log(level, message_with_args)

    def debug(self, *args, **kwargs):
        self.log(self.DEBUG, *args, **kwargs)

    def info(self, *args, **kwargs):
        self.log(self.INFO, *args, **kwargs)

    def warning(self, *args, **kwargs):
        self.log(self.WARNING, *args, **kwargs)

    def error(self, *args, **kwargs):
        self.log(self.ERROR, *args, **kwargs)

    def critical(self, *args, **kwargs):
        self.log(self.CRITICAL, *args, **kwargs)

    def enabled_for(self, level: LogLevel) -> bool:
        return self._logger.isEnabledFor(level.value)


logger: Logger = None


def create_logger(name: str, logger_types: typing.Union[LoggerType, typing.List[LoggerType]], log_level: str = 'info',
                  *,
                  filenames: typing.Optional[typing.List[str]] = None):
    global logger  # pylint:disable=C0103

    if isinstance(logger_types, LoggerType):
        logger_types = [logger_types]

    logger = Logger(name, logger_types, filenames=filenames or [])
    logger.set_level(LogLevel.from_string(log_level))


def create_logger_from_config(config: LoggerConfig) -> int:
    if config.log_none:
        if config.log_syslog or config.log_file or config.log_console:
            print('ERROR: --log-none cannot be used any other log target,')
            print('ERROR: none of: --log-file, --log-console, --log-syslog')
            return 1
        create_logger(config.name, LoggerType.NONE, config.level, filenames=[])
    else:
        logger_types = []
        if config.log_console:
            logger_types.append(LoggerType.CONSOLE)
        if config.log_file:
            logger_types.append(LoggerType.FILE)
        if config.log_syslog:
            logger_types.append(LoggerType.SYSLOG)

        if not logger_types:
            # Using default logger
            logger_types = LoggerType.CONSOLE

        create_logger(config.name, logger_types, config.level, filenames=config.log_file)

    return 0


def log_debug(*args, **kwargs):
    logger.debug(*args, **kwargs)


def log_info(*args, **kwargs):
    logger.info(*args, **kwargs)


def log_warning(*args, **kwargs):
    logger.warning(*args, **kwargs)


def log_error(*args, **kwargs):
    logger.error(*args, **kwargs)


def log_critical(*args, **kwargs):
    logger.critical(*args, **kwargs)


def log_enabled_for(level: LogLevel):
    logger.enabled_for(level)


# NOTE: ensure that log_*() can be called without explicitly
# calling create_logger()
create_logger('_main_', LoggerType.NONE, 'info')
