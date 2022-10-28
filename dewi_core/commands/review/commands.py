# Copyright 2021-2022 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

import os
import re

from dewi_core.appcontext import ApplicationContext
from dewi_core.command import Command
from dewi_core.optioncontext import OptionContext


def register_global_args_in_review_cmd(c: OptionContext) -> None:
    """
    Register global args not listed in the subcommands but in parent ReviewCommand.

    Added here just to be always visible in this module.
    """
    c.add_option('-U', '--gerrit-ssh-user', 'gerrit_ssh_user',
                 help='SSH username to send review into gerrit')
    c.add_option('--upload-gerrit-review', '--review', 'upload_gerrit_review', is_flag=True,
                 help='Upload gerrit review. By default the code uses dry run and print the review instead.')

    c.add_option('-R', '--repo', 'gerrit_review_local_repo', required=True,
                 help='Location of the bare git repository. '
                      'Can be an existing repo or a non-existent directory.')


class AutoReviewSubCommand(Command):
    def run(self, ctx: ApplicationContext) -> int | None:
        # could prepare the repository
        print("Existing repo?: ", os.path.exists(ctx.commands_args['review'].gerrit_review_local_repo))
        self.args = ctx.args
        self.ctx = ctx
        return self._run()

    def _run(self) -> int | None:
        pass


class GerritChangeReviewer(AutoReviewSubCommand):
    name = 'change'
    aliases = ['single-change', 'chg']
    description = 'Review a single change (commit)'

    @staticmethod
    def register_arguments(c: OptionContext):
        c.add_option('--gerrit-url', dest='gerrit_url',
                     required=True, help='Gerrit URL without revision ID')
        c.add_option('--change-id', 'change_id', type=int,
                     help='Change ID, should be the same as the end of the gerrit URL')
        c.add_option('--gerrit-revision', '--revision', 'revision', type=int,
                     required=True, help='Revision of the change in gerrit url')

    def _run(self) -> int | None:
        try:
            gerrit_host, change_id = self._validate_args()
        except ValueError as exc:
            print(exc)
            return 1
        print('single change', gerrit_host, change_id, self.args.change_id, self.args.revision)
        return 0

    def _validate_args(self) -> tuple[str, int]:
        if self.args.change_id and not self.args.gerrit_url.endswith(f'/{self.args.change_id}'):
            raise ValueError('Unexpected change ID, differs from the one specified in Gerrit URL')

        m = re.match(r'https://([^/]+)/[a-z/#+]+/([0-9]+)$', self.args.gerrit_url)
        if not m:
            raise ValueError('Invalid gerrit URL, should be: host/project/changeid without revision')

        return m.group(1), int(m.group(2))


class GerritChangeChainReviewer(GerritChangeReviewer):
    name = 'chain'
    aliases = []
    description = 'Review a chain of changes (commits) with the gerrit URL as HEAD'

    @staticmethod
    def register_arguments(c: OptionContext) -> None:
        GerritChangeReviewer.register_arguments(c)
        # register own arguments
        c.add_option('-r', '--repo', 'gerrit_review_local_repo', help='Conflicts with parent command, should work')

    def _run(self) -> int | None:
        # process related changes to the specified one, as it contains the complete chain
        gerrit_host, change_id = self._validate_args()
        print('chain', gerrit_host, change_id, self.args.change_id, self.args.revision)
        return
