# Tutorial: Run Full System Linux Boot Tests

## Introduction

This tutorial explains how to use gem5art to run experiments with gem5. The specific experiment we will be doing is to perform linux boot test with gem5.
The main steps to perform such an experiment using gem5art include: setting up the environment,

This tutorial follows the following directory structure:

- configs-boot-tests: the base gem5 configuration to be used to run full-system simulations
- disk-image: contains packer script and template files used to build a disk image. The built disk image will be stored in the
  same folder
- gem5: gem5 source code. This points to darchr/gem5 repo
- linux-configs: different linux kernel configurations
- linux-stable: linux kernel source code used for full-system experiments
- results: directory to store the results of the experiments (generated once gem5 jobs are executed)
- launch_boot_tests.py:  gem5 jobs launch script (creates all of the needed artifacts as well)


## Setting up the environment

gem5art relies on Python 3, so we suggest creating a virtual environment before using gem5art.

```sh
virtualenv -p python3 venv
source venv/bin/activate
```

Create the main directory named boot-tests and turn it into a git repo:

```sh
mkdir boot-tests
cd boot-tests
git init
git remote add origin https://your-remote-add/boot-tests.git
```

We also need to add a .gitignore file in our git repo, to not track files we don't care about:

```sh
*.pyc
m5out
.vscode
results
venv
disk-image/packer
```
Through the use of boot-tests git repo, we will try to keep track of changes in those files which are not included in a git repo otherwise.


Now gem5art can be installed using pip:

```sh
pip install gem5art-artifact gem5art-run gem5art-tasks
```

To install gem5art from local source, first clone the gem5art repo in boot_tests and then do:

```sh
pip install -e artifact run tasks
pip install -e run
pip install -e tasks
```

## Building gem5

Clone gem5 and build it:

```sh
git clone https://github.com/darchr/gem5
cd gem5
scons build/X86/gem5.opt -j8
```
You can also add your changes to gem5 source before building it. Make sure to commit any changes you make to gem5 repo.

Also make sure to build the m5 utility which will be needed for disk image creation later on:

```sh
cd gem5/util/m5/
make -f Makefile.x86
```

## Creating a disk image
First create a disk-image folder where we will keep all disk image related files:

```sh
mkdir disk-image
```

Add a folder named shared for config files which will be shared among all disk images and one folder named boot-exit which is specific to the disk image needed to run experiments of this tutorial.

Add three files [boot-exit.json](https://github.com/darchr/gem5art/blob/master/docs/disks/boot-exit/boot-exit.json), [exit.sh](https://github.com/darchr/gem5art/blob/master/docs/disks/boot-exit/exit.sh) and [post-installation.sh](https://github.com/darchr/gem5art/blob/master/docs/disks/boot-exit/post-installation.sh) in boot-exit/ and [preseed.cfg](https://github.com/darchr/gem5art/blob/master/docs/disks/shared/preseed.cfg) and [serial-getty@.service](https://github.com/darchr/gem5art/blob/master/docs/disks/shared/serial-getty@.service) in shared/

Next, download packer in the disk-image folder:

```
cd disk-image/
wget https://releases.hashicorp.com/packer/1.4.3/packer_1.4.3_linux_amd64.zip
unzip packer_1.4.3_linux_amd64.zip
```
packer will be used to build disk image using previously added template file (boot-exit.json):

```
../packer validate boot-exit.json

../packer build boot-exit.json
```

## Compiling the linux kernel

Similar to getting gem5, you'll likely want to update the linux kernel.
The current kernel is a long term support kernel.
However, there may be bugfixes that need to be applied.

First, add a folder linux-configs to store linux kernel config files.
We will add [config](https://github.com/darchr/gem5art/blob/master/docs/linux-configs/config.5.2.3) file for kernel v5.2.3 in this folder.
Then, we will get the linux source and checkout the required linux version (5.2.3 in this case).

```
git clone https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git
mv linux linux-stable
cd 	linux-stable
git checkout v{version-no: e.g. 5.2.3}
```

Compile the linux kernel from its source (and an appropriate config file from linux-configs/):

```
cp ../linux-configs/config.{version-no: e.g. 5.2.3} .config
make -j8
cp vmlinux vmlinux-{version-no: e.g. 5.2.3}
```

## gem5 run scripts

Next we need to add gem5 run scripts. We will do that in a folder configs-boot-tests.
Get the run script and config files from [here](https://github.com/darchr/gem5art/blob/master/docs/configs-boot-tests/run_exit.py), and system files from
[here](https://github.com/darchr/gem5art/blob/master/docs/configs-boot-tests/system/).


## Creating a launch script
Finally, we will create a launch script, which will be responsible for creating artifacts first and then launching gem5 jobs.
Add a launch-script [launch_boot_tests.py](https://github.com/darchr/gem5art/blob/master/docs/launch_boot_tests.py)
Make sure you are in python virtual env and then do

```python
python launch_boot_tests.py
```