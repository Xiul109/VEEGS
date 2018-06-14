#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

__version__ = "0.2.1"

setup(name='veegs',
      version = __version__,
      description='A tool for plotting and logging EEG data from CSV files. The initials stands for Visualization EEG Software',
      author='Luis Cabañero Gómez',
      author_email='luiscabanerogomezxcr@hotmail.com',
#      url='',
      scripts=['veegs/bin/VEEGS'],
      packages=['veegs'],
      package_data={'veegs': ['resources/*','*.ui']},
      license='MIT',
      classifiers=[
          'Development Status :: 4 - Beta',

          'Intended Audience :: Developers',
          'Intended Audience :: Science/Research',

          'License :: OSI Approved :: MIT',

          'Programming Language :: Python :: 3',
          'Topic :: Scientific/Engineering::EEG',
      ],
      keywords='lib EEG signal analysis',

      install_requires = ['numpy', 'eeglib','PyQt5','pyqtgraph']
)
