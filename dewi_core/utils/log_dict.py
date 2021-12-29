import collections

from dewi_core.logger import log_debug


def log_debug_dict(c: dict, level=0):
    for k, v in c.items():
        if isinstance(v, collections.abc.Mapping):
            log_debug(f'{" " * level}{k}:')
            log_debug_dict(v, level + 2)
        else:
            log_debug(f'{" " * level}{k}: {v}')
