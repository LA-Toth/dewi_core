# Copyright 2021-2022 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

import collections.abc
import os
import os.path
import pathlib
import typing

from dewi_core.config.appconfig import get_config as app_config
from dewi_core.config.iniconfig import IniConfig
from dewi_core.logger import log_debug
from dewi_core.utils.files import find_file_recursively

ANY_VERSION = '*'
INITIAL_VERSION = '0'


class Project:
    CFG_FILE = 'project.cfg'
    VERSION = 2

    def __init__(self, name: str):
        self.name = name
        self._project_dir = f'{app_config().projectdir}/{name}'
        self.config = IniConfig()
        self.config.open(f'{self._project_dir}/{self.CFG_FILE}')
        self.ext = _project_ext_type(self) if _project_ext_type else None

    @property
    def project_dir(self) -> str:
        return self._project_dir

    @property
    def etc_dir(self) -> str:
        return f'{self._project_dir}/etc'

    @property
    def src_dir(self) -> str:
        return f'{self._project_dir}/src'

    @property
    def tmp_dir(self) -> str:
        return f'{self._project_dir}/tmp'

    @property
    def branch(self) -> str:
        return self.config.get('main', 'branch')

    @property
    def upstream_branch(self) -> str:
        return self.config.get('main', 'upstream_branch')

    @property
    def remote(self) -> str:
        return self.config.get('main', 'remote')

    @property
    def ticket_id(self) -> str:
        return self.config.get('main', 'ticket_id')

    def repo_dir(self, repo: str) -> str:
        return f'{self.src_dir}/{repo}'

    @property
    def repositories(self) -> collections.abc.Iterable[str]:
        for entry in os.listdir(self.src_dir):
            if os.path.exists(f'{self.repo_dir(entry)}/.git'):
                yield entry

    @property
    def version(self) -> str:
        return self.config.get('core', 'version')

    @property
    def custom_version(self) -> str:
        return self.config.get_or_default_value('core', 'custom_version', INITIAL_VERSION)

    def as_dict(self) -> dict[str, typing.Any]:
        return dict(
            name=self.name,
            branch=self.branch,
            upstream=dict(remote=self.remote,
                          branch=self.upstream_branch),
            ticket_id=self.ticket_id,
            repositories=list(self.repositories)
        )


class ProjectExtension:
    """
    Additional fields and functionality to extend Project class without changing it.
    """

    def __init__(self, project: Project):
        self.project = project
        self.config = project.config


class ProjectError(RuntimeError):
    pass


class ProjectUpdateError(ProjectError):
    pass


def create_project(name: str | None = None) -> Project:
    return _create_project(name)


def _create_project(name: str | None = None, *,
                    branch: str | None = None,
                    upstream_remote: str | None = None,
                    upstream_branch: str | None = None,
                    ticket_id: str | None = None) -> Project:
    project_dir = app_config().projectdir
    if not name or name == '.':
        fname = find_file_recursively(Project.CFG_FILE)
        if not fname and os.getcwd().startswith(project_dir):
            fname = os.path.join(project_dir,
                                 os.getcwd()[len(project_dir) + len(os.sep):].split(os.sep, 1)[0],
                                 Project.CFG_FILE)
        if not fname:
            raise ProjectError(f"Current directory is not part of any project; directory={os.getcwd()}")
        name = os.path.basename(os.path.dirname(fname))

    log_debug('Creating project directory if not exists', dict(directory=os.path.join(project_dir, name)))
    os.makedirs(os.path.join(project_dir, name), exist_ok=True)
    update_project(name, branch=branch, upstream_remote=upstream_remote, upstream_branch=upstream_branch,
                   ticket_id=ticket_id)
    return Project(name)


def create_project_with_details(name: str, *, branch: str, upstream_remote: str, upstream_branch: str,
                                ticket_id: str) -> Project:
    return _create_project(name, branch=branch, upstream_remote=upstream_remote, upstream_branch=upstream_branch,
                           ticket_id=ticket_id)


def update_project(project_name: str, *,
                   branch: str | None = None,
                   upstream_remote: str | None = None,
                   upstream_branch: str | None = None,
                   ticket_id: str | None = None):
    project_dir = f'{app_config().projectdir}/{project_name}'
    if not os.path.exists(os.path.join(project_dir, Project.CFG_FILE)):
        log_debug('Initial, still non-existing project config')
        core_version = INITIAL_VERSION
        custom_version = INITIAL_VERSION
    else:
        log_debug('Selecting version specific Updater')
        core_version, custom_version = _get_core_and_custom_version(project_dir)

    while True:
        updaters = []
        if core_version in _registered_core_updaters:
            updaters += _registered_core_updaters[core_version]
        updaters += _registered_core_updaters[ANY_VERSION]

        if updaters:
            MultiUpdater(project_dir, branch=branch, upstream_remote=upstream_remote, upstream_branch=upstream_branch,
                         ticket_id=ticket_id,
                         updaters=updaters).update()

        while True:
            updaters = []
            if custom_version in _registered_updaters:
                updaters += _registered_updaters[custom_version]
            updaters += _registered_updaters[ANY_VERSION]

            if not updaters:
                break

            MultiUpdater(project_dir, branch=branch, upstream_remote=upstream_remote, upstream_branch=upstream_branch,
                         ticket_id=ticket_id,
                         updaters=updaters).update()

            _, new_custom_version = _get_core_and_custom_version(project_dir)
            if new_custom_version == custom_version:
                break
            else:
                custom_version = new_custom_version

        new_core_version, _ = _get_core_and_custom_version(project_dir)

        if new_core_version == core_version:
            break

        else:
            core_version = new_core_version


def _get_core_and_custom_version(project_dir: str) -> tuple[str, str]:
    cfg = IniConfig()
    cfg.open(os.path.join(project_dir, Project.CFG_FILE))
    core_version = cfg.get('core', 'version')
    custom_version = cfg.get_or_default_value('core', 'custom_version', INITIAL_VERSION)
    return core_version, custom_version


class Updater:
    def __init__(self, project_dir: str, ):
        self._project_dir = project_dir

    def update(self):
        raise NotImplementedError()

    def _create_dir_if_missing(self, directory: str, *, with_dot_keep_file: bool = False):
        directory = os.path.join(self._project_dir, directory)
        if not os.path.exists(directory):
            log_debug('Creating project subdirectory', dict(directory=directory))
            os.makedirs(directory, exist_ok=True)
        if with_dot_keep_file:
            filename = os.path.join(directory, '.keep')
            if not os.path.exists(filename):
                log_debug('Add missing .keep file', dict(directory=directory))
                pathlib.Path(filename).touch()

    def _open_cfg(self) -> IniConfig:
        cfg = IniConfig()
        cfg.open(os.path.join(self._project_dir, Project.CFG_FILE))
        return cfg

    def _core_version(self, cfg: IniConfig) -> str:
        return cfg.get('core', 'version')

    def _custom_version(self, cfg: IniConfig) -> str:
        return cfg.get_or_default_value('core', 'custom_version', INITIAL_VERSION)

    def _set_custom_version(self, cfg: IniConfig, version: str):
        cfg.set('core', 'custom_version', version)


class DetailedUpdater(Updater):
    def __init__(self, project_dir: str, *,
                 branch: str | None = None,
                 upstream_remote: str | None = None,
                 upstream_branch: str | None = None,
                 ticket_id: str | None = None):
        super().__init__(project_dir)
        self._name = os.path.basename(self._project_dir)
        self._branch = branch or ''
        self._upstream_remote = upstream_remote or ''
        self._upstream_branch = upstream_branch or ''
        self._ticket_id = ticket_id or ''


class NoopUpdater(Updater):
    def __init__(self, project_dir: str):
        super().__init__(project_dir)

    def update(self):
        pass


class MultiUpdater(DetailedUpdater):
    def __init__(self, project_dir: str, *,
                 branch: str | None = None,
                 upstream_remote: str | None = None,
                 upstream_branch: str | None = None,
                 ticket_id: str | None = None,
                 updaters: list[type[Updater]]):
        super().__init__(project_dir, branch=branch, upstream_remote=upstream_remote, upstream_branch=upstream_branch,
                         ticket_id=ticket_id)
        self._updaters = updaters

    def update(self):
        for updater_cls in self._updaters:
            if issubclass(updater_cls, DetailedUpdater):
                updater = updater_cls(self._project_dir, branch=self._branch, upstream_remote=self._upstream_remote,
                                      upstream_branch=self._upstream_branch,
                                      ticket_id=self._ticket_id)
            else:
                updater = updater_cls(self._project_dir)

            updater.update()


class ProjectUpdaterV1(DetailedUpdater):

    def update(self):
        self._ensure_subdir_hierarchy()
        self._write_project_config()

    def _ensure_subdir_hierarchy(self):
        self._create_dir_if_missing('src', with_dot_keep_file=True)
        self._create_dir_if_missing('etc', with_dot_keep_file=True)
        self._create_dir_if_missing('tmp', with_dot_keep_file=True)

    def _write_project_config(self):
        if not self._ticket_id or not self._upstream_branch or not self._branch:
            raise ProjectUpdateError('Missing details')
        cfg = IniConfig()
        cfg.config_file = os.path.join(self._project_dir, Project.CFG_FILE)
        cfg.set('core', 'version', '1')
        cfg.set('core', 'custom_version', INITIAL_VERSION)
        # branch is git branch, name is the project directory name
        cfg.set('core', 'name', self._name)
        cfg.set('main', 'branch', self._branch)
        cfg.set('main', 'ticket_id', self._ticket_id)
        cfg.set('main', 'maint_branch', self._upstream_branch)
        cfg.set('main', 'remote', self._upstream_remote)
        cfg.write()


class ProjectUpdaterV2(Updater):

    def update(self):
        cfg = self._open_cfg()
        cfg.set('core', 'version', '2')
        cfg.set('main', 'upstream_branch', cfg.get('main', 'maint_branch'))
        cfg.remove('main', 'maint_branch')
        cfg.write()


# Each version can have one or more updater
# '0' means: initial update
# '*' means: always run regardless of current version, aka. mandatory updater
# Behaviour:
#   for every core version starting with zero:
#        run version specific core updaters
#        and run mandatory core updaters (ANY_VERSION)
#        for every custom version starting with current version (initially: zero)
#                    run version specific custom updaters
#                    run mandatory custom updaters
# It is possible that later the actul upgrade will be the following sequence:
#   core updater to v1, custom updater to v1, core updater to v2, custom to v2 and v3, core to v3, custom to v4 etc.
# as each update can check the project's current state at that step and they may depend on a previous updater

_registered_core_updaters: dict[str, list[type[Updater]]] = {
    ANY_VERSION: [],
    INITIAL_VERSION: [ProjectUpdaterV1],
    '1': [ProjectUpdaterV2],
}

# custom updaters based on core.custom_version field
_registered_updaters: dict[str, list[type[Updater]]] = {ANY_VERSION: [], INITIAL_VERSION: []}

_project_ext_type: type[ProjectExtension] | None = None


def register_updater(version: str, updater: type[Updater]):
    global _registered_updaters
    if version not in _registered_updaters:
        _registered_updaters[version] = []

    _registered_updaters[version].append(updater)


def register_updater_to_all(updater: type[Updater]):
    _registered_updaters[ANY_VERSION].append(updater)


def register_project_extension(ext: type[ProjectExtension]):
    global _project_ext_type

    _project_ext_type = ext
