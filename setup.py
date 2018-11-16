# coding: utf-8

from setuptools import setup

setup(
    name = 'singularity',
    packages = ['singularity'],
    version = "0.1",
    license = "LGPLv3+",
    author = "João S. O. Bueno",
    author_email = "gwidion@gmail.com",
    description = "Rich Data Tools - multi-serialiser and acessor package",
    keywords = "data management",
    py_modules = ['singularity'],
    url = 'https://github.com/jsbueno/singularity',
    long_description = open('README.md').read(),
    requires=['dateparser'],
    test_requires = ['pytest'],
    classifiers = [
        "Development Status :: 2 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
    ]
)
