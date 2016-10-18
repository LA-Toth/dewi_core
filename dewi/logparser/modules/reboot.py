# Copyright 2016 Laszlo Attila Toth
# Distributed under the terms of the GNU General Public License v3

from dewi.module_framework.messages import Level
from steve.commands.debug_bundle_processor.logparsers.base_module import BaseModule


class RebootModule(BaseModule):
    """
    Example module that calculates reboots on a system that have @reboot cron jobs
    """

    def get_registration(self):
        return [
            {
                'program': 'cron',
                'message_substring': '(CRON) INFO (Running @reboot jobs)',
                'callback': self.system_reboot
            }
        ]

    def start(self):
        self._reboots = list()

    def system_reboot(self, time, program, pid, msg):
        self._reboots.append(time)

    def finish(self):
        if len(self._reboots):
            self.add_message(
                Level.WARNING, 'System',
                "System is rebooted; count='{}'".format(len(self._reboots)))

            for reboot_time in self._reboots:
                self.append('system.reboots', reboot_time)
