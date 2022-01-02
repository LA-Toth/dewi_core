import sys

import click

import dewi_core.testcase
from dewi_core.context_managers import redirect_outputs
from dewi_core.optioncontext import OptionContext


def _i(s: str, i: int):
    return (' ' * (i * 2)) + s


class _InvokableTestBase(dewi_core.testcase.TestCase):
    APP_NAME = 'myprogram'
    HELP_ARGS = ['--help']

    def _invoke(self, optctx: OptionContext, callback: callable, args, *, expected_exit_value=1):
        @click.pass_context
        def r(cctx: click.Context, *_args, **_kwargs):
            sys.exit(callback(cctx.params) or 0)

        optctx.add_args_to_func(r)
        r = click.command(self.APP_NAME)(r)
        with self.assert_raises(SystemExit) as context:
            r(args, self.APP_NAME)

        self.assert_equal(expected_exit_value, context.exception.code)

    def _invoke_redirected(self, optctx: OptionContext, callback: callable, args, *, expected_exit_value=1):
        with redirect_outputs() as redirection:
            self._invoke(optctx, callback, args, expected_exit_value=expected_exit_value)

        return redirection

    def _dummy(*_, **_kw):
        pass

    def assert_empty_redirection(self, r):
        self.assert_equal('', r.stdout.getvalue())
        self.assert_equal('', r.stderr.getvalue())


class OptionContextTest(_InvokableTestBase):

    def test_embedded_groups(self):
        params = dict()

        def f(p):
            nonlocal params
            params = p

        self.tested = OptionContext()
        self.tested.add_option('--first-option', help='The first option')
        grp = self.tested.add_group()
        grp.add_option('--grp1', dest='grp1arg', is_flag=True, )
        self.tested.add_option('--second-option', is_flag=True, )
        grp2 = self.tested.add_group('A title')
        self.tested.add_option('--3rd-option', dest='opt3', is_flag=True, )
        grp2.add_option('--grp2', dest='grp2arg', is_flag=True, )
        grp.add_option('--grp1-second', is_flag=True, )

        r = self._invoke_redirected(self.tested, f, self.HELP_ARGS, expected_exit_value=0)
        self.assert_equal({}, params)
        self.assert_equal('', r.stderr.getvalue())
        lines = r.stdout.getvalue().splitlines(keepends=False)
        self.assert_equal(11, len(lines))
        self.assert_true(lines[0].startswith('Usage'))
        self.assert_equal(
            ['Options:', _i('--first-option TEXT  The first option', 1), _i('--grp1', 2), _i('--grp1-second', 2),
             _i('--second-option', 1), _i('A title: ', 1), _i('--grp2', 2), _i('--3rd-option', 1)],
            lines[2:-1])

        r = self._invoke_redirected(self.tested, f, ['--first-option', 'something'], expected_exit_value=0)
        self.assert_equal({'first_option': 'something', 'grp1arg': False, 'grp1_second': False, 'second_option': False,
                           'grp2arg': False, 'opt3': False}, params)
        self.assert_equal('', r.stdout.getvalue())
        self.assert_equal('', r.stderr.getvalue())


class OptionContextWithNestedGroupsTest(_InvokableTestBase):

    def set_up(self):
        self.tested = OptionContext()
        db = self.tested.add_mutually_exclusive_group('Database settings', required=True)
        db.add_option('--config-file')
        settings = db.add_group(require_all=True)
        pw = settings.add_mutually_exclusive_group()
        pw.add_option('--password')
        pw.add_option('--password-file')
        settings.add_option('--host')
        settings.add_option('--port', type=int)
        self.params = {}

    def f(self, p):
        self.params = p

    def test_help(self):
        r = self._invoke_redirected(self.tested, self._dummy, self.HELP_ARGS, expected_exit_value=0)
        self.assert_equal('', r.stderr.getvalue())

    def test_top_level_xgrp_regular_param(self):
        r = self._invoke_redirected(self.tested, self.f, ['--config-file', 'ff'], expected_exit_value=0)
        self.assert_empty_redirection(r)
        self.assert_equal({'config_file': 'ff',
                           'host': None,
                           'password': None,
                           'password_file': None,
                           'port': None},
                          self.params)

    def test_top_level_xgrp_requires_single_option(self):
        r = self._invoke_redirected(self.tested, self.f, [], expected_exit_value=2)
        self.assert_equal('', r.stdout.getvalue())
        self.assert_in("'--config-file'", r.stderr.getvalue())

    def test_top_level_xgrp_requires_all_suboptions1(self):
        r = self._invoke_redirected(self.tested, self.f, ['--host', 'x'], expected_exit_value=2)
        self.assert_equal('', r.stdout.getvalue())
        self.assert_in("'--port", r.stderr.getvalue())

    def test_top_level_xgrp_requires_all_suboptions2(self):
        r = self._invoke_redirected(self.tested, self.f, ['--host', 'x', '--port', '42'], expected_exit_value=2)
        self.assert_equal('', r.stdout.getvalue())
        self.assert_in("'--password", r.stderr.getvalue())

    def test_top_level_xgrp_pass_if_all_suboptions_set(self):
        r = self._invoke_redirected(self.tested, self.f, ['--host', 'example', '--port', '42', '--password', 'foo'],
                                    expected_exit_value=0)
        self.assert_empty_redirection(r)
        self.assert_equal({'config_file': None,
                           'host': 'example',
                           'password': 'foo',
                           'password_file': None,
                           'port': 42},
                          self.params)


class NestedGroupsDontAllowSameSubGroup(dewi_core.testcase.TestCase):
    def test_option_context_add_group_cant_have_subgroup(self):
        tested = OptionContext().add_group()
        self.assert_false(hasattr(tested, 'add_group'))
        self.assert_false(hasattr(tested, 'add_mutually_exclusive_group'))

    def test_group_can_only_have_mutually_exclusive_group(self):
        tested = OptionContext().add_multilevel_group()
        self.assert_false(hasattr(tested, 'add_group'))
        self.assert_true(hasattr(tested, 'add_mutually_exclusive_group'))

    def test_mutually_exclusive_group_cant_have_same_group(self):
        tested = OptionContext().add_mutually_exclusive_group()
        self.assert_true(hasattr(tested, 'add_group'))
        self.assert_false(hasattr(tested, 'add_mutually_exclusive_group'))

    def test_deep_hierarchy_keeps_different_subgroup_invariant(self):
        tested = OptionContext().add_multilevel_group().add_mutually_exclusive_group()
        self.assert_true(hasattr(tested, 'add_group'))
        self.assert_false(hasattr(tested, 'add_mutually_exclusive_group'))
        tested = OptionContext().add_mutually_exclusive_group().add_group()
        self.assert_false(hasattr(tested, 'add_group'))
        self.assert_true(hasattr(tested, 'add_mutually_exclusive_group'))
