#  Copyright 2026, Laszlo Attila Toth
#  Distributed under the terms of the Apache License, Version 2.0

"""
Tests for Config, the dotted-path store.

This is the write path of every dewi_module_framework module: `set()` walks a
tree by key, creating missing levels, and the tree it walks is usually made of
DataClass nodes rather than plain dicts. Both are exercised here.
"""

import io

import dewi_core.testcase
from dewi_core.config.config import Config, InvalidEntry
from dewi_dataclass import DataClass


class Child(DataClass):
    value: int

    def __init__(self):
        self.value = 0


class Root(DataClass):
    child: Child

    def __init__(self):
        self.child = Child()


class ConfigTest(dewi_core.testcase.TestCase):
    def set_up(self):
        self.tested = Config()

    def test_that_a_new_config_is_empty(self):
        self.assert_equal({}, self.tested.get_config())

    def test_that_a_top_level_entry_round_trips(self):
        self.tested.set('key', 42)
        self.assert_equal(42, self.tested.get('key'))

    def test_that_a_dotted_path_creates_the_levels(self):
        self.tested.set('a.b.c', 1)

        self.assert_equal(1, self.tested.get('a.b.c'))
        self.assert_equal({'b': {'c': 1}}, self.tested.get('a'))

    def test_that_a_missing_entry_gives_none(self):
        self.assert_is_none(self.tested.get('nope'))
        self.assert_is_none(self.tested.get('no.such.path'))

    def test_that_get_config_returns_a_copy(self):
        self.tested.set('a', 1)
        snapshot = self.tested.get_config()
        snapshot['a'] = 2

        self.assert_equal(1, self.tested.get('a'))

    def test_that_overwrite_config_replaces_everything(self):
        self.tested.set('a', 1)
        self.tested.overwrite_config({'b': 2})

        self.assert_is_none(self.tested.get('a'))
        self.assert_equal(2, self.tested.get('b'))

    def test_that_setting_over_a_container_is_refused(self):
        self.tested.set('a.b', 1)

        with self.assert_raises(InvalidEntry):
            self.tested.set('a', 2)

    def test_that_setting_over_a_list_is_refused(self):
        self.tested.append('items', 1)

        with self.assert_raises(InvalidEntry):
            self.tested.set('items', 2)

    def test_that_append_creates_and_extends_a_list(self):
        self.tested.append('a.list', 1)
        self.tested.append('a.list', 2)

        self.assert_equal([1, 2], self.tested.get('a.list'))

    def test_that_add_to_set_creates_and_dedupes(self):
        self.tested.add_to_set('a.set', 1)
        self.tested.add_to_set('a.set', 1)
        self.tested.add_to_set('a.set', 2)

        self.assert_equal({1, 2}, self.tested.get('a.set'))

    def test_that_delete_removes_an_entry(self):
        self.tested.set('a.b', 1)
        self.tested.delete('a.b')

        self.assert_is_none(self.tested.get('a.b'))

    def test_that_deleting_a_missing_entry_raises(self):
        with self.assert_raises(KeyError):
            self.tested.delete('nope')

    def test_that_top_level_unsafe_set_bypasses_the_container_check(self):
        self.tested.set('a.b', 1)
        self.tested._top_level_unsafe_set('a', 2)

        self.assert_equal(2, self.tested.get('a'))


class ConfigOverDataClassTest(dewi_core.testcase.TestCase):
    """The sysinfo shape: Config holding DataClass trees, walked by key."""

    def set_up(self):
        self.tested = Config()
        self.tested.set('root', Root())

    def test_that_a_dotted_path_walks_into_a_data_class(self):
        self.tested.set('root.child.value', 7)

        self.assert_equal(7, self.tested.get('root.child.value'))
        self.assert_equal(7, self.tested.get('root').child.value)

    def test_that_the_node_objects_are_kept_not_replaced(self):
        original = self.tested.get('root').child
        self.tested.set('root.child.value', 7)

        self.assert_is(original, self.tested.get('root').child)

    def test_that_a_missing_level_under_a_node_becomes_a_plain_dict(self):
        self.tested.set('root.extra.key', 1)

        self.assert_is(dict, type(self.tested.get('root')['extra']))
        self.assert_equal(1, self.tested.get('root.extra.key'))

    def test_that_a_missing_path_gives_none_whichever_kind_of_container(self):
        """A dict raises KeyError for a missing key, a DataClass raises
        AttributeError, and a config tree mixes the two freely -- so get()
        has to catch both or the answer depends on which subtree you are in.
        """
        self.assert_is_none(self.tested.get('nosuch.plain.path'))
        self.assert_is_none(self.tested.get('root.child.nope'))
        self.assert_is_none(self.tested.get('root.nope.deeper'))

    def test_that_a_present_node_path_still_returns_its_value(self):
        self.tested.set('root.child.value', 3)

        self.assert_equal(3, self.tested.get('root.child.value'))

    def test_that_deletion_still_differs_because_a_node_forbids_it(self):
        """Not an exception-type mismatch but a capability difference: a dict
        entry can be deleted, a Node member cannot."""
        self.tested.set('plain.key', 1)
        self.tested.delete('plain.key')
        self.assert_is_none(self.tested.get('plain.key'))

        with self.assert_raises(TypeError):
            self.tested.delete('root.child.value')


class ConfigOutputTest(dewi_core.testcase.TestCase):
    def set_up(self):
        self.tested = Config()
        self.tested.set('b.y', 2)
        self.tested.set('a', 1)

    def test_that_print_sorts_and_flattens(self):
        buf = io.StringIO()
        self.tested.print(file=buf)

        self.assert_equal(['a: 1', 'b.y: 2'], buf.getvalue().splitlines())

    def test_that_dump_writes_yaml(self):
        import yaml

        buf = io.StringIO()
        self.tested.dump(buf)

        self.assert_equal({'a': 1, 'b': {'y': 2}}, yaml.safe_load(buf.getvalue()))

    def test_that_dump_can_ignore_entries(self):
        import yaml

        buf = io.StringIO()
        self.tested.dump(buf, ignore=['b'])

        self.assert_equal({'a': 1}, yaml.safe_load(buf.getvalue()))

    def test_that_ignoring_does_not_change_the_config(self):
        self.tested.dump(io.StringIO(), ignore=['b'])

        self.assert_equal(2, self.tested.get('b.y'))


if __name__ == '__main__':
    import unittest

    unittest.main()
