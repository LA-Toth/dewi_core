# Copyright 2017-2021 Laszlo Attila Toth
# Distributed under the terms of the GNU Lesser General Public License v3

import subprocess

from dewi_core.appcontext import ApplicationContext
from dewi_core.command import Command
from dewi_core.optioncontext import OptionContext


class XSshCommand(Command):
    """Logs into an SSH server and chroots on the server if necessary"""

    name = 'xssh'
    aliases = [
        'x' + postfix
        for postfix in ['chroot', 'srv']]
    description = "Start ssh to log in to a server or on a chroot"

    @staticmethod
    def register_arguments(c: OptionContext):
        c.add_argument('server', help='The SSH server address to log in to')

    def run(self, ctx: ApplicationContext):
        print(ctx.command_names)
        cmd = 'chroot /srv/chroot/example' if ctx.command_names.command.endswith('chroot') else 'bash'
        res = subprocess.run(
            ['ssh', '-oUserKnownHostsFile=/dev/null', '-oStrictHostKeyChecking=no',
             '-l', 'root', ctx.current_args.server, '-t', cmd])
        return res.returncode
