# Copyright 2020-2021 Laszlo Attila Toth
# Distributed under the terms of the GNU Lesser General Public License v3
# The license can be found in COPYING file or on http://www.gnu.org/licenses/

import os.path
import typing

from .iniconfig import IniConfig

DEFAULT_CONFIG_PATH = os.path.expanduser('~/.config/dewi/config.ini')


class AppConfig(IniConfig):
    remote_mode = False

    @property
    def basedir(self) -> str:
        return self.get('core', 'basedir')

    @property
    def etcdir(self) -> str:
        return f'{self.basedir}/etc'

    @property
    def projectdir(self) -> str:
        return f'{self.basedir}/projects'

    @property
    def srcdir(self) -> str:
        return os.path.join(self.basedir, 'src')

    @property
    def tmpdir(self) -> str:
        return os.path.join(self.basedir, 'tmp')

    def repo_dir_of(self, repo_name: str) -> str:
        return os.path.join(self.srcdir, 'bare', repo_name)


_config: AppConfig = None


def get_config(path: typing.Optional[str] = None) -> AppConfig:
    global _config
    if not _config:
        config = AppConfig()
        config.open(path or DEFAULT_CONFIG_PATH)
        _config = config

    return _config


def _set_config(cfg: typing.Optional[AppConfig]):
    global _config
    _config = cfg
