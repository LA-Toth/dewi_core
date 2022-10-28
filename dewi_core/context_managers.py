# Copyright 2016-2022 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0
import io
import os
import sys


def redirect_outputs(stdout=None, stderr=None):
    class Redirection:
        def __init__(self):
            self.stdout = stdout or io.StringIO()
            self.stderr = stderr or io.StringIO()

            self._saved_stdouts = []
            self._saved_stderrs = []

        def __enter__(self):
            self._saved_stdouts.append(sys.stdout)
            self._saved_stderrs.append(sys.stderr)

            sys.stdout = self.stdout
            sys.stderr = self.stderr

            return self

        def __exit__(self, *args):
            sys.stdout = self._saved_stdouts.pop()
            sys.stderr = self._saved_stderrs.pop()

    return Redirection()


def in_directory(directory: str):
    class InDirectory:
        _old_directories: list[str]
        _directory: str

        def __init__(self, directory: str):
            self._directory = directory
            self._old_directories = list()

        def __enter__(self):
            self._old_directories.append(os.getcwd())
            os.chdir(self._directory)

        def __exit__(self, exc_type, exc_val, exc_tb):
            os.chdir(self._old_directories.pop())

    return InDirectory(directory)
