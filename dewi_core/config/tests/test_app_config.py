# Copyright 2020-2021 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

from unittest import mock

import dewi_core.testcase
from ..appconfig import AppConfig, DEFAULT_CONFIG_PATH, get_config, _set_config


class AppConfigTest(dewi_core.testcase.TestCase):
    BASEDIR = '/path/to/whatever/location'

    def set_up(self):
        _set_config(None)

    def test_members(self):
        config = AppConfig()
        self.assert_is_none(config.basedir)

        config.set('core', 'basedir', self.BASEDIR)

        self.assert_equal(self.BASEDIR, config.basedir)
        self.assert_equal(f'{self.BASEDIR}/etc', config.etcdir)
        self.assert_equal(f'{self.BASEDIR}/projects', config.projectdir)
        self.assert_equal(f'{self.BASEDIR}/src', config.srcdir)
        self.assert_equal(f'{self.BASEDIR}/src/bare/example-repo', config.repo_dir_of('example-repo'))
        self.assert_equal(f'{self.BASEDIR}/src/bare/something', config.repo_dir_of('something'))

    @mock.patch('dewi_core.config.iniconfig.IniConfig.open')
    def test_get_config(self, load_mock):
        self.assert_is_instance(get_config(), AppConfig)
        load_mock.assert_called_once_with(DEFAULT_CONFIG_PATH)

    @mock.patch('dewi_core.config.iniconfig.IniConfig.open')
    def test_get_config_with_some_path(self, load_mock):
        path = '/it/really/does/not/matter'
        self.assert_is_instance(get_config(path), AppConfig)
        load_mock.assert_called_once_with(path)

    @mock.patch('dewi_core.config.iniconfig.IniConfig.open')
    def test_get_config_sets_config_only_once_with_default_path(self, load_mock):
        path = '/it/really/does/not/matter'
        cfg1 = get_config()
        cfg2 = get_config(path)
        self.assert_equal(cfg1, cfg2)
        self.assert_equal(cfg1, get_config())
        self.assert_equal(cfg2, get_config(path))
        load_mock.assert_called_once_with(DEFAULT_CONFIG_PATH)

    @mock.patch('dewi_core.config.iniconfig.IniConfig.open')
    def test_get_config_sets_config_only_once_with_path(self, load_mock):
        path = '/it/really/does/not/matter'
        cfg1 = get_config(path)
        cfg2 = get_config()
        self.assert_equal(cfg1, cfg2)
        load_mock.assert_called_once_with(path)
