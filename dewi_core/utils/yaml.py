# Copyright 2018-2021 Laszlo Attila Toth
# Distributed under the terms of the GNU Lesser General Public License v3

import os
import sys

import yaml

if os.environ.get('DEWI_YAML_WITH_ALIASES', '0') == '0':
    yaml.Dumper.ignore_aliases = lambda *args: True


def save_to_yaml(cfg, output_file):
    if output_file == '-':
        yaml.dump(cfg, stream=sys.stdout, indent=4, default_flow_style=False)
    else:
        with open(output_file, 'wt', encoding='UTF-8') as f:
            yaml.dump(cfg, stream=f, indent=4, default_flow_style=False)
