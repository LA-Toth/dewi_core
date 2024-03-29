# Copyright 2015-2021 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

import dewi_core.testcase

from dewi_core.commands.edit.edit import convert_to_vim_args


class TestVimArgumentConverter(dewi_core.testcase.TestCase):
    def test_empty_list_is_not_changed(self):
        self.assert_equal([], convert_to_vim_args([]))

    def test_filename_is_not_changed(self):
        self.assert_equal(['path/to/file34.txt'], convert_to_vim_args(['path/to/file34.txt']))

    def test_file_colon_number_is_converted_to_line_number(self):
        self.assert_equal(['path/to/file34.txt', '+42'], convert_to_vim_args(['path/to/file34.txt:42']))
        self.assert_equal(['path/to/file34.txt', '+42'], convert_to_vim_args(['path/to/file34.txt:42:']))

    def test_file_names_with_line_and_column_number_are_converted(self):
        self.assert_equal(['path/to/file34.txt', '+42'], convert_to_vim_args(['path/to/file34.txt:42:12']))
        self.assert_equal(['path/to/file34.txt', '+42'], convert_to_vim_args(['path/to/file34.txt:42:12:']))

    def test_multiple_args_are_prefixed_by_p_option(self):
        self.assert_equal(
            ['-p', 'path/to/file34.txt:34', 'path/to/file35.txt'],
            convert_to_vim_args(['path/to/file34.txt:34', 'path/to/file35.txt']))
