# Copyright 2021 Laszlo Attila Toth
# Distributed under the terms of the GNU Lesser General Public License v3

import argparse
import copy
import typing


def serialize_argparse_namespace(ns: argparse.Namespace,
                                 app_specific_keys: typing.Optional[typing.List[str]] = None) \
        -> typing.Dict[str, typing.Any]:
    return copy.deepcopy({k: v for k, v in ns.__dict__.items() if
                          k not in ['func', 'parser_', 'context_', 'cmd_remote'] + (app_specific_keys or [])})


def deserialize_argparse_namespace(args: typing.Dict[str, typing.Any]) -> argparse.Namespace:
    ns = argparse.Namespace()
    for k, v in args.items():
        setattr(ns, k, v)
    return ns
