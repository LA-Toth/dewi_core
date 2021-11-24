# Copyright 2018-2020 Laszlo Attila Toth
# Distributed under the terms of the GNU Lesser General Public License v3

import typing

import yaml

import dewi_core.testcase
from dewi_core.config.node import Node, NodeList


class N1(Node):
    def __init__(self):
        self.x: int = 0
        self.y: int = None


class N2(Node):
    def __init__(self):
        self.list_of_n1s: typing.List[N1] = NodeList(N1)
        self.title: str = None
        self.count: int = 100


NODE_TEST_RESULT = """count: 100
list_of_n1s:
- x: 0
  y: null
- x: 0
  y: 42
title: null
"""

NODE_EMPTY_RESULT = """count: 100
list_of_n1s: []
title: null
"""


class NodeAndNodeListTest(dewi_core.testcase.TestCase):
    def set_up(self):
        self.tested = N2()
        self.tested.list_of_n1s.append(N1())

        node = N1()
        node.y = 42
        self.tested.list_of_n1s.append(node)

    def test_empty_object(self):
        self.assert_equal(NODE_EMPTY_RESULT, yaml.dump(N2()))
        self.tested = N2()
        self.assert_equal(NODE_EMPTY_RESULT, yaml.dump(self.tested))

    def test_yaml_dump(self):
        self.assert_equal(NODE_TEST_RESULT, yaml.dump(self.tested))

    def test_load_from_dict(self):
        self.tested = N2()
        self.assert_equal(NODE_EMPTY_RESULT, yaml.dump(self.tested))
        self.tested.load_from(dict(list_of_n1s=[dict(x=0, y=None), dict(x=0, y=42)], title=None))
        self.assert_equal(NODE_TEST_RESULT, yaml.dump(self.tested))

    def test_load_from_yaml(self):
        self.tested = N2()
        self.assert_equal(NODE_EMPTY_RESULT, yaml.dump(self.tested))
        self.tested.load_from(yaml.load(NODE_TEST_RESULT, Loader=yaml.SafeLoader))
        self.assert_equal(NODE_TEST_RESULT, yaml.dump(self.tested))

    def test_size_of_empty_object(self):
        self.assert_equal(3, len(N2()))

    def test_size_of_filled_object(self):
        self.assert_equal(3, len(self.tested))

    def test_size_of_node_list_equals_item_count(self):
        self.assert_equal(2, len(self.tested.list_of_n1s))

    def test_contains_known_members(self):
        self.assert_in('list_of_n1s', self.tested)

    def test_additional_members_can_be_added(self):
        self.assert_not_in('as_member', self.tested)
        self.tested.as_member = 123
        self.assert_in('as_member', self.tested)
        self.assert_not_in('as_key', self.tested)
        self.tested['as_key'] = 4
        self.assert_in('as_key', self.tested)

    def test_get_unknown_member_raises_attribute_error(self):
        self.assert_raises(AttributeError, lambda: self.tested.a_member)
        self.assert_raises(AttributeError, lambda: self.tested['another_member'])

    def test_that_key_can_be_invalid_identifier(self):
        self.assert_not_in('a-value', self.tested)
        self.assert_false(hasattr(self.tested, 'a-value'))
        self.tested['a-value'] = 44
        self.assert_equal(44, self.tested['a-value'])
        self.assert_equal(44, getattr(self.tested, 'a-value'))
