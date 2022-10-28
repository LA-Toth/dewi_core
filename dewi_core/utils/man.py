# Copyright 2021-2022 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

# vim: ts=8 sts=4 sw=4 et ai si
import abc
import argparse
import inspect
import os
import random
import re
import subprocess

from dewi_core.command import Command

XMLTO_XSL_DIR = os.path.join(os.path.dirname(__file__), 'xmlto_xsl')


class GeneratorConfig:
    def __init__(self, includes_dir: str, output_dir: str, app_name: str, *, app_version: str | None = None,
                 section: int = 1):
        self.includes_dir = includes_dir
        self.output_dir = output_dir
        self.app_name = app_name
        self.app_version = app_version or '1.0-SNAPSHOT'
        self.section = section

    def get_basename(self, cmd_name: str):
        if cmd_name:
            return f'{self.app_name}-{cmd_name.replace(" ", "-")}'
        else:
            return self.app_name

    def get_refentry_title(self, cmd_name: str):
        if cmd_name:
            return f'{self.app_name} {cmd_name}'
        else:
            return self.app_name

    def get_target_filename(self, cmd_name: str):
        return f'{self.output_dir}/{self.get_basename(cmd_name)}.{self.section}'

    def get_include_filename(self, include_name: str):
        return f'{self.includes_dir}/{include_name}.xml'


class Generator:
    def __init__(self, config: GeneratorConfig):
        self.config = config
        self._random = random.randint(1000, 100000)

    def _get_temp_dir(self):
        return f'/tmp/DEWI-MAN-{self._random}-{os.getpid()}/man-tmp'

    def _get_temp_file(self, cmd_name: str):
        return self._get_temp_dir() + '/tmp--' + self.config.get_basename(cmd_name) + '.xml.' + str(os.getpid())

    def print_man_page(self, source_file: str, cmd_name: str, doc: str):
        try:
            self.generate_man_page(source_file, cmd_name)
            if os.path.exists(self.config.get_target_filename(cmd_name)):
                subprocess.run(['man', self.config.get_target_filename(cmd_name)])
            else:
                print(doc)
        except subprocess.CalledProcessError:
            print("\nUnable to generate manual page. Perhaps \"xmlto\" is not installed?\n")
            print(doc)

    def generate_man_page(self, source_file: str, cmd_name: str) -> bool:
        if os.path.exists(source_file):
            self._generate_man_page(source_file)
            return True
        else:
            return False

    def _generate_man_page(self, source_file: str, cmd_name: str):
        if self._is_update_of_man_page_needed(source_file, cmd_name):
            self._update_man_page(source_file, cmd_name)

    def _is_update_of_man_page_needed(self, source_file: str, cmd_name: str):
        man_file = self.config.get_target_filename(cmd_name)
        xml_file = source_file

        def is_newer(f1: str, f2: str) -> bool:
            return os.path.getmtime(f1) > os.path.getmtime(f2)

        update = (not os.path.exists(man_file) or is_newer(xml_file, man_file))

        if not update:
            xf_content = open(xml_file).read().split('\n')
            for xf in xf_content:
                if re.match(r'<!-- include [^ ]+ -->', xf):
                    fname = self.config.get_include_filename(re.sub(r'^<!-- include ([^ ]+) -->', r'\1', xf))
                    if is_newer(fname, man_file):
                        update = True
                        break

        return update

    def _update_man_page(self, source_file: str, cmd_name: str):
        converted = ''
        refentrytitle_changed = False
        xf_content = open(source_file, encoding='UTF-8').read().split('\n')
        for xf in xf_content:
            if re.match(r'.*<refmiscinfo class="version">.*</refmiscinfo>', xf):
                converted += re.sub(
                    r'(<refmiscinfo class="version">).*(</refmiscinfo>)',
                    f'<refmiscinfo class="version">{self.config.app_version}</refmiscinfo>\n', xf)
            elif re.match(r'.*<refname>.*</refname>', xf):
                converted += '<refname>{0}</refname>\n'.format(os.path.basename(source_file)[:-4])
            elif not refentrytitle_changed and re.match(r'.*<refentrytitle>.*</refentrytitle>', xf):
                converted += f'<refentrytitle>{self.config.get_refentry_title()}</refentrytitle>\n'
                refentrytitle_changed = True
            elif re.match(r'<!-- include [^ ]+ -->', xf):
                fname = self.config.get_include_filename(re.sub(r'^<!-- include ([^ ]+) -->', r'\1', xf))
                converted += open(fname).read()
            elif re.match(r'.*\$CMDNAME\b.*', xf):
                converted += '%s\n' % re.sub(r'\$CMDNAME\b', self.config.app_name, xf)
            else:
                converted += '%s\n' % (xf,)

        os.makedirs(self._get_temp_dir(), exist_ok=True)
        tempfile = open(self._get_temp_file(cmd_name), "w")
        tempfile.write(converted)
        tempfile.close()

        os.makedirs(self.config.output_dir, exist_ok=True)

        subprocess.run([
            'xmlto', '-o', self.config.output_dir, '-m', 'manpage-normal.xsl',
            '-m', 'manpage-bold-literal.xsl', 'man', self._get_temp_file(cmd_name)],
            cwd=XMLTO_XSL_DIR, check=True)


class ManGeneratorConfigBase(abc.ABC):
    def __init__(self, app_name: str, man_name: str):
        self._app_name = app_name
        self._name = man_name
        self.tmpfile = ''
        self._random = random.randint(1000, 100000)

    def _set_name(self, name: str):
        self._name = name

    def get_name(self):
        return self._name

    @abc.abstractmethod
    def get_source_dir(self) -> str:
        pass

    @abc.abstractmethod
    def get_target_dir(self) -> str:
        pass

    def get_source_file(self):
        return self.get_source_dir() + '/' + self._get_base_file_name() + '.xml'

    def get_target_file(self):
        return f'{self.get_target_dir()}/{self._get_target_base_file_name()}.{self._get_section()}'

    def _get_section(self):
        return 1

    def get_temp_dir(self):
        return f'/tmp/DEWI-MAN-{self._random}-{os.getpid()}/man-tmp'

    def get_temp_file(self):
        if not self.tmpfile:
            self.tmpfile = self.get_temp_dir() + '/tmp--' + self._get_base_file_name() + '.xml.' + str(os.getpid())
        return self.tmpfile

    def _get_base_file_name(self):
        if self._name:
            return f'{self._app_name}-{self._name.replace(" ", "-")}'
        else:
            return self._app_name

    def _get_target_base_file_name(self):
        return self._get_base_file_name()

    def get_man_page_refname(self):
        return self._get_target_base_file_name()

    def get_man_page_refentrytitle(self):
        if self._name:
            return f'{self._app_name} {self._name}'
        else:
            return self._app_name

    def get_command_name(self):
        return self._app_name


def print_man_page(config: GeneratorConfig, ns: argparse.Namespace):
    cmd_class: type[Command] = ns.cmd_class_
    man_page_files = [(inspect.getfile(cmd_class), cmd_class.man_page_file)]
    name = ns.running_command_
    if 'running_subcommands_' in ns and ns.running_subcommands_:
        for sub_cmd_name in ns.running_subcommands_:
            for cc in cmd_class.subcommand_classes:
                if cc.name == sub_cmd_name:
                    cmd_class = cc
                    man_page_files.append((inspect.getfile(cmd_class), cmd_class.man_page_file))
                    name += f' {sub_cmd_name}'

    man_page_file = ''
    for entry in reversed(man_page_files):
        if entry[1]:
            man_page_file = os.path.abspath(os.path.join(os.path.dirname(entry[0]), entry[1]))

    g = Generator(config)
    # a subcommand may not have separate man page file but its use is mandatory
    # if no man page is specified (and the current method is called)
    return g.print_man_page(man_page_file, name, cmd_class.__doc__)
