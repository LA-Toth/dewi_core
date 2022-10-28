# Copyright 2015-2022 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

import sys
import traceback
import typing


def print_backtrace(tbe: typing.Optional[traceback.TracebackException] = None):
    print(format_backtrace(tbe))


def format_backtrace(tbe: typing.Optional[traceback.TracebackException] = None) -> str:
    tbe = tbe or traceback.TracebackException(*sys.exc_info())
    return f'Exception occurred:\n  Type: {tbe.exc_type.__name__}\n  Message: {tbe}\n\n' \
           + '* Details - First exception:\n' + _format_traceback_exception(tbe)


def _format_traceback_exception(exc: traceback.TracebackException, prefix: str | None = None):
    tb_str = ''

    if exc.__cause__ is not None:
        tb_str += _format_traceback_exception(
            exc.__cause__,
            '\n* The above exception was the direct cause of the following exception:')
    elif exc.__context__ is not None and not exc.__suppress_context__:
        tb_str += _format_traceback_exception(
            exc.__context__,
            '\n* During handling of the above exception, another exception occurred')
    return tb_str + _format_single_traceback(exc, prefix)


def _format_single_traceback(exc: traceback.TracebackException, prefix: str | None = None):
    tb_str = f'  Type: {exc.exc_type.__name__}\n  Message: {exc}\n\n'
    for tb in exc.stack:
        tb_str += '  File %s:%s in %s\n    %s\n' % (tb.filename, tb.lineno, tb.name, tb.line)
    if prefix:
        tb_str += f'{prefix}\n'
    return tb_str
