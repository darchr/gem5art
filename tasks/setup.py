"""A setuptools based setup module."""

from os.path import join
from pathlib import Path
from setuptools import setup, find_packages


with open(Path(__file__).parent / 'README.md', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name = "gem5art-tasks",
    version = "0.2.0",
    description = "A celery app for gem5art",
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
    packages=find_packages(),
    install_requires=['pymongo', 'celery'],
    extras_require={
         'flower': ['flower'],
    },
    python_requires='>=3.6',
    project_urls={
        'Bug Reports':'https://github.com/darchr/gem5art/issues',
        'Source':'https://github.com/darchr/gem5art',
        'Documentation':'https://gem5art.readthedocs.io/en/latest/',
    }
)
