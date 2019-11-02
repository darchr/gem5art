# Tutorial 2: Run NAS Parallel Benchmarks with gem5

## Introduction
In this tutorial, we will use gem5art to create a disk image for NAS parallel benchmarks ([NPB](https://www.nas.nasa.gov/)) and then run these benchmarks using gem5. NPB consist of 5 kernels and 3 pseudo applications. Following are their details:

Kernels:
- **IS:** Integer Sort, random memory access
- **EP:** Embarrassingly Parallel
- **CG:** Conjugate Gradient, irregular memory access and communication
- **MG:** Multi-Grid on a sequence of meshes, long- and short-distance communication, memory intensive
- **FT:** discrete 3D fast Fourier Transform, all-to-all communication

Pseudo Applications:
- **BT:** Block Tri-diagonal solver
- **SP:** Scalar Penta-diagonal solver
- **LU:** Lower-Upper Gauss-Seidel solver

There are different classes (A,B,C,D,E and F) of the workloads based on the data size that is used with the benchmarks. Detailed discussion of the data sizes is available [here](https://www.nas.nasa.gov/publications/npb_problem_sizes.html).

This tutorial follows the following directory structure:

- configs-npb-tests: the base gem5 configuration to be used to run full-system simulations
- disk-image: contains packer script and template files used to build a disk image. The built disk image will be stored in the
  same folder
- gem5: gem5 source code. This points to darchr/gem5 repo
- linux-configs: different linux kernel configurations
- linux-stable: linux kernel source code used for full-system experiments
- results: directory to store the results of the experiments (generated once gem5 jobs are executed)
- launch_npb_tests.py:  gem5 jobs launch script (creates all of the needed artifacts as well)


## Setting up the environment

gem5art relies on Python 3, so we suggest creating a virtual environment before using gem5art.

```sh
virtualenv -p python3 venv
source venv/bin/activate
```

Create the main directory named npb-tests and turn it into a git repo:

```sh
mkdir npb-tests
cd npb-tests
git init
git remote add origin https://your-remote-add/npb-tests.git
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
Through the use of npb-tests git repo, we will try to keep track of changes in those files which are not included in any git repo otherwise.
npb-tests will also serve as the directory from where we will run everything.

gem5art can be installed (if not already) using pip:

```sh
pip install gem5art-artifact gem5art-run gem5art-tasks
```

To install gem5art from a local source, first clone the gem5art repo in npb_tests and then do:

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
Add a folder named shared for config files which will be shared among all disk images (and will be kept to their defaults) and one folder named npb which will contain files configured for NPB disk image. Add [preseed.cfg](https://github.com/darchr/gem5art/blob/master/docs/disks/shared/preseed.cfg) and [serial-getty@.service](https://github.com/darchr/gem5art/blob/master/docs/disks/shared/serial-getty@.service) in shared/.

In npb/ we will add the benchmark source first, which will eventually be transferred to the disk image through our npb.json file.

```sh
wget https://www.nas.nasa.gov/assets/npb/NPB3.3.1.tar.gz
tar xvzf  NPB3.3.1.tar.gz
```

Next, we will add few other files in npb/ which will be used for compilation of NPB inside the disk image and eventually running of these benchmarks with gem5.
These files will be moved from host to the disk image using npb.json file as we will soon seee.

First, create a file npb-install.sh, which will install NPB on the disk image:

```sh
# install build-essential (gcc and g++ included) and gfortran

#Compile NPB

echo "12345" | sudo apt-get install build-essential gfortran

cp /home/gem5/NPB3.3-OMP/config/suite.def_C /home/gem5/NPB3.3-OMP/config/suite.def

cd /home/gem5/NPB3.3-OMP/
make suite
```

We are specifically compiling OMP version of class C NPB workloads. To configure the benchmark build process, we will use modified make.def and suite.def files. Look [here]() in order to understand the build process of NAS parallel benchmarks.

Create suite.def_C in npb/ and add:

```
# config/suite.def
# This file is used to build several benchmarks with a single command.
# Typing "make suite" in the main directory will build all the benchmarks
# specified in this file.
# Each line of this file contains a benchmark name and the class.
# The name is one of "cg", "is", "dc", "ep", mg", "ft", "sp",
#  "bt", "lu", and "ua".
# The class is one of "S", "W", "A" through "E"
# (except that no classes C,D,E for DC and no class E for IS and UA).
# No blank lines.
# The following example builds sample sizes of all benchmarks.
ft      C
mg      C
sp      C
lu      C
bt      C
is      C
ep      C
cg      C
ua      C
```

Next, create make.def in npb/ and add:


```
#---------------------------------------------------------------------------
#
#                SITE- AND/OR PLATFORM-SPECIFIC DEFINITIONS.
#
#---------------------------------------------------------------------------

#---------------------------------------------------------------------------
# Items in this file will need to be changed for each platform.
#---------------------------------------------------------------------------

#---------------------------------------------------------------------------
# Parallel Fortran:
#
# For CG, EP, FT, MG, LU, SP, BT and UA, which are in Fortran, the following
# must be defined:
#
# F77        - Fortran compiler
# FFLAGS     - Fortran compilation arguments
# F_INC      - any -I arguments required for compiling Fortran
# FLINK      - Fortran linker
# FLINKFLAGS - Fortran linker arguments
# F_LIB      - any -L and -l arguments required for linking Fortran
#
# compilations are done with $(F77) $(F_INC) $(FFLAGS) or
#                            $(F77) $(FFLAGS)
# linking is done with       $(FLINK) $(F_LIB) $(FLINKFLAGS)
#---------------------------------------------------------------------------

#---------------------------------------------------------------------------
# This is the fortran compiler used for Fortran programs
#---------------------------------------------------------------------------
F77 = f77
# This links fortran programs; usually the same as ${F77}
FLINK	= $(F77)

#---------------------------------------------------------------------------
# These macros are passed to the linker
#---------------------------------------------------------------------------
F_LIB  =

#---------------------------------------------------------------------------
# These macros are passed to the compiler
#---------------------------------------------------------------------------
F_INC =

#---------------------------------------------------------------------------
# Global *compile time* flags for Fortran programs
#---------------------------------------------------------------------------
FFLAGS	= -O3 -fopenmp

#---------------------------------------------------------------------------
# Global *link time* flags. Flags for increasing maximum executable
# size usually go here.
#---------------------------------------------------------------------------
FLINKFLAGS = -O3 -fopenmp


#---------------------------------------------------------------------------
# Parallel C:
#
# For IS and DC, which are in C, the following must be defined:
#
# CC         - C compiler
# CFLAGS     - C compilation arguments
# C_INC      - any -I arguments required for compiling C
# CLINK      - C linker
# CLINKFLAGS - C linker flags
# C_LIB      - any -L and -l arguments required for linking C
#
# compilations are done with $(CC) $(C_INC) $(CFLAGS) or
#                            $(CC) $(CFLAGS)
# linking is done with       $(CLINK) $(C_LIB) $(CLINKFLAGS)
#---------------------------------------------------------------------------

#---------------------------------------------------------------------------
# This is the C compiler used for C programs
#---------------------------------------------------------------------------
CC = cc
# This links C programs; usually the same as ${CC}
CLINK	= $(CC)

#---------------------------------------------------------------------------
# These macros are passed to the linker
#---------------------------------------------------------------------------
C_LIB  = -lm

#---------------------------------------------------------------------------
# These macros are passed to the compiler
#---------------------------------------------------------------------------
C_INC =

#---------------------------------------------------------------------------
# Global *compile time* flags for C programs
# DC inspects the following flags (preceded by "-D"):
#
# IN_CORE - computes all views and checksums in main memory (if there is
# enough memory)
#
# VIEW_FILE_OUTPUT - forces DC to write the generated views to disk
#
# OPTIMIZATION - turns on some nonstandard DC optimizations
#
# _FILE_OFFSET_BITS=64
# _LARGEFILE64_SOURCE - are standard compiler flags which allow to work with
# files larger than 2GB.
#---------------------------------------------------------------------------
CFLAGS	= -O3 -fopenmp

#---------------------------------------------------------------------------
# Global *link time* flags. Flags for increasing maximum executable
# size usually go here.
#---------------------------------------------------------------------------
CLINKFLAGS = -O3 -fopenmp


#---------------------------------------------------------------------------
# Utilities C:
#
# This is the C compiler used to compile C utilities.  Flags required by
# this compiler go here also; typically there are few flags required; hence
# there are no separate macros provided for such flags.
#---------------------------------------------------------------------------
UCC	= cc


#---------------------------------------------------------------------------
# Destination of executables, relative to subdirs of the main directory. .
#---------------------------------------------------------------------------
BINDIR	= ../bin


#---------------------------------------------------------------------------
# The variable RAND controls which random number generator
# is used. It is described in detail in README.install.
# Use "randi8" unless there is a reason to use another one.
# Other allowed values are "randi8_safe", "randdp" and "randdpvec"
#---------------------------------------------------------------------------
RAND   = randi8
# The following is highly reliable but may be slow:
# RAND   = randdp


#---------------------------------------------------------------------------
# The variable WTIME is the name of the wtime source code module in the
# common directory.
# For most machines,       use wtime.c
# For SGI power challenge: use wtime_sgi64.c
#---------------------------------------------------------------------------
WTIME  = wtime.c


#---------------------------------------------------------------------------
# Enable if either Cray (not Cray-X1) or IBM:
# (no such flag for most machines: see common/wtime.h)
# This is used by the C compiler to pass the machine name to common/wtime.h,
# where the C/Fortran binding interface format is determined
#---------------------------------------------------------------------------
# MACHINE	=	-DCRAY
# MACHINE	=	-DIBM
```

In npb/, create a file post-installation.sh and add following lines to it:

```sh
#!/bin/bash
echo 'Post Installation Started'

mv /home/gem5/serial-getty@.service /lib/systemd/system/

mv /home/gem5/m5 /sbin
ln -s /sbin/m5 /sbin/gem5

# copy and run outside (host) script after booting
cat /home/gem5/runscript.sh >> /root/.bashrc

echo 'Post Installation Done'
```

This post-installation.sh script (which is a script to run after Ubuntu is installed on the disk image) installs m5 and copies the contents of runscript.sh to .bashrc. Therefore, we need
to add those things in runscript.sh which we want to execute as soon as the sytem boots up. Create runscript.sh in npb/ and add following
lines to it:

```sh
#!/bin/sh

m5 readfile > script.sh
if [ -s script.sh ]; then
    # if the file is not empty, execute it
    chmod +x script.shm5 re
    ./script.sh
    m5 exit
fi
# otherwise, drop to the terminal
```
runscript.sh uses m5 readfile to read the contents of a script which is how gem5 passes scripts to the simulated system from the host system.
The passed script will then be executed and will be responsible for running benchmark/s which we will look into more later.

Finally, create npb.json and add following contents:

```json
{
    "builders":
    [
        {
            "type": "qemu",
            "format": "raw",
            "accelerator": "kvm",
            "boot_command":
            [
                "{{ user `boot_command_prefix` }}",
                "debian-installer={{ user `locale` }} auto locale={{ user `locale` }} kbd-chooser/method=us ",
                "file=/floppy/{{ user `preseed` }} ",
                "fb=false debconf/frontend=noninteractive ",
                "hostname={{ user `hostname` }} ",
                "/install/vmlinuz noapic ",
                "initrd=/install/initrd.gz ",
                "keyboard-configuration/modelcode=SKIP keyboard-configuration/layout=USA ",
                "keyboard-configuration/variant=USA console-setup/ask_detect=false ",
                "passwd/user-fullname={{ user `ssh_fullname` }} ",
                "passwd/user-password={{ user `ssh_password` }} ",
                "passwd/user-password-again={{ user `ssh_password` }} ",
                "passwd/username={{ user `ssh_username` }} ",
                "-- <enter>"
            ],
            "cpus": "{{ user `vm_cpus`}}",
            "disk_size": "{{ user `image_size` }}",
            "floppy_files":
            [
                "shared/{{ user `preseed` }}"
            ],
            "headless": "{{ user `headless` }}",
            "http_directory": "shared/",
            "iso_checksum": "{{ user `iso_checksum` }}",
            "iso_checksum_type": "{{ user `iso_checksum_type` }}",
            "iso_urls": [ "{{ user `iso_url` }}" ],
            "memory": "{{ user `vm_memory`}}",
            "output_directory": "npb/{{ user `image_name` }}-image",
            "qemuargs":
            [
                [ "-cpu", "host" ],
                [ "-display", "none" ]
            ],
            "qemu_binary":"/usr/bin/qemu-system-x86_64",
            "shutdown_command": "echo '{{ user `ssh_password` }}'|sudo -S shutdown -P now",
            "ssh_password": "{{ user `ssh_password` }}",
            "ssh_username": "{{ user `ssh_username` }}",
            "ssh_wait_timeout": "60m",
            "vm_name": "{{ user `image_name` }}"
        }
    ],
    "provisioners":
    [
        {
            "type": "file",
            "source": "../gem5/util/m5/m5",
            "destination": "/home/gem5/"
        },
        {
            "type": "file",
            "source": "shared/serial-getty@.service",
            "destination": "/home/gem5/"
        },
        {
            "type": "file",
            "source": "npb/runscript.sh",
            "destination": "/home/gem5/"
        },
        {
            "type": "file",
            "source": "npb/NPB3.3.1/NPB3.3-OMP",
            "destination": "/home/gem5/"
        },
        {
            "type": "file",
            "source": "npb/make.def",
            "destination": "/home/gem5/NPB3.3-OMP/config/make.def"
        },
        {
            "type": "file",
            "source": "npb/suite.def_C",
            "destination": "/home/gem5/NPB3.3-OMP/config/suite.def_C"
        },
        {
            "type": "shell",
            "execute_command": "echo '{{ user `ssh_password` }}' | {{.Vars}} sudo -E -S bash '{{.Path}}'",
            "scripts":
            [
                "npb/post-installation.sh",
                "npb/npb-install.sh"
            ]
        }
    ],
    "variables":
    {
        "boot_command_prefix": "<enter><wait><f6><esc><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs><bs>",
        "desktop": "false",
        "image_size": "12000",
        "headless": "true",
        "iso_checksum": "34416ff83179728d54583bf3f18d42d2",
        "iso_checksum_type": "md5",
        "iso_name": "ubuntu-18.04.2-server-amd64.iso",
        "iso_url": "http://old-releases.ubuntu.com/releases/18.04.2/ubuntu-18.04.2-server-amd64.iso",
        "locale": "en_US",
        "preseed" : "preseed.cfg",
        "hostname": "gem5",
        "ssh_fullname": "gem5",
        "ssh_password": "12345",
        "ssh_username": "gem5",
        "vm_cpus": "16",
        "vm_memory": "8192",
        "image_name": "npb"
  }

}
```

npb.json is our primary .json configuration file. The provisioners and variables section of this file configure the files that need to be transferred to the disk and other things like disk image's name.

Next, download packer (if not already downloaded) in the disk-image folder:

```
cd disk-image/
wget https://releases.hashicorp.com/packer/1.4.3/packer_1.4.3_linux_amd64.zip
unzip packer_1.4.3_linux_amd64.zip
```
Now, to build the disk image, inside disk-image folder, run:

```
./packer validate npb/npb.json

./packer build npb/npb.json
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

```python
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