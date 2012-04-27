#!/usr/bin/python

from setuptools import setup

setup(
    name="piplint",
    license='Apache License 2.0',
    version="0.1.0",
    description="Checks packages in your active environment against pip requirements files",
    author="David Cramer",
    url="https://github.com/dcramer/piplint",
    packages=["piplint"],
    package_dir={'': 'src'},
    entry_points={
        'console_scripts': [
            'piplint = piplint:main',
        ],
    },
    classifiers=[
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Topic :: Software Development",
        "Topic :: Utilities",
    ])
