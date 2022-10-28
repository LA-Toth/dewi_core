# Copyright 2021-2022 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

import importlib.util
import os
import typing

from dewi_core.logger import log_debug


class EnvConfig:
    def __init__(self, current_env: str):
        self._current_env = current_env
        self.available_envs = {'development', 'production'}
        self._config_dir_to_envs_map: dict[str, typing.Set[str]] = {}

    @property
    def current_env(self):
        return self._current_env

    def set_current_env(self, current_env: str):
        self._current_env = current_env

    def add_from_directory(self, directory: str):
        self._config_dir_to_envs_map[directory] = set()
        envs = set()
        for dir_entry in os.listdir(directory):
            entry = f'{directory}/{dir_entry}'
            if dir_entry == 'environments' and os.path.isdir(entry):
                for env_entry in os.listdir(entry):
                    if env_entry.endswith('.py') and env_entry != '__init__.py':
                        envs.add(env_entry[:-3])

        self.available_envs |= envs
        self._config_dir_to_envs_map[directory] |= envs

    def load_current_env_from_directory(self, directory: str):
        path = os.path.abspath(os.path.join(directory, 'environment.py'))
        if os.path.exists(path):
            self._load(path)

        if self._current_env in self._config_dir_to_envs_map[directory]:
            path = os.path.abspath(os.path.join(directory, 'environments', f'{self._current_env}.py'))
            self._load(path)

    def _load(self, path: str):
        module = os.path.basename(path)[:-3].replace('/', '.').replace('\\', '.')
        log_debug('Loading environment file', dict(filename=path, module_name=module, current_env=self._current_env))
        spec = importlib.util.spec_from_file_location(module, path)
        mfspec = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mfspec)


class ConfigDirRegistry:
    def __init__(self, env_config: EnvConfig):
        self.env_config = env_config
        self.config_directories: list[str] = []

    def register_config_directory(self, directory: str):
        if directory in self.config_directories:
            log_debug('Not registering duplicated config directory', dict(name=directory))
            return False
        log_debug('Registering config directory', dict(name=directory))
        self.config_directories.append(directory)
        self.env_config.add_from_directory(directory)
        return True

    def register_config_directories(self, directories: list[str]):
        for d in directories:
            self.register_config_directory(d)

    def set_current_env(self, env_name: str):
        self.env_config.set_current_env(env_name)

    def load_env(self):
        for config_dir in self.config_directories:
            self.env_config.load_current_env_from_directory(config_dir)


def load_config_of_env(config_dir: str, env_name: str):
    """
    Load a single env file with a common one if exits from the specified directory.
    Useful for loading test env as Rails-like loading is not supported in Python.
    """
    r = ConfigDirRegistry(EnvConfig(env_name))
    r.register_config_directory(config_dir)
    r.load_env()
