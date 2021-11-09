# Copyright 2019-2021 Laszlo Attila Toth
# Distributed under the terms of the GNU Lesser General Public License v3

import os
import tempfile

import dewi_core.testcase
from dewi_core.config.iniconfig import DictConfigParser, IniConfig, IniConfigError

ASSETS_DIR = os.path.join(os.path.dirname(__file__), 'assets')


class DictParserTest(dewi_core.testcase.TestCase):
    def test_as_dict(self):
        parser = DictConfigParser()
        parser.add_section('an')
        parser.add_section('another "example"')
        parser.set('an', 'example', '42')
        parser.set('an', 'example2', 'a text value')
        parser.set('another "example"', 'value', '43')
        self.assert_equal({
            'an': dict(example='42', example2='a text value'),
            'another "example"': dict(value='43')},
            parser.as_dict())


class IniConfigTest(dewi_core.testcase.TestCase):

    def set_up(self):
        self.cfg_file = '/tmp/test-cfg-mod.config'
        self.settings = [
            ['remote.origin', 'branch', 'master'],
            ['remote.origin', 'b', 'other'],
            ['stew', 'aliasx', 'apple'],
        ]

    def test_cfg_init(self):
        cfg = IniConfig()
        self.assert_is_none(cfg.config_file)
        self.assert_is_not_none(cfg.parser)

    def _verify_config(self, config):
        settings_sections_options = {}
        # Verify values
        for (section, option, value) in self.settings:
            cfg_value = config.get(section, option)
            self.assert_equal(cfg_value, value)

        # Fill settings_sections_options
        for (section, option, value) in self.settings:
            if section not in settings_sections_options:
                settings_sections_options[section] = []
            if option not in settings_sections_options[section]:
                settings_sections_options[section].append(option)

        # Verify that no extra value is stored
        self.assert_equal(sorted(settings_sections_options.keys()), sorted(config.get_sections()))
        for section, options in settings_sections_options.items():
            self.assert_equal(sorted(options), sorted(config.get_options(section)))

    def test_set_get_save_load(self):
        # Test assumes it
        self.assert_false(os.path.exists(self.cfg_file))
        cfg = IniConfig()
        cfg.open(self.cfg_file)
        for (section, option, value) in self.settings:
            cfg.set(section, option, value)

        self._verify_config(cfg)

        # Before the first write it can't exist
        self.assert_false(os.path.exists(self.cfg_file))
        cfg.write()
        self.assert_true(os.path.exists(self.cfg_file))

        with open(self.cfg_file, 'r') as f:
            content = f.read()
        # In fact, it is 67, but it cannot be guaranteed
        self.assert_true(len(content) > 1)

        # let's open it
        new_config = IniConfig()
        new_config.open(self.cfg_file)
        self._verify_config(new_config)
        os.unlink(self.cfg_file)

    def test_overwrite_and_delete(self):
        # Saving because the order of test functions is not guaranteed
        saved_settings = list(self.settings)
        # Test assumes it
        self.assert_false(os.path.exists(self.cfg_file))
        cfg = IniConfig()
        cfg.open(self.cfg_file)
        for (section, option, value) in self.settings:
            cfg.set(section, option, value)

        self._verify_config(cfg)

        self.settings[0][2] += " Something not too useful"
        cfg.set(self.settings[0][0], self.settings[0][1], self.settings[0][2])
        self._verify_config(cfg)

        cfg.remove(self.settings[1][0], self.settings[1][1])
        del self.settings[1]
        self._verify_config(cfg)

        self.settings = saved_settings

    def test_other_functions(self):
        # Test assumes it
        self.assert_false(os.path.exists(self.cfg_file))
        cfg = IniConfig()
        cfg.open(self.cfg_file)

        # testing has
        self.assert_false(cfg.has('an', 'apple'))
        cfg.set('an', 'apple', 'is red')
        self.assert_equal(cfg.get('an', 'apple'), 'is red')
        self.assert_true(cfg.has('an', 'apple'))
        cfg.remove('an', 'apple')
        self.assert_false(cfg.has('an', 'apple'))

        # cfg must not be empty
        cfg.set('an', 'apple', 'is red')
        self.assert_equal(cfg.get('an', 'apple'), 'is red')

        # testing default return values
        self.assert_equal(cfg.get_sections(), ['an'])
        self.assert_equal(cfg.get_options('an'), ['apple'])
        self.assert_equal(cfg.get_options('death star'), [])
        self.assert_equal(cfg.get('siths', 'darth vader'), None)

        cfg.set('an apple', 'is red', '!%@#""' + "\nangry bird")
        self.assert_equal(cfg.get('an apple', 'is red'), '!%@#""' + "\nangry bird")
        self.assert_equal(cfg.get_or_default_value('an apple', 'is red', 'green'), '!%@#""' + "\nangry bird")
        self.assert_equal(cfg.get_or_default_value('an apple', 'is not red', 'green'), 'green')

    def test_write_without_open_and_filename_fails(self):
        cfg = IniConfig()
        self.assert_raises(IniConfigError, cfg.write)

    def test_config_can_be_written_and_read(self):
        (fd, filename) = tempfile.mkstemp()
        os.close(fd)
        cfg = IniConfig()
        cfg.set('an', 'example', '4222222')
        cfg.write(filename)
        cfg = IniConfig()
        self.assert_is_none(cfg.get('an', 'example'))
        cfg.open(filename)
        self.assert_equal('4222222', cfg.get('an', 'example'))
        os.unlink(filename)

    def test_open_sets_and_close_clears_config_and_filename(self):
        cfg = IniConfig()
        cfg.open(f'{ASSETS_DIR}/1.ini')
        self.assert_equal({'some': {'thing': 'some value'}}, cfg.as_dict())
        self.assert_equal(f'{ASSETS_DIR}/1.ini', cfg.config_file)
        self.assert_equal([f'{ASSETS_DIR}/1.ini'], cfg.loaded_files)
        cfg.close()
        self.assert_equal({}, cfg.as_dict())
        self.assert_is_none(cfg.config_file)
        self.assert_equal([], cfg.loaded_files)

    def test_config_cannot_be_opened_twice_without_close(self):
        cfg = IniConfig()
        cfg.open(f'{ASSETS_DIR}/1.ini')
        self.assert_raises(IniConfigError, cfg.open, f'{ASSETS_DIR}/2.ini')
        cfg.close()

        cfg.open(f'{ASSETS_DIR}/2.ini')
        self.assert_equal({'more': {'stuff': '4444'}}, cfg.as_dict())
        self.assert_equal(f'{ASSETS_DIR}/2.ini', cfg.config_file)
        self.assert_equal([f'{ASSETS_DIR}/2.ini'], cfg.loaded_files)

    def test_config_can_be_extended_by_multiple_ini_files(self):
        cfg = IniConfig()

        cfg.open(f'{ASSETS_DIR}/1.ini')
        self.assert_equal(f'{ASSETS_DIR}/1.ini', cfg.config_file)
        self.assert_equal([f'{ASSETS_DIR}/1.ini'], cfg.loaded_files)
        self.assert_equal({'some': {'thing': 'some value'}}, cfg.as_dict())

        cfg.open(f'{ASSETS_DIR}/2.ini', merge=True)
        self.assert_equal(f'{ASSETS_DIR}/1.ini', cfg.config_file)
        self.assert_equal([f'{ASSETS_DIR}/{x}.ini' for x in range(1, 3)], cfg.loaded_files)
        self.assert_equal({'more': {'stuff': '4444'}, 'some': {'thing': 'some value'}}, cfg.as_dict())

        cfg.open(f'{ASSETS_DIR}/3.ini', merge=True)
        self.assert_equal(f'{ASSETS_DIR}/1.ini', cfg.config_file)
        self.assert_equal([f'{ASSETS_DIR}/{x}.ini' for x in range(1, 4)], cfg.loaded_files)
        self.assert_equal(
            {'some': {'thing': 'some value', 'thingy': 'multi\nline stuff'}, 'more': {'stuff': 'more.stuff.!\\nx'}},
            cfg.as_dict())
