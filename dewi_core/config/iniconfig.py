# Copyright 2009-2022 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0
# vim: sts=4 ts=8 et ai

import configparser


class DictConfigParser(configparser.RawConfigParser):

    def as_dict(self) -> dict[str, dict[str, str]]:
        d = dict(self._sections)
        for k in d:
            d[k] = dict(self._defaults, **d[k])
            d[k].pop('__name__', None)
        return d


class IniConfig:

    def __init__(self):
        self.config_file = None
        self.parser = DictConfigParser()
        self.loaded_files = []

    def _section_from_dotted(self, section: str) -> str:
        s = section.split('.', 1)
        if len(s) == 2:
            return '%s "%s"' % tuple(s)
        else:
            return section

    def _section_to_dotted(self, section: str) -> str:
        s = section.split('"')
        if len(s) == 3:
            return '%s.%s' % (s[0][:-1], s[1])
        else:
            return section

    def open(self, cfgfile: str, /, *, merge: bool = False):
        if not merge:
            if self.config_file is not None:
                raise IniConfigError("Already opened with " + self.config_file)
            self.config_file = cfgfile
        elif not self.config_file:
            raise IniConfigError("No initial config is opened")
        self.loaded_files.append(cfgfile)
        self.parser.read(cfgfile, encoding='UTF-8')

    def extend(self, cfgfile: str):
        self.loaded_files.append(cfgfile)
        self.parser.read(cfgfile, encoding='UTF-8')

    def write(self, filename: str | None = None):
        if filename:
            self.config_file = filename
        if self.config_file is None:
            raise IniConfigError("Unable to save config file because file name is unset")
        with open(self.config_file, 'wt') as f:
            self.parser.write(f)

    def close(self):
        self.config_file = None
        self.loaded_files.clear()
        self.parser = DictConfigParser()

    def has(self, section: str, option: str) -> bool:
        section = self._section_from_dotted(section)
        return self.parser.has_option(section, option)

    def set(self, section: str, option: str, value):
        section = self._section_from_dotted(section)
        if not self.parser.has_section(section):
            self.parser.add_section(section)
        self.parser.set(section, option, value)

    def get(self, section: str, option: str) -> str | None:
        section = self._section_from_dotted(section)
        if not self.parser.has_section(section):
            return None
        try:
            return self.parser.get(section, option)
        except configparser.NoOptionError:
            return None

    def get_or_default_value(self, section: str, option: str, default_value: str) -> str:
        res = self.get(section, option)
        return res if res is not None else default_value

    def remove(self, section: str, option: str):
        section = self._section_from_dotted(section)
        if not self.parser.has_section(section):
            return
        if not self.parser.has_option(section, option):
            return
        self.parser.remove_option(section, option)

    def get_options(self, section: str) -> list[str]:
        section = self._section_from_dotted(section)
        if not self.parser.has_section(section):
            return []
        else:
            return self.parser.options(section)

    def get_sections(self) -> list[str]:
        return [self._section_to_dotted(s) for s in self.parser.sections()]

    def as_dict(self) -> dict[str, dict[str, str]]:
        return self.parser.as_dict()


class IniConfigError(Exception):
    pass


def convert_to_bool(val) -> bool:
    if not val:
        return False
    if isinstance(val, bool):
        return val
    lowered = val.lower()
    return lowered == 'y' or lowered == 'yes' or lowered == 't' or lowered == 'true'


def convert_from_bool(val: bool) -> str:
    return 'yes' if val else 'no'
