# Copyright 2021-2022 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

import copy
import typing

from dewi_core.appcontext import ApplicationContext


def serialize_application_context(ctx: ApplicationContext) \
        -> dict[str, typing.Any]:
    return copy.deepcopy({k: v for k, v in ctx if k != 'command_registry'})


def deserialize_application_context(serialized: dict[str, typing.Any]) -> ApplicationContext:
    return ApplicationContext.create_from(serialized)
