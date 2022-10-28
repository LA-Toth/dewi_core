# Copyright 2016-2022 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

import collections.abc


class _TypedDictionary(dict):
    def __init__(self, element_type: type):
        super().__init__()
        self._element_type = element_type

    def _add_element(self, key, value):
        raise NotImplementedError()

    def __setitem__(self, key, value):
        if key not in self:
            super().__setitem__(key, self._element_type())

        self._add_element(key, value)


class DictionaryWithList(_TypedDictionary):
    def __init__(self):
        super().__init__(list)

    def _add_element(self, key, value):
        self[key].append(value)


class DictionaryWithSet(_TypedDictionary):
    def __init__(self):
        super().__init__(set)

    def _add_element(self, key, value):
        self[key].add(value)


def sort_dict(d: collections.abc.Mapping) -> collections.OrderedDict:
    result = collections.OrderedDict()
    for key in sorted(list(d.keys())):
        result[key] = d[key]

    return result
