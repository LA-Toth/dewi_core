#  Copyright 2026, Laszlo Attila Toth
#  Distributed under the terms of the Apache License, Version 2.0

"""Tests for serialising an ApplicationContext across a process boundary."""

import dewi_core.testcase
from dewi_core.appcontext import ApplicationContext
from dewi_core.remoting import (deserialize_application_context,
                                serialize_application_context)
from dewi_dataclass import DataClass


class RemotingTest(dewi_core.testcase.TestCase):
    def set_up(self):
        self.ctx = ApplicationContext()
        self.ctx.program_name = 'the-app'
        self.ctx.environment = 'development'
        self.ctx.add_arg('log_dir', '/var/log')
        self.ctx.command_names.command = 'worktime'

    def test_that_the_serialised_form_is_a_plain_mapping(self):
        result = serialize_application_context(self.ctx)

        self.assert_is_instance(result, dict)
        self.assert_equal('the-app', result['program_name'])

    def test_that_the_command_registry_is_left_out(self):
        """It holds live command classes, which cannot cross a boundary."""
        self.assert_not_in('command_registry', serialize_application_context(self.ctx))

    def test_that_serialising_does_not_share_state_with_the_original(self):
        result = serialize_application_context(self.ctx)
        result['args'].program_name = 'changed'

        self.assert_equal('the-app', self.ctx.program_name)

    def test_that_a_context_round_trips(self):
        restored = deserialize_application_context(serialize_application_context(self.ctx))

        self.assert_is_instance(restored, ApplicationContext)
        self.assert_equal('the-app', restored.program_name)
        self.assert_equal('development', restored.environment)

    def test_that_nested_nodes_survive_the_round_trip(self):
        restored = deserialize_application_context(serialize_application_context(self.ctx))

        self.assert_equal('/var/log', restored.args.log_dir)
        self.assert_equal('worktime', restored.command_names.command)

    def test_that_the_restored_context_has_no_registry(self):
        restored = deserialize_application_context(serialize_application_context(self.ctx))

        self.assert_is_none(restored.command_registry)

    def test_that_the_arg_bags_stay_data_classes(self):
        restored = deserialize_application_context(serialize_application_context(self.ctx))

        self.assert_is_instance(restored.args, DataClass)


if __name__ == '__main__':
    import unittest

    unittest.main()
