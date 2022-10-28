# Copyright 2018-2022 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

import os
import sys

import yaml

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

if os.environ.get('DEWI_YAML_WITH_ALIASES', '0') == '0':
    yaml.Dumper.ignore_aliases = lambda *args: True


def save_to_yaml(cfg, output_file: str | None = None):
    if not output_file or output_file == '-':
        yaml.dump(cfg, stream=sys.stdout, indent=4, default_flow_style=False)
    else:
        with open(output_file, 'wt', encoding='UTF-8') as f:
            yaml.dump(cfg, stream=f, indent=4, default_flow_style=False)


def print_as_yaml(cfg):
    save_to_yaml(cfg, '-')


def load_yaml(filename: str):
    with open(filename) as f:
        return yaml.load(f, yaml.Loader)
