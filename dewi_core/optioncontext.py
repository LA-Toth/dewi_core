# Copyright 2021-2022 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

import typing
import weakref

import click
from click_option_group import GroupedOption, MutuallyExclusiveOptionGroup, OptionGroup, RequiredAllOptionGroup, \
    optgroup


class _OptionGroupMixin:

    def given_option_with_count(self, ctx: click.Context, opts: dict) -> tuple[set[str], int, int]:
        option_names = set(self.get_option_names(ctx))
        given_option_names = option_names.intersection(opts)
        return given_option_names, len(given_option_names), len(option_names)

    def option_count_requirement_met(self, ctx: click.Context, opts: dict) -> bool:
        for grp in self._extgrp._groups:
            if not grp._option_group().option_count_requirement_met(ctx, opts):
                return False

        return True


class _OptionGroup(OptionGroup, _OptionGroupMixin):
    def __init__(self, name: str | None = None, *,
                 hidden=False, help: str | None = None, extgrp: '_ExtGroup' = None) -> None:
        super().__init__(name, hidden=hidden, help=help)
        self._extgrp = extgrp
        extgrp._set_option_group(self)


class _RequiredAllOptionGroup(RequiredAllOptionGroup, _OptionGroupMixin):
    def __init__(self, name: str | None = None, *,
                 hidden=False, help: str | None = None, extgrp: '_ExtGroup' = None) -> None:
        super().__init__(name, hidden=hidden, help=help)
        self._extgrp = extgrp
        extgrp._set_option_group(self)

    def option_count_requirement_met(self, ctx: click.Context, opts: dict):
        option_names = set(self.get_options(ctx))

        if not _OptionGroupMixin.option_count_requirement_met(self, ctx, opts):
            return False

        return option_names.issubset(opts)

    def handle_parse_result(self, option: GroupedOption, ctx: click.Context, opts: dict) -> None:
        if self._extgrp._option_count_requirement_met(ctx, opts):
            return

        option_names = set(self.get_options(ctx))

        if not option_names.issubset(opts):
            group_name = self._group_name_str()
            required_names = option_names.difference(option_names.intersection(opts))
            option_info = self.get_error_hint(ctx, required_names)

            raise click.UsageError(
                f"Missing required options from {group_name} option group:\n{option_info}",
                ctx=ctx
            )


class _MutuallyExclusiveOptionGroup(MutuallyExclusiveOptionGroup, _OptionGroupMixin):
    def __init__(self, name: str | None = None, *,
                 hidden=False, help: str | None = None, extgrp: '_ExtGroup' = None) -> None:
        super().__init__(name, hidden=hidden, help=help)
        self._extgrp = extgrp
        extgrp._set_option_group(self)

    def option_count_requirement_met(self, ctx: click.Context, opts: dict) -> bool:
        option_names = set(self.get_options(ctx))
        given_option_names = option_names.intersection(opts)
        if len(given_option_names) > 1:
            return False

        if len(given_option_names) == 0:
            count = 0
            for grp in self._extgrp._groups:
                count += int(grp._option_group().option_count_requirement_met(ctx, opts))
            if count > 1:
                return False

        return True

    def handle_parse_result(self, option: GroupedOption, ctx: click.Context, opts: dict) -> None:
        if self._extgrp._option_count_requirement_met(ctx, opts):
            return

        option_names = set(self.get_options(ctx))
        given_option_names = option_names.intersection(opts)
        given_option_count = len(given_option_names)

        for grp in self._extgrp._groups:
            names, given, _ = grp._option_group().given_option_with_count(ctx, opts)
            given_option_count += given
            given_option_names = given_option_names.union(names)

        if given_option_count > 1:
            group_name = self._group_name_str()
            option_info = self.get_error_hint(ctx, given_option_names)

            raise click.UsageError(
                f"Mutually exclusive options from {group_name} option group "
                f"cannot be used at the same time:\n{option_info}",
                ctx=ctx
            )


class _RequiredMutuallyExclusiveOptionGroup(MutuallyExclusiveOptionGroup, _OptionGroupMixin):
    def __init__(self, name: str | None = None, *,
                 hidden=False, help: str | None = None, extgrp: '_ExtGroup' = None) -> None:
        super().__init__(name, hidden=hidden, help=help)
        self._extgrp: _ExtGroup = extgrp
        extgrp._set_option_group(self)

    @property
    def name_extra(self) -> list[str]:
        return super().name_extra + ['required']

    def option_count_requirement_met(self, ctx: click.Context, opts: dict) -> bool:
        option_names = set(self.get_options(ctx))
        given_option_names = option_names.intersection(opts)
        if len(given_option_names) > 1:
            return False

        if len(given_option_names) == 0:
            count = 0
            for grp in self._extgrp._groups:
                count += int(grp._option_group().option_count_requirement_met(ctx, opts))
            if count != 1:
                return False

        return True

    def handle_parse_result(self, option: GroupedOption, ctx: click.Context, opts: dict) -> None:
        if self._extgrp._option_count_requirement_met(ctx, opts):
            return

        super().handle_parse_result(option, ctx, opts)

        option_names = set(self.get_option_names(ctx))
        given_option_names = option_names.intersection(opts)

        for grp in self._extgrp._groups:
            names, given, _ = grp._option_group().given_option_with_count(ctx, opts)
            given_option_names = given_option_names.union(names)

        if len(given_option_names) == 0:
            group_name = self._group_name_str()
            option_info = self.get_error_hint(ctx)
            if self._extgrp._groups:
                option_info += '\n  ' + 'one or more groups, check --help'

            raise click.UsageError(
                "Missing one of the required mutually exclusive options from "
                f"{group_name} option group:\n{option_info}",
                ctx=ctx
            )


class _Base:
    def __init__(self):
        self._callbacks: list[callable] = []
        self._last_callbacks: list[callable] = []

    def _add_option(self, decorator: callable, *args, **kwargs):
        if 'dest' in kwargs:
            args = (*args, kwargs['dest'])
            del kwargs['dest']
        if 'choices' in kwargs:
            kwargs['type'] = click.Choice(kwargs['choices'])
            del kwargs['choices']

        self._callbacks.append(lambda: decorator(*args, **kwargs))

    def add_args_to_func(self, f: callable):
        for c in reversed(self._last_callbacks):
            f = c()(f)
        for c in reversed(self._callbacks):
            f = c()(f)

        return f

    def add_custom_decorator(self, decorator: callable, *dec_args, **dec_kwargs):
        self._callbacks.append(lambda: decorator(*dec_args, **dec_kwargs))


class _Group(_Base):
    def __init__(self, name: str | None = None, *,
                 help: str | None = None,
                 cls: type[OptionGroup] | None = None,
                 **kwargs):
        super().__init__()
        self._cls = cls
        self._callbacks.append(lambda: optgroup.group(name, help=help, cls=cls, **kwargs))

    def add_option(self, *args, **kwargs):
        """@see click_option_group.optgroup.option"""
        self._add_option(optgroup.option, *args, **kwargs)

    def __call__(self, *args, **kwargs):
        return self.add_args_to_func


class _ExtGroup(_Group):
    def __init__(self, name: str | None = None, *,
                 help: str | None = None,
                 cls: type[OptionGroup] | None = None,
                 parent: typing.Optional['_ExtGroup'] = None):
        super().__init__(name, help=help, cls=cls, extgrp=self)
        self._parent = weakref.ref(parent) if parent else None
        self._groups = []
        self._option_group = None

    def _set_option_group(self, o: OptionGroup):
        self._option_group = weakref.ref(o)

    def _option_count_requirement_met(self, ctx: click.Context, opts: dict) -> bool:
        if self._parent:
            return self._parent()._option_count_requirement_met(ctx, opts)
        else:
            return self._option_group().option_count_requirement_met(ctx, opts)


class _ExtOptionGroup(_ExtGroup):
    def __init__(self, name: str | None = None, *,
                 help: str | None = None,
                 cls: type[OptionGroup] | None = None,
                 parent: _ExtGroup | None = None):
        super().__init__(name, help=help, cls=cls, parent=parent)

    def add_mutually_exclusive_group(self, name: str | None = None, *,
                                     help: str | None = None,
                                     required: bool = False
                                     ) -> '_ExtMutuallyExclusiveGroup':
        if self._cls == _RequiredAllOptionGroup:
            required = True
        g = _ExtMutuallyExclusiveGroup(name, help=help,
                                       cls=_RequiredMutuallyExclusiveOptionGroup if required else _MutuallyExclusiveOptionGroup,
                                       parent=self)
        self._last_callbacks.append(g)
        self._groups.append(g)
        return g


class _ExtMutuallyExclusiveGroup(_ExtGroup):
    def __init__(self, name: str | None = None, *,
                 help: str | None = None,
                 cls: type[OptionGroup] | None = None,
                 parent: _ExtGroup | None = None):
        super().__init__(name, help=help, cls=cls, parent=parent)

    def add_group(self, name: str | None = None, *,
                  help: str | None = None, require_all=False) -> '_ExtOptionGroup':
        g = _ExtOptionGroup(name, help=help, cls=_RequiredAllOptionGroup if require_all else _OptionGroup, parent=self)
        self._last_callbacks.append(g)
        self._groups.append(g)
        return g


class OptionContext(_Base):

    def add_option(self, *args, **kwargs):
        """
        @see click.option decorator for details of parameters
        """
        self._add_option(click.option, *args, **kwargs)

    def add_argument(self, *args, **kwargs):
        """
        @see click.argument decorator for details of parameters.

        The help parameter is ignored, it's not supported by click v8,
        but it can be passed to this method.
        """
        if 'help' in kwargs:
            del kwargs['help']
        if 'choices' in kwargs:
            kwargs['type'] = click.Choice(kwargs['choices'])
            del kwargs['choices']

        self._callbacks.append(lambda: click.argument(*args, **kwargs))

    def add_group(self, name: str | None = None, *,
                  help: str | None = None,
                  cls: type[OptionGroup] | None = None) -> _Group:
        g = _Group(name, help=help, cls=cls)
        self._callbacks.append(g)
        return g

    def add_multilevel_group(self, name: str | None = None, *,
                             help: str | None = None, require_all=False) -> _ExtOptionGroup:
        g = _ExtOptionGroup(name, help=help, cls=_RequiredAllOptionGroup if require_all else _OptionGroup)
        self._callbacks.append(g)
        return g

    def add_mutually_exclusive_group(self, name: str | None = None, *,
                                     help: str | None = None,
                                     required: bool = False
                                     ) -> _ExtMutuallyExclusiveGroup:
        g = _ExtMutuallyExclusiveGroup(name, help=help,
                                       cls=_RequiredMutuallyExclusiveOptionGroup if required else _MutuallyExclusiveOptionGroup)
        self._callbacks.append(g)
        return g

    def register_args(self, arg_reg_func: callable):
        arg_reg_func(self)

    def add_args_to_func(self, f: callable):
        for c in reversed(self._callbacks):
            f = c()(f)

        return f
