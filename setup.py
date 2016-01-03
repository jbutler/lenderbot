#!/usr/bin/env python3

from distutils.core import setup

setup(name='lenderbot',
      version='1.0.6',
      description='LendingClub auto investor tool',
      author='Joe Butler',
      author_email='joebutler88@gmail.com',
      packages=['investor'],
      install_requires=['requests', 'pyparsing'],
)
