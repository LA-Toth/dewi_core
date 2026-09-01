#  Copyright 2026, Laszlo Attila Toth
#  Distributed under the terms of the Apache License, Version 2.0

"""Tests for the small pure helpers in dewi_core.utils."""

import collections
import datetime
import os
import re
import tempfile

import dewi_core.testcase
from dewi_core.utils.dictionaries import (DictionaryWithList, DictionaryWithSet,
                                          _TypedDictionary, sort_dict)
from dewi_core.utils.files import find_file_recursively
from dewi_core.utils.log_dict import log_debug_dict
from dewi_core.utils.time import humanize_time, localtime


class HumanizeTimeTest(dewi_core.testcase.TestCase):
    def test_that_seconds_only_are_split_out(self):
        self.assert_equal((0, 0, 0, 42), humanize_time(42))

    def test_that_minutes_and_seconds_are_split_out(self):
        self.assert_equal((0, 0, 2, 5), humanize_time(125))

    def test_that_hours_are_split_out(self):
        self.assert_equal((0, 1, 1, 1), humanize_time(3661))

    def test_that_more_than_a_day_yields_days(self):
        # note the boundary: days appear only once hours exceeds 24, so
        # exactly 24 hours is reported as 24 hours rather than one day
        self.assert_equal((0, 24, 0, 0), humanize_time(24 * 3600))
        self.assert_equal((1, 1, 0, 0), humanize_time(25 * 3600))

    def test_that_fractional_seconds_are_trimmed_to_two_places(self):
        self.assert_equal((0, 0, 0, 1.23), humanize_time(1.23456))

    def test_that_trimming_can_be_disabled(self):
        self.assert_almost_equal(1.23456, humanize_time(1.23456, trim_secs=False)[3])

    def test_that_format_renders_a_string(self):
        self.assert_equal('01:01:01.00', humanize_time(3661, format=True))

    def test_that_format_includes_days_when_there_are_any(self):
        self.assert_equal('1 days01:00:00.00', humanize_time(25 * 3600, format=True))

    def test_that_format_pads_and_keeps_two_decimals(self):
        self.assert_equal('00:00:01.23', humanize_time(1.23456, format=True))


class LocaltimeTest(dewi_core.testcase.TestCase):
    def test_that_it_matches_the_documented_shape(self):
        self.assert_regex(localtime(), r'^\d{8}-\d{6}-\d+$')

    def test_that_the_date_part_is_today(self):
        self.assert_true(localtime().startswith(
            datetime.datetime.now().strftime('%Y%m%d')))


class DictionariesTest(dewi_core.testcase.TestCase):
    def test_that_a_list_dictionary_appends(self):
        tested = DictionaryWithList()
        tested['a'] = 1
        tested['a'] = 2
        tested['b'] = 3

        self.assert_equal({'a': [1, 2], 'b': [3]}, tested)

    def test_that_a_list_dictionary_keeps_duplicates(self):
        tested = DictionaryWithList()
        tested['a'] = 1
        tested['a'] = 1

        self.assert_equal({'a': [1, 1]}, tested)

    def test_that_a_set_dictionary_adds(self):
        tested = DictionaryWithSet()
        tested['a'] = 1
        tested['a'] = 2

        self.assert_equal({'a': {1, 2}}, tested)

    def test_that_a_set_dictionary_drops_duplicates(self):
        tested = DictionaryWithSet()
        tested['a'] = 1
        tested['a'] = 1

        self.assert_equal({'a': {1}}, tested)

    def test_that_the_base_class_refuses_to_add(self):
        tested = _TypedDictionary(list)

        with self.assert_raises(NotImplementedError):
            tested['a'] = 1

    def test_that_sort_dict_orders_by_key(self):
        result = sort_dict({'b': 2, 'a': 1, 'c': 3})

        self.assert_equal(['a', 'b', 'c'], list(result))
        self.assert_is_instance(result, collections.OrderedDict)

    def test_that_sort_dict_keeps_the_values(self):
        self.assert_equal({'a': 1, 'b': 2}, dict(sort_dict({'b': 2, 'a': 1})))

    def test_that_sort_dict_handles_an_empty_mapping(self):
        self.assert_equal({}, dict(sort_dict({})))


class LogDebugDictTest(dewi_core.testcase.TestCase):
    def _logged(self, mapping) -> list[str]:
        recorded = []
        import dewi_core.utils.log_dict as module
        original = module.log_debug
        module.log_debug = lambda msg: recorded.append(msg)
        try:
            log_debug_dict(mapping)
        finally:
            module.log_debug = original
        return recorded

    def test_that_a_flat_mapping_is_logged_as_key_value(self):
        self.assert_equal(['a: 1', 'b: 2'], self._logged({'a': 1, 'b': 2}))

    def test_that_a_nested_mapping_is_indented(self):
        self.assert_equal(['outer:', '  inner: 1'],
                          self._logged({'outer': {'inner': 1}}))

    def test_that_nesting_indents_two_spaces_per_level(self):
        self.assert_equal(['a:', '  b:', '    c: 1'],
                          self._logged({'a': {'b': {'c': 1}}}))

    def test_that_an_empty_mapping_logs_nothing(self):
        self.assert_equal([], self._logged({}))


class FindFileRecursivelyTest(dewi_core.testcase.TestCase):
    def set_up(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self._tmpdir.name)
        self.deep = os.path.join(self.root, 'a', 'b', 'c')
        os.makedirs(self.deep)
        self.marker = os.path.join(self.root, 'marker.txt')
        with open(self.marker, 'wt') as f:
            f.write('x')

    def tear_down(self):
        self._tmpdir.cleanup()

    def test_that_a_file_in_the_directory_itself_is_found(self):
        self.assert_equal(self.marker, find_file_recursively('marker.txt', self.root))

    def test_that_a_file_in_a_parent_directory_is_found(self):
        """The .gitignore rule: walk upwards until it turns up."""
        self.assert_equal(self.marker, find_file_recursively('marker.txt', self.deep))

    def test_that_the_nearest_one_wins(self):
        nearer = os.path.join(self.deep, 'marker.txt')
        with open(nearer, 'wt') as f:
            f.write('y')

        self.assert_equal(nearer, find_file_recursively('marker.txt', self.deep))

    def test_that_a_missing_file_gives_none(self):
        self.assert_is_none(find_file_recursively('no-such-file-here.txt', self.deep))

    def test_that_the_current_directory_is_used_without_a_directory(self):
        from dewi_core.context_managers import in_directory

        with in_directory(self.root):
            self.assert_equal(self.marker, find_file_recursively('marker.txt'))

    def test_that_a_directory_counts_as_found(self):
        """git finds .git/ this way, so a directory has to match too."""
        self.assert_equal(os.path.join(self.root, 'a'),
                          find_file_recursively('a', self.deep))


if __name__ == '__main__':
    import unittest

    unittest.main()
