# Copyright 2019-2022 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

import os.path

import dewi_core.testcase
from dewi_core.utils.files import find_file_recursively


class RecursiveFileSearchTest(dewi_core.testcase.TestCase):
    def assert_recursive_file_equal(self, expected_subdir: list[str], asset_subdir: list[str]):
        def abspath_from_partial(subdir: list[str]):
            return os.path.join(os.path.abspath(os.path.dirname(__file__)), 'assets', 'files', *subdir)

        expected_filename = os.path.join(abspath_from_partial(expected_subdir), 'search.txt')
        actual_filename = find_file_recursively('search.txt', abspath_from_partial(asset_subdir))

        self.assert_equal(expected_filename, actual_filename, 'File name differs from expected: ' + expected_filename)

    def test_one_level(self):
        self.assert_recursive_file_equal(['one_level'], ['one_level'])

    def test_one_level_in_sub_directory(self):
        self.assert_recursive_file_equal(['one_level', 'sub_directory'], ['one_level', 'sub_directory'])

    def test_multi_level(self):
        self.assert_recursive_file_equal(['multi_level'], ['multi_level', 'sub_directory', 'innermost'])

    def test_from_current_directory(self):
        try:
            find_file_recursively('something')
            self.assert_true(True)
        except:
            self.assert_false(True, "find_file_recursively must not raise any exception")
