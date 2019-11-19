# Tutorial: Run Microbenchmarks with gem5

## Introduction
In this tutorial, we will learn how to run some simple microbenchmarks using gem5art.
Microbenchmarks are small benchmarks designed to test a component of a larger system.
The particular microbenchmarks we are using in this tutorial were originally developed at the
[University of Wisconsin-Madison](https://github.com/VerticalResearchGroup/microbench).
This microbenchmark suite is divided into different control, execution and memory benchmarks.
We will use system emulation (SE) mode of gem5 to run these microbenchmarks with gem5.


This tutorial follows the following directory structure:

- configs-micro-tests: the base gem5 configuration to be used to run full-system simulations
- gem5: gem5 [source code](https://gem5.googlesource.com/public/gem5) and the compiled binary

- results: directory to store the results of the experiments (generated once gem5 jobs are executed)
- launch_micro_tests.py:  gem5 jobs launch script (creates all of the needed artifacts as well)


## Setting up the environment
First, we need to create the main directory named micro-tests (from where we will run everything) and turn it into a git repository we did in the previous tutorials.
Next, add a git remote to this repo pointing to a remote location where we want this repo to be hosted.

```sh
mkdir micro-tests
cd micro-tests
git init
git remote add origin https://your-remote-add/micro-tests.git
```

We also need to add a .gitignore file in our git repo, to not track files we don't care about:

```
*.pyc
m5out
.vscode
results
venv
```

Next, we will create a virtual environment before using gem5art

```sh
virtualenv -p python3 venv
source venv/bin/activate
```

gem5art can be installed (if not already) using pip:

```sh
pip install gem5art-artifact gem5art-run gem5art-tasks
```

## Build gem5
Clone gem5 and build it (optionally, after making your changes):

```sh
git clone https://gem5.googlesource.com/public/gem5
cd gem5
scons build/X86/gem5.opt -j8
```

## Download and compile the microbenchmarks
Download the microbenchmarks:

```sh
git clone https://github.com/darchr/microbench.git
```

Commit the source of microbenchmarks to the micro-tests repo (so that the current version of microbenchmarks becomes a part of the micro-tests reposiotry).

```sh
git add microbench/
git commit -m "Add microbenchmarks"
```

compile the benchmarks:

```sh
cd microbench
make
```

By default, these microbenchmarks are compiled for x86 ISA (which will be our focus in this tutorial).
You can add ARM or RISCV to the make command (as shown below) to compile these benchmarks for ARM and RISC V ISAs.

```sh
make ARM

make RISCV
```

## gem5 run scripts

## Database and Celery Server

## Creating a launch script
