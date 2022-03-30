#!/usr/bin/env python3
#
# DEWI: a developer tool and framework -- Core part
# Copyright 2012-2021  Laszlo Attila Toth
# Distributed under the terms of the Apache License, Version 2.0

import sys

if sys.hexversion < 0x03080000:
    raise RuntimeError("Required python version: 3.8 or newer (current: %s)" % sys.version)

try:
    from setuptools import setup, find_packages

except ImportError:
    from distutils.core import setup

setup(
    name="dewi_core",
    description="DEWI Core: Plugin and Config Tree framework and Application",
    license="LGPLv3",
    version="5.1.1",
    author="Laszlo Attila Toth",
    author_email="python-dewi@laszloattilatoth.me",
    maintainer="Laszlo Attila Toth",
    maintainer_email="python-dewi@laszloattilatoth.me",
    keywords='tool framework development synchronization',
    url="https://github.com/LA-Toth/dewi_core",
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Software Development',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Utilities',
    ],
    zip_safe=True,
    use_2to3=False,
    python_requires='>=3.8',
    packages=find_packages(exclude=['*tests*', 'pylintcheckers']),
    install_requires=[
        'pyyaml',
        'click >=8.0, <9',
        'click_option_group',
    ]
)
