# Copyright 2015-2021 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

from dewi_core.commandregistry import CommandRegistry
from dewi_core.config.node import Node
from dewi_core.config_env import ConfigDirRegistry


class ContextError(Exception):
    pass


class ContextEntryNotFound(ContextError):
    pass


class ContextEntryAlreadyRegistered(ContextError):
    pass


class Context(Node):
    """
    A context is a generic purpose registry, which helps
    communicate between different parts of the code. Instead of a global variable
    or module is for storing object(s), the context can be used and passed around
    the necessary objects and functions.

    An example: a CommandRegistry object can be registered into this context.
    """

    RESERVED_KEYS = ['command_registry', 'commands', 'config_dir_registry']

    def __init__(self, command_registry: CommandRegistry, config_dir_registry: ConfigDirRegistry):
        self.command_registry = command_registry
        self.commands = command_registry
        self.config_dir_registry = config_dir_registry

    def register(self, name: str, value):
        """
        Registers an element into the context. It doesn't support overwriting already
        registered entries, in that case `ContextEntryAlreadyRegistered` will be raised.

        :param name: the name of the new entry
        :param value: the value of the new entry
       """
        if name in self:
            raise ContextEntryAlreadyRegistered("Context entry {!r} already registered".format(name))
        self[name] = value

    def unregister(self, name: str):
        """
        Unregisters an already registered entry
        :param name: The name of the entry to be unregistered
        """
        self._check_entry(name)

        if name in self.RESERVED_KEYS:
            raise ContextError(f'Reserved key {name} cannot be unregistered')
        del self.__dict__[name]

    def _check_entry(self, name: str):
        if name not in self:
            raise ContextEntryNotFound("Requested context entry {!r} is not registered".format(name))

    def __getitem__(self, item):
        self._check_entry(item)
        return super().__getitem__(item)

    def __contains__(self, item):
        return item in self.__dict__
