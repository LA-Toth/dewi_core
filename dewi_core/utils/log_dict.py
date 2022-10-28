# Copyright 2021-2022 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0
import collections.abc

from dewi_core.logger import log_debug


def log_debug_dict(c: collections.abc.Mapping, level=0):
    for k, v in c.items():
        if isinstance(v, collections.abc.Mapping):
            log_debug(f'{" " * level}{k}:')
            log_debug_dict(v, level + 2)
        else:
            log_debug(f'{" " * level}{k}: {v}')
