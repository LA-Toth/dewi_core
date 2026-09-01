# Copyright 2018-2026 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

import os
import sys

import yaml

from dewi_dataclass.serialization import convert

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

if os.environ.get('DEWI_YAML_WITHOUT_ALIASES', '0') != '0':
    yaml.Dumper.ignore_aliases = lambda *args: True


def save_to_yaml(data, output_file: str | None = None):
    """
    Saves (dumps) data as YAML into the specified file or to the standard output.

    The data is converted to plain Python types first, so a DataClass or a
    DataList is written as a mapping or a sequence — wherever it sits, including
    inside a plain list or dict.

    :param data: The data to be stored as YAML file or text
    :param output_file: The output filename. If it is '-' or None (default), the standard output is used
    """
    data = convert(data)

    if not output_file or output_file == '-':
        yaml.dump(data, stream=sys.stdout, indent=4, default_flow_style=False)
    else:
        with open(output_file, 'wt', encoding='UTF-8') as f:
            yaml.dump(data, stream=f, indent=4, default_flow_style=False)


def print_as_yaml(cfg):
    save_to_yaml(cfg, '-')


def load_yaml(filename: str):
    """
    Loads a YAML file written by save_to_yaml().

    Uses the full loader, not safe_load(), so a value that only YAML's Python
    tags can express — an Enum member, for instance — is reconstructed. Do not
    point this at a file from an untrusted source.
    """
    with open(filename) as f:
        return yaml.load(f, Loader)
