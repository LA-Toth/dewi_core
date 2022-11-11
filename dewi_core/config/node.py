# Copyright 2017-2022 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

import collections.abc

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

    def load_from(self, data: dict, *, raise_error: bool = False):
        load_node(self, data, sealed=self._sealed__, raise_error=raise_error)

    @classmethod
    def create_from(cls, data: dict):
        n = cls()
        n.load_from(data)
        return n

    @classmethod
    def create(cls, /, **kwargs):
        n = cls()
        is_sealed = n._sealed__
        n._seal()
        n.load_from(kwargs, raise_error=True)
        if not is_sealed:
            n._unseal()
        return n


class NodeList(list):
    type_: type[Node]

    def __init__(self, member_type: type[Node]):
        super().__init__()
        self.type_ = member_type

    def load_from(self, data: list):
        self.clear()
        for item in data:
            if isinstance(item, Node):
                self.append(item)
            else:
                node = self.type_()
                node.load_from(item)
                self.append(node)


def load_node(node: Node, d: dict, *, sealed: bool = False, raise_error: bool = False):
    for key, value in d.items():
        if key in node and isinstance(node[key], (Node, NodeList)):
            node[key].load_from(value)
        elif key in node:
            node[key] = value
        elif not sealed:
            if isinstance(value, dict):
                node[key] = Node()
                node[key].load_from(value)
            elif isinstance(value, (list, tuple)):
                if isinstance(value, tuple):
                    value = list(value)
                if value and isinstance(value[0], dict):
                    node[key] = NodeList(Node)
                    node[key].load_from(value)
                else:
                    node[key] = value
            else:
                node[key] = value
        elif raise_error:
            raise KeyError(key)


def represent_node(dumper: Dumper, data: Node):
    return dumper.represent_dict(data)


def represent_node_list(dumper: Dumper, data: NodeList):
    return dumper.represent_list(data)


yaml.add_multi_representer(Node, represent_node)
yaml.add_multi_representer(NodeList, represent_node_list)
