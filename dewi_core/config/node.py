# Copyright 2017-2021 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

import collections.abc
import typing

import yaml
from yaml.dumper import Dumper


class Node(collections.abc.MutableMapping):
    """
    This class is a base class to add typesafe objects to a Config.
    Example:

    >>> from dewi_core.config.config import Config
    >>> class A(Node):
    >>>     entry: str = 'default-value'
    >>> c = Config()
    >>> c.set('root', A())
    """

    SEALED_ATTR_NAME = '_sealed__'
    _sealed__ = False

    def _seal(self):
        self._sealed__ = True

    def _unseal(self):
        self._sealed__ = False

    def __len__(self):
        return len(self.__dict__)

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        return setattr(self, key, value)

    def __setattr__(self, key, value):
        if self._sealed__ and key not in self.__dict__:
            raise KeyError(key)
        super().__setattr__(key, value)

    def __iter__(self):
        return iter({x: y for x, y in self.__dict__.items() if x != self.SEALED_ATTR_NAME})

    def __delitem__(self, key):
        raise RuntimeError('Unable to delete key {}'.format(key))

    def __repr__(self):
        return str({x: y for x, y in self.__dict__.items() if x != self.SEALED_ATTR_NAME})

    def __contains__(self, item):
        return item != self.SEALED_ATTR_NAME and item in self.__dict__

    def load_from(self, data: dict):
        load_node(self, data, sealed=self._sealed__)

    @classmethod
    def create_from(cls, data: dict):
        n = cls()
        n.load_from(data)
        return n


class NodeList(list):
    def __init__(self, member_type: typing.Type[Node]):
        super().__init__()
        self.type_: typing.Type[Node] = member_type

    def load_from(self, data: list):
        self.clear()
        for item in data:
            if isinstance(item, Node):
                self.append(item)
            else:
                node = self.type_()
                node.load_from(item)
                self.append(node)


def load_node(node: Node, d: dict, *, sealed: bool = False):
    for key, value in d.items():
        if key in node and isinstance(node[key], (Node, NodeList)):
            node[key].load_from(value)
        elif key in node or not sealed:
            node[key] = value


def represent_node(dumper: Dumper, data: Node):
    return dumper.represent_dict(data)


def represent_node_list(dumper: Dumper, data: NodeList):
    return dumper.represent_list(data)


yaml.add_multi_representer(Node, represent_node)
yaml.add_multi_representer(NodeList, represent_node_list)
