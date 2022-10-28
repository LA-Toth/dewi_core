# Copyright 2021-2022 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

import os.path

import dewi_core.testcase
from dewi_core.config_env import ConfigDirRegistry, EnvConfig, load_config_of_env
from dewi_core.tests.common import DATA_DIR, test_env


class ConfigDirAndEnvTest(dewi_core.testcase.TestCase):
    def set_up(self):
        test_env.reset_entries()
        self.env_config = EnvConfig('foobar')
        self.config_dir_registry = ConfigDirRegistry(self.env_config)

    def _register_dir(self, directory: str):
        path = os.path.join(DATA_DIR, 'cfgdirs', directory)
        result = self.config_dir_registry.register_config_directory(path)
        if result:
            self.assert_equal(path, self.config_dir_registry.config_directories[-1],
                              'Lastly added config directory is not stored as last in the list')

    def _register_dirs(self):
        self._register_dir('dir1')
        self._register_dir('dir2')
        self._register_dir('dir3')
        self.assert_equal(3, len(self.config_dir_registry.config_directories))

    def _asssert_env_after_load(self, expected_list: list[str]):
        self.config_dir_registry.load_env()
        self._asssert_env(expected_list)

    def _asssert_env(self, expected_list: list[str]):
        self.assert_equal(expected_list, test_env.entries, 'Mismatching list of env strings in test_env')

    def test_initial_env_name_is_stored(self):
        self.assert_equal('foobar', self.env_config.current_env)

    def test_initially_available_env_names(self):
        self.assert_equal({'development', 'production'}, self.env_config.available_envs)

    def test_change_current_env(self):
        self.env_config.set_current_env('something')
        self.assert_equal('something', self.env_config.current_env)
        self.config_dir_registry.set_current_env('something-else')
        self.assert_equal('something-else', self.env_config.current_env)

    def test_single_common_env(self):
        self._register_dir('dir1')
        self.assert_equal({'development', 'production'}, self.env_config.available_envs)
        self._asssert_env_after_load(['dir1-common'])
        self.assert_equal('foobar', self.env_config.current_env)

    def test_single_env_with_common_and_specific_modules(self):
        self._register_dir('dir2')
        self.assert_equal({'development', 'foobar', 'production', 'test'}, self.env_config.available_envs)
        self._asssert_env_after_load(['dir2-common', 'dir2-foobar'])

    def test_single_env_specific_module(self):
        self._register_dir('dir3')
        self.assert_equal({'development', 'foobar', 'production'}, self.env_config.available_envs)
        self._asssert_env_after_load(['dir3-foobar'])

    def test_all_env_with_name_foobar(self):
        self._register_dirs()
        self.assert_equal({'development', 'foobar', 'production', 'test'}, self.env_config.available_envs)
        self._asssert_env_after_load(['dir1-common', 'dir2-common', 'dir2-foobar', 'dir3-foobar'])

    def test_all_env_with_name_foobar_and_dir1_again(self):
        self._register_dirs()
        self._register_dir('dir1')
        self._asssert_env_after_load(['dir1-common', 'dir2-common', 'dir2-foobar', 'dir3-foobar'])

    def test_all_env_with_name_test(self):
        self._register_dirs()
        self.assert_equal({'development', 'foobar', 'production', 'test'}, self.env_config.available_envs)
        self.env_config.set_current_env('test')
        self._asssert_env_after_load(['dir1-common', 'dir2-common', 'dir2-test'])

    def _assert_wrapper_method(self, directory: str, env_name: str, expected_list: list[str]):
        test_env.reset_entries()
        path = os.path.join(DATA_DIR, 'cfgdirs', directory)
        load_config_of_env(path, env_name)
        self._asssert_env(expected_list)

    def test_wrapper_method(self):
        self._assert_wrapper_method('dir1', 'whatever', ['dir1-common'])
        self._assert_wrapper_method('dir2', 'whatever', ['dir2-common'])
        self._assert_wrapper_method('dir2', 'test', ['dir2-common', 'dir2-test'])
        self._assert_wrapper_method('dir3', 'test', [])
        self._assert_wrapper_method('dir3', 'foobar', ['dir3-foobar'])
