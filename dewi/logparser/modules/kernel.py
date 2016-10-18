# Copyright 2016 Laszlo Attila Toth
# Distributed under the terms of the GNU General Public License v3

from dewi.module_framework.messages import Level
from steve.commands.debug_bundle_processor.logparsers.base_module import BaseModule


class KernelModule(BaseModule):
    """
    Example module to track processes which are unresponsible on a system having high - I/O - load
    """
    def get_registration(self):
        return [
            {
                'program': 'kernel',
                'message_substring': 'blocked for more than 120 seconds',
                'callback': self._blocked_process
            }
        ]

    def start(self):
        self._blocked_process_list = list()

    def _blocked_process(self, time, program, pid, msg):
        # example msg:
        # [16974495.906550] INFO: task java:14545 blocked for more than 120 seconds.

        parts = msg.split(' ', 4)
        self._blocked_process_list.append(dict(time=time, program=parts[3]))

    def finish(self):
        self.set('system.blocked_processes.count', len(self._blocked_process_list))
        if len(self._blocked_process_list):
            self.add_message(
                Level.WARNING, 'System',
                "Blocked processes; count='{}'".format(len(self._blocked_process_list)))

            for process in self._blocked_process_list:
                self.append('system.blocked_processes.details', process)
