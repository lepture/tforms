#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup
import tforms


setup(
    name = 'tforms',
    version = tforms.__version__,
    author = 'Hsiaoming Young',
    author_email = 'lepture@me.com',
    url = 'http://github.com/lepture/tforms',
    packages = ['tforms'],
    description = 'A simple form frameworks for tornado',
    license = 'BSD License',
    install_requires=['tornado'],
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX',
        'Operating System :: MacOS',
        'Programming Language :: Python',
    ]
)
