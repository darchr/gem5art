# Tutorial 1: Run Full System Linux Boot Tests

## Introduction

This tutorial explains how to use gem5art to run experiments with gem5. The specific experiment we will be doing is to test the linux kernel boot for various kernel versions and simulator configurations.
The main steps to perform such an experiment using gem5art include: setting up the environment, building gem5, creating a disk image, compiling linux kernels, preparing gem5 run script, creating a job launch script (which will also register all of the required artifacts) and finally running this script.

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
Through the use of boot-tests git repo, we will try to keep track of changes in those files which are not included in any git repo otherwise.
boot-tests will also serve as the directory from where we will run everything.

gem5art can be installed (if not already) using pip:

```sh
pip install gem5art-artifact gem5art-run gem5art-tasks
```

To install gem5art from a local source, first clone the gem5art repo in boot_tests and then do:

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

Also make sure to build the m5 utility which will be needed during disk image creation (specifically for post installation stuff) later on:

```sh
cd gem5/util/m5/
make -f Makefile.x86
```

## Creating a disk image
First create a disk-image folder where we will keep all disk image related files:

```sh
mkdir disk-image
```

We will follow the similar directory structure as discussed in [Disk Images](disks.md) section.
Add a folder named shared for config files which will be shared among all disk images (and will be kept to their defaults) and one folder named boot-exit which is specific to the disk image needed to run experiments of this tutorial.
Add three files [boot-exit.json](https://github.com/darchr/gem5art/blob/master/docs/disks/boot-exit/boot-exit.json), [exit.sh](https://github.com/darchr/gem5art/blob/master/docs/disks/boot-exit/exit.sh) and [post-installation.sh](https://github.com/darchr/gem5art/blob/master/docs/disks/boot-exit/post-installation.sh) in boot-exit/ and [preseed.cfg](https://github.com/darchr/gem5art/blob/master/docs/disks/shared/preseed.cfg) and [serial-getty@.service](https://github.com/darchr/gem5art/blob/master/docs/disks/shared/serial-getty@.service) in shared/

boot-exit.json is our primary .json configuration file. The provisioners and variables section of this file configure the files that need to be transferred to the disk and other things like disk image's name. post-installation.sh (which is a script to run after Ubuntu is installed on the disk image) makes sure that the m5 binary is installed on the system and also moves the content of our other script (exit.sh, which should be already transferred inside the disk image as configured in boot-exit.json) to .bashrc as exit.sh contains the stuff that we want to be executed as soon as the system boots. exit.sh just contains one command `m5 exit`, which will eventually terminate the simulation.

Next, download packer (if not already downloaded) in the disk-image folder:

```
cd disk-image/
wget https://releases.hashicorp.com/packer/1.4.3/packer_1.4.3_linux_amd64.zip
unzip packer_1.4.3_linux_amd64.zip
```
Now, to build the disk image, inside boot-exit folder, run:

```
../packer validate boot-exit.json

../packer build boot-exit.json
```

## Compiling the linux kernel

Similar to getting gem5, you'll likely want to update the linux kernel.
The current kernel is a long term support kernel.
However, there may be bugfixes that need to be applied.

In this tutorial, we want to experiment with different linux kernels to examine the state of gem5's ability to boot different linux kernels. The specific kernel versions we picked include: v5.2.3, v4.14.134, v4.9.186, and v4.4.186.

Let's use an example of kernel v5.2.3 to see how to compile the kernel.
First, add a folder linux-configs to store linux kernel config files. The configuration files of interest are available [here](https://github.com/darchr/gem5art/blob/master/docs/linux-configs/).
Then, we will get the linux source and checkout the required linux version (e.g. 5.2.3 in this case).

```
git clone https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git
mv linux linux-stable
cd linux-stable
git checkout v{version-no: e.g. 5.2.3}
```
Compile the linux kernel from its source (and an appropriate config file from linux-configs/):

```
cp ../linux-configs/config.{version-no: e.g. 5.2.3} .config
make -j8
cp vmlinux vmlinux-{version-no: e.g. 5.2.3}
```

Repeat the above process for other kernel versions that we want to use in this experiment.

## gem5 run scripts

Next, we need to add gem5 run scripts. We will do that in a folder named configs-boot-tests.
Get the run script named run_exit.py from [here](https://github.com/darchr/gem5art/blob/master/docs/configs-boot-tests/run_exit.py), and other system configuration files from
[here](https://github.com/darchr/gem5art/blob/master/docs/configs-boot-tests/system/).
The run script (run_exit.py) takes the following arguments:
- kernel: compiled kernel to be used for simulation
- disk: built disk image to be used for simulation
- cpu_type: gem5 cpu model (KVM, atomic, timing or O3)
- mem_sys: gem5 memory system (classic or ruby)
- num_cpus: number of parallel cpus to be simulated
- boot_type: linux kernel boot type (with init or systemd)


## Database and Celery Server

If not already running/created, you can create a database using:

```sh
`docker run -p 27017:27017 -v <absolute path to the created directory>:/data/db --name mongo-<some tag> -d mongo`
```
in a newly created directory and run celery server using:

```sh
celery -E -A gem5art.tasks.celery worker --autoscale=[number of workers],0
```


## Creating a launch script
Finally, we will create a launch script with the name launch_boot_tests.py, which will be responsible for registering the artifacts to be used and then launching gem5 jobs.

The first thing to do in the launch script is to import required modules and classes:

```python
import os
import sys
from uuid import UUID

from gem5art.artifact.artifact import Artifact
from gem5art.run import gem5Run
from gem5art.tasks.tasks import run_gem5_instance
```

Next, we will register artifacts. For example, to register packer artifact we will add the following lines:

```python
packer = Artifact.registerArtifact(
    command = '''wget https://releases.hashicorp.com/packer/1.4.3/packer_1.4.3_linux_amd64.zip;
    unzip packer_1.4.3_linux_amd64.zip;
    ''',
    typ = 'binary',
    name = 'packer',
    path =  'disk-image/packer',
    cwd = 'disk-image',
    documentation = 'Program to build disk images. Downloaded sometime in August from hashicorp.'
)
```

For our boot-tests repo,

```python
experiments_repo = Artifact.registerArtifact(
    command = 'git clone https://github.com/darchr/fs-x86-test',
    typ = 'git repo',
    name = 'Boot_test',
    path =  './',
    cwd = '../',
    documentation = 'main experiments repo to run full system tests with gem5'
)
```

Note that the name of the artifact (returned by the registerArtifact method) is totally up to the user as well as
all most of the other attributes of these artifacts.

For all other artifacts, add following lines in launch_boot_tests.py:

```python
gem5_repo = Artifact.registerArtifact(
    command = 'git clone https://github.com/darchr/gem5',
    typ = 'git repo',
    name = 'gem5',
    path =  'gem5/',
    cwd = './',
    documentation = 'git repo with gem5 master branch on Sep 23rd'
)

m5_binary = Artifact.registerArtifact(
    command = 'make -f Makefile.x86',
    typ = 'binary',
    name = 'm5',
    path =  'gem5/util/m5/m5',
    cwd = 'gem5/util/m5',
    inputs = [gem5_repo,],
    documentation = 'm5 utility'
)

disk_image = Artifact.registerArtifact(
    command = 'packer build template.json',
    typ = 'disk image',
    name = 'boot-disk',
    cwd = 'disk-image',
    path = 'disk-image/boot-exit/boot-exit-image/boot-exit',
    inputs = [packer, experiments_repo, m5_binary,],
    documentation = 'Ubuntu with m5 binary installed and root auto login'
)

gem5_binary = Artifact.registerArtifact(
    command = 'scons build/X86/gem5.opt',
    typ = 'binary',
    name = 'gem5',
    cwd = 'gem5/',
    path =  'gem5/build/X86/gem5.opt',
    inputs = [gem5_repo,],
    documentation = 'default gem5 x86'
)

linux_repo = Artifact.registerArtifact(
    command = '''git clone https://github.com/torvalds/linux.git;
    mv linux linux-stable''',
    typ = 'git repo',
    name = 'linux-stable',
    path =  'linux-stable/',
    cwd = './',
    documentation = 'linux kernel source code repo from Sep 23rd'
)

linuxes = ['5.2.3', '4.14.134', '4.9.186', '4.4.186']
linux_binaries = {
    version: Artifact.registerArtifact(
                name = f'vmlinux-{version}',
                typ = 'kernel',
                path = f'linux-stable/vmlinux-{version}',
                cwd = 'linux-stable/',
                command = f'''git checkout v{version};
                cp ../linux-configs/config.{version} .config;
                make -j8;
                cp vmlinux vmlinux-{version};
                '''.format(v='5.2.3'),
                inputs = [experiments_repo, linux_repo,],
                documentation = f"Kernel binary for {version} with simple "
                                 "config file",
            )
    for version in linuxes
}
```

Once, all the artifacts are registered the next step is to launch all gem5 jobs. To do that, add the following lines in your script:

```ptyhon
if __name__ == "__main__":
    boot_types = ['init', 'systemd']
    num_cpus = ['1', '2', '4', '8']
    cpu_types = ['kvm', 'atomic', 'simple', 'o3']
    mem_types = ['classic', 'ruby']

    for linux in linuxes:
        for boot_type in boot_types:
            for cpu in cpu_types:
                for num_cpu in num_cpus:
                    for mem in mem_types:
                        run = gem5Run.createFSRun(
                            'gem5/build/X86/gem5.opt',
                            'configs-boot-tests/run_exit.py',
                            gem5_binary, gem5_repo, experiments_repo,
                            os.path.join('linux-stable', 'vmlinux'+'-'+linux),
                            'disk-image/boot-exit/boot-exit-image/boot-exit',
                            linux_binaries[linux], disk_image,
                            cpu, mem, num_cpu, boot_type
                            )
                        run_gem5_instance.apply_async((run,))
```
The above lines are responsible for looping through all possible combinations of variables involved in this experiment.
For each combination, a gem5Run object is created and eventually passed to run_gem5_instance to be
executed asynchronously using Celery.

The complete launch script is available [here:](https://github.com/darchr/gem5art/blob/master/docs/launch_boot_tests.py).
Finally, make sure you are in python virtual env and then run the script:

```python
python launch_boot_tests.py
```
