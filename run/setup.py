"""A setuptools based setup module."""

from os.path import join
from pathlib import Path
from setuptools import setup, find_namespace_packages


with open(Path(__file__).parent / 'README.md', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name = "gem5art-run",
    version = "0.2.1",
    description = "A collection of utilities for running gem5",
    long_description = long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/darchr/gem5art',
    author='Davis Architecture Research Group (DArchR)',
    author_email='jlowepower@ucdavis.edu',
    license='BSD',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: BSD License',
        'Topic :: System :: Hardware',
        'Intended Audience :: Science/Research',
        'Programming Language :: Python :: 3',
        ],
    keywords='simulation architecture gem5',
    packages=find_namespace_packages(),
    install_requires=['gem5art-artifact'],
    python_requires='>=3.6',
    project_urls={
        'Bug Reports':'https://github.com/darchr/gem5art/issues',
        'Source':'https://github.com/darchr/gem5art',
        'Documentation':'https://gem5art.readthedocs.io/en/latest/',
    }
)
