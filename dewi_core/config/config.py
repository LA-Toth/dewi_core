# Copyright 2016-2022 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

import yaml


class InvalidEntry(KeyError):
    pass


class Config:
    def __init__(self):
        self._config = dict()

    def get_config(self):
        return dict(self._config)

    def overwrite_config(self, config: dict):
        self._config = config

    def _top_level_unsafe_set(self, key: str, value):
        self._config[key] = value

    def set(self, entry: str, value):
        cfg, key = self._get_container_and_key(entry)

        if key in cfg and isinstance(cfg[key], (dict, list, set)):
            raise InvalidEntry("The '{}' entry should not refer either a dict, list or set".format(entry))

        cfg[key] = value

    def _get_container_and_key(self, entry):
        parents = entry.split('.')
        key = parents.pop()
        cfg = self._config

        for parent in parents:
            if parent not in cfg:
                cfg[parent] = dict()

            cfg = cfg[parent]

        return cfg, key

    def append(self, list_entry: str, value):
        cfg, key = self._get_container_and_key(list_entry)

        if key not in cfg:
            cfg[key] = list()

        cfg[key].append(value)

    def add_to_set(self, list_entry: str, value):
        cfg, key = self._get_container_and_key(list_entry)

        if key not in cfg:
            cfg[key] = set()

        cfg[key].add(value)

    def get(self, entry: str):
        keys = entry.split('.')
        cfg = self._config

        try:
            for key in keys:
                cfg = cfg[key]
        except KeyError:
            return None

        return cfg

    def delete(self, list_entry: str):
        cfg, key = self._get_container_and_key(list_entry)
        del cfg[key]

    def dump(self, file, ignore: list[str] | None = None):
        cfg = self._config
        if ignore:
            cfg = dict(cfg)
            for item in ignore:
                del cfg[item]

        yaml.dump(cfg, file, indent=4, default_flow_style=False)

    def print(self, file=None):
        self._print(self._config, '', file=file)

    def _print(self, config: dict, prefix: str, file=None):
        for key in sorted(config.keys()):
            value = config[key]

            if isinstance(value, dict):
                self._print(value, "{}{}.".format(prefix, key), file=file)
            else:
                print("{}{}: {}".format(prefix, key, value), file=file)
