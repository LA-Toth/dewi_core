# Copyright 2019-2022 Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0
import os


def find_file_recursively(filename: str, directory_name: str | None = None) -> str | None:
    """
    Searches a filename in directory_name directory or in current directory
    if directory_name is None, or in their parent directories if the filename file
    is not found in the specific directory.

    The behaviour is the same as how git finds .gitignore, .git/ and other entries.

    :param filename: the filename to be found
    :param directory_name: the start directory, or if it is None: current directory
    :return: the absolute path of the searched file or None if it is not found
    """

    def maybe_file(filename: str, directory_name: str) -> str | None:
        full_path = os.path.join(directory_name, filename)
        if os.path.exists(full_path):
            return full_path
        else:
            return None

    directory_name = os.path.abspath(directory_name) if directory_name else os.getcwd()
    fname = maybe_file(filename, directory_name)
    while fname is None and directory_name and directory_name != os.path.sep:
        directory_name = os.path.dirname(directory_name)
        fname = maybe_file(filename, directory_name)

    return fname
