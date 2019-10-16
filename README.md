# gem5art: Artifact, reproducibility, and testing utilities for gem5

## Installing gem5art

To install gem5art, simply use pip.
We suggest creating a virtual environment first.
Note that gem5art requires Python 3, so be sure to use a Python 3 interpreter when creating the virtual environment

```sh
virtualenv -p python3
pip install gem5art-artifact gem5art-run gem5art-tasks
```

It's not required to install all of the gem5art utilities (e.g., you can skip gem5art-tasks if you don't want to use the celery job server).


## Directory structure

The directory structure is a little strange so we can distribute each Python package separately.
However, they are all part of the gem5art namespace.
See the [Python namespace documentation](https://packaging.python.org/guides/packaging-namespace-packages/) for more details.

## Building for distribution

1. Run the setup.py (this can be done from either the root directory as shown below or in each subdirectory.)

```sh
python run/setup.py sdist
python artifact/setup.py sdist
python tasks/setup.py sdist
```

2. Upload to PyPI

```sh
twine upload dist/*
```
