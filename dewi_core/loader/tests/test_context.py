# Copyright 2015-2021 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0
import dewi_core.testcase
from dewi_core.commandregistry import CommandRegistry
from dewi_core.config_env import ConfigDirRegistry, EnvConfig
from dewi_core.loader.context import Context, ContextEntryNotFound, ContextEntryAlreadyRegistered


class ContextTest(dewi_core.testcase.TestCase):
    def set_up(self):
        self.registry = CommandRegistry()
        self.config_dir_registry = ConfigDirRegistry(EnvConfig('ttt'))
        self.context = Context(self.registry, self.config_dir_registry)

    def test_that_context_is_almost_empty_initially(self):
        self.assert_equal(3, len(self.context))

    def test_register_an_element_and_can_be_queried(self):
        class Something:
            pass

        a_thing = Something()
        self.context.register('a_name', a_thing)
        self.assert_equal(4, len(self.context))
        self.assert_in('a_name', self.context)
        self.assert_equal(a_thing, self.context['a_name'])

    def test_that_exception_raised_if_entry_is_not_found(self):
        self.assert_raises(ContextEntryNotFound, self.context.__getitem__, 'something')

    def test_that_a_name_cannot_be_registered_twice(self):
        class Something:
            pass

        a_thing = Something()
        self.context.register('a_name', a_thing)
        self.assert_raises(ContextEntryAlreadyRegistered, self.context.register, 'a_name', 42)

    def test_that_an_already_registered_entry_can_be_unregistered(self):
        self.context.register('a_name', 42)
        self.assert_in('a_name', self.context)
        self.context.unregister('a_name')
        self.assert_equal(3, len(self.context))
        self.assert_not_in('a_name', self.context)

    def test_that_unregistering_unknown_entry_raises_exception(self):
        self.assert_raises(ContextEntryNotFound, self.context.unregister, 'a_name')

    def test_iteration(self):
        self.context.register('a', 42)
        self.context.register('b', 43)

        value = set()
        for i in self.context:
            value.add(i)

        self.assert_equal({'a', 'b', 'commands', 'command_registry', 'config_dir_registry'}, value)
