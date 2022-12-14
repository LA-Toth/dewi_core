# Copyright 2018-2022 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

import os
import sys

import yaml

from dewi_dataclass import DataClass, DataList

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

if os.environ.get('DEWI_YAML_WITHOUT_ALIASES', '0') != '0':
    yaml.Dumper.ignore_aliases = lambda *args: True


def _represent_node(dumper: yaml.dumper.Dumper, data: DataClass):
    return dumper.represent_dict(data)


def _represent_node_list(dumper: yaml.dumper.Dumper, data: DataList):
    return dumper.represent_list(data)


def register_dataclass_representers():
    yaml.add_multi_representer(DataClass, _represent_node)
    yaml.add_multi_representer(DataList, _represent_node_list)


def save_to_yaml(data, output_file: str | None = None, *, convert_dataclass=True):
    """
    Saves (dumps) data (dict, list, etc.) as YAML into the specified file or to the standard output.
    :param data: The data to be stored as YAML file or text
    :param output_file: The output filename. If it is '-' or None (default), the standard output is used
    :param convert_dataclass: a Node (DataClass) is converted by as_dict() if True, serialized directly otherwise
    """
    if convert_dataclass and isinstance(data, DataClass):
        data = data.as_dict()
    if not output_file or output_file == '-':
        yaml.dump(data, stream=sys.stdout, indent=4, default_flow_style=False)
    else:
        with open(output_file, 'wt', encoding='UTF-8') as f:
            yaml.dump(data, stream=f, indent=4, default_flow_style=False)


def print_as_yaml(cfg):
    save_to_yaml(cfg, '-')


def load_yaml(filename: str):
    with open(filename) as f:
        return yaml.load(f, yaml.Loader)
