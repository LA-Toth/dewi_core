# Copyright 2015-2021 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

import collections.abc

import dewi_core.testcase
from dewi_core.commandregistry import CommandRegistry
from dewi_core.config_env import ConfigDirRegistry, EnvConfig
from dewi_core.loader.context import Context
from dewi_core.loader.loader import PluginLoader, PluginLoaderError
from dewi_core.loader.plugin import Plugin


class TestPlugin1(Plugin):
    """Sample description"""

    def get_dependencies(self) -> collections.abc.Iterable:
        return ()

    def load(self, c: Context):
        c.register('plugin1', 42)


class TestPlugin2a(Plugin):
    """Sample description"""

    def get_dependencies(self) -> collections.abc.Iterable:
        return ('dewi_core.loader.tests.test_loader.TestPlugin1',)

    def load(self, c: Context):
        c.register('plugin2a', 12)


class TestPlugin2b(Plugin):
    def get_dependencies(self) -> collections.abc.Iterable:
        return ('dewi_core.loader.tests.test_loader.TestPlugin1',)

    def load(self, c: Context):
        c.register('plugin2b', 22)


class TestPlugin3(Plugin):
    def get_dependencies(self) -> collections.abc.Iterable:
        return (
            'dewi_core.loader.tests.test_loader.TestPlugin2a',
            'dewi_core.loader.tests.test_loader.TestPlugin2b',
        )

    def load(self, c: Context):
        c.register('plugin3', 342)
        c.register('result', c['plugin2a'] + c['plugin2b'] + c['plugin1'])


class TestPluginWithInvalidDependencies1(Plugin):
    def get_dependencies(self) -> collections.abc.Iterable:
        return (
            'dewi_core.loader2.tests2.test_loader2.TestPlugin1',
            'dewi_core.loader.tests.test_loader.TestPluginThatWillNeverExist',
        )

    def load(self, c: Context):
        c.register('pluginX', 2242)


class TestPluginO1(Plugin):
    """plugin with circular dependencies"""

    def get_dependencies(self):
        return ('dewi_core.loader.tests.test_loader.TestPluginO2',)

    def load(self, c: Context):
        c.register('pluginO1', 2242)


class TestPluginO2(Plugin):
    """plugin with circular dependencies"""

    def get_dependencies(self):
        return ('dewi_core.loader.tests.test_loader.TestPluginO1',)

    def load(self, c: Context):
        c.register('pluginO2', 2242)


class TestLoader(dewi_core.testcase.TestCase):
    def set_up(self):
        self.registry = CommandRegistry()
        self.config_dir_registry = ConfigDirRegistry(EnvConfig('foo'))
        self.loader = PluginLoader(self.registry, self.config_dir_registry)

    def test_that_context_command_registry_is_the_same_as_the_loader_s(self):
        context = self.loader.load({'dewi_core.loader.tests.test_loader.TestPlugin1'})
        self.assert_equal(context.command_registry, self.registry)

    def test_load_plugin_without_dependencies(self):
        context = self.loader.load({'dewi_core.loader.tests.test_loader.TestPlugin1'})
        self.assert_equal(42, context['plugin1'])

    def test_that_a_plugin_can_be_loaded_twice_and_the_second_is_ignored(self):
        context = self.loader.load(
            ['dewi_core.loader.tests.test_loader.TestPlugin1', 'dewi_core.loader.tests.test_loader.TestPlugin1'])
        self.assert_equal(42, context['plugin1'])

    def test_load_plugin_with_invalid_class_name(self):
        self.assert_raises(
            PluginLoaderError,
            self.loader.load, {'dewi_core.loader.tests.test_loader.TestPluginThatWillNeverExist'})

    def test_load_plugin_with_invalid_module_name(self):
        self.assert_raises(
            PluginLoaderError,
            self.loader.load, {'dewi_core.loader.tests42.test_loader.TestPluginThatWillNeverExist'})

    def test_load_plugin_without_module_name(self):
        self.assert_raises(
            PluginLoaderError,
            self.loader.load, {'J316'})

    def test_load_plugin_with_single_dependency(self):
        context = self.loader.load({'dewi_core.loader.tests.test_loader.TestPlugin2a'})
        self.assert_equal(12, context['plugin2a'])
        self.assert_equal(42, context['plugin1'])

    def test_that_multiple_plugins_can_be_loaded_at_once(self):
        context = self.loader.load(
            {'dewi_core.loader.tests.test_loader.TestPlugin2a', 'dewi_core.loader.tests.test_loader.TestPlugin2b'})
        self.assert_equal(12, context['plugin2a'])
        self.assert_equal(22, context['plugin2b'])

    def test_load_plugin_with_multiple_dependencies(self):
        context = self.loader.load({'dewi_core.loader.tests.test_loader.TestPlugin3'})
        self.assert_equal(342, context['plugin3'])
        self.assert_equal(76, context['result'])

    def test_load_plugin_with_invalid_dependency_list(self):
        self.assert_raises(
            PluginLoaderError,
            self.loader.load, {'dewi_core.loader.tests.test_loader.TestPluginWithInvalidDependencies1'})

    def test_circular_dependency(self):
        self.assert_raises(
            PluginLoaderError,
            self.loader.load, {'dewi_core.loader.tests.test_loader.TestPluginO1'})

    def test_loaded_plugin_property(self):
        self.assert_equal(set(), self.loader.loaded_plugins)
        self.loader.load({'dewi_core.loader.tests.test_loader.TestPlugin3'})
        self.assert_equal(
            {
                'dewi_core.loader.tests.test_loader.TestPlugin3',
                'dewi_core.loader.tests.test_loader.TestPlugin1',
                'dewi_core.loader.tests.test_loader.TestPlugin2a',
                'dewi_core.loader.tests.test_loader.TestPlugin2b',
            },
            self.loader.loaded_plugins
        )
