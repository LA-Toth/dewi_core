# Copyright 2018-2022 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

import enum
import logging
import logging.handlers
import sys
import threading

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
    name: str
    level: str
    log_none: bool
    log_syslog: bool
    log_console: bool
    log_file: list[str] | None

    def __init__(self):
        self.name = ''
        self.level = ''
        self.log_none = False
        self.log_syslog = False
        self.log_console = False
        self.log_file = []

    def duplicate_with_name(self, name: str) -> 'LoggerConfig':
        return self.create(name=name, level=self.level,
                           log_none=self.log_none, log_syslog=self.log_syslog,
                           log_console=self.log_console, log_file=self.log_file)


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
    def create_handler(cls, logger_type: LoggerType, *, filename: str | None = None):
        if logger_type == LoggerType.CONSOLE:
            return cls.create_console_handler()
        if logger_type == LoggerType.SYSLOG:
            return cls.create_syslog_handler()
        if logger_type == LoggerType.FILE:
            return cls.create_file_handler(filename)
        # same as: logger_type == LoggerType.NONE:
        return cls.create_null_handler()


def _format_message(message: str, args: dict) -> str:
    if not args:
        return message + ';'

    return '{}; {}'.format(message, ', '.join(f'{k}={v!r}' for k, v in args.items()))


class Logger:
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR

    CRITICAL = logging.CRITICAL

    def __init__(self, name: str, logger_types: list[LoggerType], *, filenames: list[str] = None):
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


_loggers: dict[str, Logger] = {}
_loggers_lock = threading.Lock()


def create_logger(name: str, logger_types: LoggerType | list[LoggerType], log_level: str = 'info',
                  *,
                  filenames: list[str] | None = None):
    if isinstance(logger_types, LoggerType):
        logger_types = [logger_types]

    try:
        _loggers_lock.acquire()
        if name in _loggers:
            return _loggers[name]

        logger = Logger(name, logger_types, filenames=filenames or [])
        _loggers[name] = logger
    finally:
        _loggers_lock.release()

    logger.set_level(LogLevel.from_string(log_level))

    return logger


def create_null_logger(name: str) -> Logger:
    logger = Logger(name, [LoggerType.NONE], filenames=[])
    logger.set_level(LogLevel.INFO)
    return logger


def _create_logger_from_config(config: LoggerConfig) -> Logger:
    if config.log_none:
        if config.log_syslog or config.log_file or config.log_console:
            print('ERROR: log_none cannot be used any other log target,', file=sys.stderr)
            print('ERROR: none of: log_file, --log_console, log_syslog', file=sys.stderr)
            raise Exception("Invalid logger config")
        return create_logger(config.name, LoggerType.NONE, config.level, filenames=[])
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

        return create_logger(config.name, logger_types, config.level, filenames=config.log_file)


def set_global_logger_from_config(config: LoggerConfig) -> int:
    if config.log_none:
        if config.log_syslog or config.log_file or config.log_console:
            print('ERROR: --log-none cannot be used any other log target,')
            print('ERROR: none of: --log-file, --log-console, --log-syslog')
            return 1

    global _logger
    _logger = _create_logger_from_config(config)

    global _config
    if _config is None:
        _config = config

    return 0


def create_logger_based_on_global_config(name: str) -> Logger:
    global _config
    if _config is None:
        return create_null_logger(name)
    return _create_logger_from_config(_config.duplicate_with_name(name))


def create_logger_for(obj: type | object, module_name_part_count: int = 1) -> Logger:
    """Get a new logger from already initialized config; either for an object or for its __class__.
    @see #get_logger_for_class()"""
    return create_logger_for_class(
        obj if isinstance(obj, type) else obj.__class__,
        module_name_part_count)


def create_logger_for_class(klass: type, module_name_part_count: int = 1) -> Logger:
    """
    Get a new logger for the specified `klass` type based on the previously stored config (first call
    of create_logger_from_config()).
    The module_name_part_count specifies the amount of the module name to be added; or none if it's 0.

    Eg. m1.m2.m3.MyClass => cnt = 1: name m3.MyClass;
    cnt: 2: m2.m3.MyClass
    cnt: 3 or more : m1.m2.m3.MyClass
    and if 0: MyClass
    """
    name = klass.__name__
    if module_name_part_count:
        name = '.'.join(klass.__module__
                        .rsplit('.', module_name_part_count)[-module_name_part_count:]) \
               + '.' + name
    return create_logger_based_on_global_config(name)


def log_debug(*args, **kwargs):
    _logger.debug(*args, **kwargs)


def log_info(*args, **kwargs):
    _logger.info(*args, **kwargs)


def log_warning(*args, **kwargs):
    _logger.warning(*args, **kwargs)


def log_error(*args, **kwargs):
    _logger.error(*args, **kwargs)


def log_critical(*args, **kwargs):
    _logger.critical(*args, **kwargs)


def log_enabled_for(level: LogLevel):
    _logger.enabled_for(level)


# NOTE: ensure that log_*() can be called without explicitly
# calling create_logger()
_logger = create_null_logger('_main_')
_config: LoggerConfig = None
