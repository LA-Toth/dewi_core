#  Copyright 2026, Laszlo Attila Toth
#  Distributed under the terms of the Apache License, Version 2.0

"""
Tests for the YAML glue: save_to_yaml(), print_as_yaml() and load_yaml().

This module is the one place a DataClass tree meets a serializer, and the
reason `dewi_dataclass.serialization.convert()` exists: a Node that reaches
the dumper unconverted is emitted as a `!!python/object:` tag -- output no
other consumer can read, and which yaml.safe_load() rejects.
"""

import enum
import io
import os
import sys
import tempfile

import yaml

import dewi_core.testcase
from dewi_core.utils.yaml import load_yaml, print_as_yaml, save_to_yaml
from dewi_dataclass import DataClass, DataList


class Leaf(DataClass):
    value: int

    def __init__(self):
        self.value = 1


class Tree(DataClass):
    name: str
    leaf: Leaf
    entries: DataList[Leaf]

    def __init__(self):
        self.name = 'root'
        self.leaf = Leaf()
        self.entries = DataList(Leaf)
        self.entries.append(Leaf())


class Mode(enum.IntFlag):
    NO_MODE = 0
    WITH_LOGS = 1


class SaveToYamlTest(dewi_core.testcase.TestCase):
    def set_up(self):
        self._tmpdir = tempfile.TemporaryDirectory()

    def tear_down(self):
        self._tmpdir.cleanup()

    def _path(self, name: str = 'out.yml') -> str:
        return os.path.join(self._tmpdir.name, name)

    def _captured(self, data, output_file=None) -> str:
        buf = io.StringIO()
        original = sys.stdout
        sys.stdout = buf
        try:
            save_to_yaml(data, output_file)
        finally:
            sys.stdout = original
        return buf.getvalue()

    def test_that_a_plain_dict_is_written_to_a_file(self):
        path = self._path()
        save_to_yaml(dict(a=1, b='two'), path)

        with open(path) as f:
            self.assert_equal({'a': 1, 'b': 'two'}, yaml.safe_load(f))

    def test_that_no_output_file_means_stdout(self):
        self.assert_equal({'a': 1}, yaml.safe_load(self._captured(dict(a=1))))

    def test_that_a_dash_means_stdout(self):
        self.assert_equal({'a': 1}, yaml.safe_load(self._captured(dict(a=1), '-')))

    def test_that_a_data_class_is_written_as_a_mapping(self):
        output = self._captured(Tree())

        self.assert_not_in('!!python/', output)
        self.assert_equal(
            {'name': 'root', 'leaf': {'value': 1}, 'entries': [{'value': 1}]},
            yaml.safe_load(output))

    def test_that_a_bare_list_of_data_classes_is_converted(self):
        """It could not be, before: a list is not a DataClass, so nothing
        converted it and the nodes reached the dumper untouched."""
        output = self._captured([Leaf(), Leaf()])

        self.assert_not_in('!!python/', output)
        self.assert_equal([{'value': 1}, {'value': 1}], yaml.safe_load(output))

    def test_that_a_data_class_inside_a_plain_container_is_converted(self):
        node = DataClass()
        node['in_list'] = [Leaf()]
        node['in_dict'] = {'key': Leaf()}
        node['in_tuple'] = (Leaf(),)

        output = self._captured(node)

        self.assert_not_in('!!python/', output)
        self.assert_equal({'in_list': [{'value': 1}],
                           'in_dict': {'key': {'value': 1}},
                           'in_tuple': [{'value': 1}]},
                          yaml.safe_load(output))

    def test_that_the_output_is_safe_loadable(self):
        self.assert_is_instance(yaml.safe_load(self._captured(Tree())), dict)

    def test_that_print_as_yaml_writes_to_stdout(self):
        buf = io.StringIO()
        original = sys.stdout
        sys.stdout = buf
        try:
            print_as_yaml(Tree())
        finally:
            sys.stdout = original

        self.assert_equal(yaml.safe_load(buf.getvalue()), Tree().as_dict())


class LoadYamlTest(dewi_core.testcase.TestCase):
    def set_up(self):
        self._tmpdir = tempfile.TemporaryDirectory()

    def tear_down(self):
        self._tmpdir.cleanup()

    def _path(self, name: str = 'in.yml') -> str:
        return os.path.join(self._tmpdir.name, name)

    def test_that_a_plain_document_loads(self):
        path = self._path()
        with open(path, 'wt') as f:
            f.write('a: 1\nb:\n  - x\n  - y\n')

        self.assert_equal({'a': 1, 'b': ['x', 'y']}, load_yaml(path))

    def test_that_a_saved_tree_round_trips(self):
        path = self._path()
        original = Tree()
        original.name = 'saved'
        save_to_yaml(original, path)

        restored = Tree()
        restored.load_from(load_yaml(path))

        self.assert_equal(original.as_dict(), restored.as_dict())
        self.assert_is(Leaf, type(restored.entries[0]))

    def test_that_the_full_loader_reconstructs_a_python_value(self):
        """sysinfo relies on this: an Enum member survives the round trip
        because load_yaml() uses the full loader rather than safe_load()."""
        path = self._path()
        save_to_yaml(dict(mode=Mode.WITH_LOGS), path)

        self.assert_is(Mode.WITH_LOGS, load_yaml(path)['mode'])

    def test_that_safe_load_would_refuse_that_same_file(self):
        path = self._path()
        save_to_yaml(dict(mode=Mode.WITH_LOGS), path)

        with open(path) as f:
            with self.assert_raises(yaml.YAMLError):
                yaml.safe_load(f)


if __name__ == '__main__':
    import unittest

    unittest.main()
