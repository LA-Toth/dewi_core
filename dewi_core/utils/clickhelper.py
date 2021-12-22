# Copyright 2015-2021 Laszlo Attila Toth
# Distributed under the terms of the GNU Lesser General Public License v3

import typing
from typing import Optional, Type

import click
from click._unicodefun import _verify_python_env
from click_option_group import optgroup, OptionGroup, MutuallyExclusiveOptionGroup, RequiredMutuallyExclusiveOptionGroup


def _dummy():
    pass


_verify_python_env.__code__ = _dummy.__code__


class _Base:
    def __init__(self):
        self._callbacks: typing.List[callable] = []

    def add_args_to_func(self, f: callable):
        for c in reversed(self._callbacks):
            f = c()(f)

        return f


class _Group(_Base):
    def __init__(self, name: Optional[str] = None, *,
                 help: Optional[str] = None,
                 cls: Optional[Type[OptionGroup]] = None):
        super().__init__()
        self._callbacks.append(lambda: optgroup.group(name, help=help, cls=cls))

    def add_option(self, *args, **kwargs):
        """@see click_option_group.optgroup.option"""
        self._callbacks.append(lambda: optgroup.option(*args, **kwargs))

    def __call__(self, *args, **kwargs):
        return self.add_args_to_func


class ClickHelper(_Base):

    def add_option(self, *args, **kwargs):
        """
        @see click.option decorator for details of parameters
        """
        self._callbacks.append(lambda: click.option(*args, **kwargs))

    def add_argument(self, *args, **kwargs):
        """
        @see click.argument decorator for details of parameters
        """
        self._callbacks.append(lambda: click.argument(*args, **kwargs))

    def add_group(self, name: Optional[str] = None, *,
                  help: Optional[str] = None,
                  cls: Optional[Type[OptionGroup]] = None) -> _Group:
        g = _Group(name, help=help, cls=cls)
        self._callbacks.append(g)
        return g

    def add_mutually_exclusive_group(self, name: Optional[str] = None, *,
                                     help: Optional[str] = None,
                                     required: bool = False
                                     ):
        self.add_group(name, help=help,
                       cls=RequiredMutuallyExclusiveOptionGroup if required else MutuallyExclusiveOptionGroup)

    def add_custom_decorator(self, decorator: callable, *dec_args, **dec_kwargs):
        self._callbacks.append(lambda: decorator(*dec_args, **dec_kwargs))

    def register_args(self, arg_reg_func: callable):
        arg_reg_func(self)

    def add_args_to_func(self, f: callable):
        for c in reversed(self._callbacks):
            f = c()(f)

        return f
