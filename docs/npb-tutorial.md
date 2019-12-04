# Tutorial: Run NAS Parallel Benchmarks with gem5

## Introduction
In this tutorial, we will use gem5art to create a disk image for NAS parallel benchmarks ([NPB](https://www.nas.nasa.gov/)) and then run these benchmarks using gem5. NPB belongs to the category of high performance computing (HPC) workloads and consist of 5 kernels and 3 pseudo applications.
Following are their details:

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

- configs-npb-tests: gem5 run and configuration scripts to run NPB
- disk-image: contains packer script and template files used to build a disk image.
The built disk image will be stored in the same folder
- gem5: gem5 [source code](https://gem5.googlesource.com/public/gem5) and the compiled binary
- linux-stable: linux kernel [source code](https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git)  used for full-system experiments
- config.4.19.83: linux kernel config file used for its compilation
- results: directory to store the results of the experiments (generated once gem5 jobs are executed)
- launch_npb_tests.py:  gem5 jobs launch script (creates all of the needed artifacts as well)


## Setting up the environment
First, we need to create the main directory named npb-tests (from where we will run everything) and turn it into a git repository.
Through the use of npb-tests git repo, we will try to keep track of changes in those files which are not included in any git repo otherwise.
An example of such files is gem5 run and config scripts (config-npb-tests).
We want to make sure that we can keep record of any changes in these scripts, so that a particular run of NPB benchmarks can be associated with a particular snapshot of these files.
We also need to add a git remote to this repo pointing to a remote location where we want this repo to be hosted.


```sh
mkdir npb-tests
cd npb-tests
git init
git remote add origin https://your-remote-add/npb-tests.git
```

We also need to add a .gitignore file in our git repo, to avoid tracking those files which are not important or will be tracked through other git repos:

```sh
*.pyc
m5out
.vscode
results
venv
disk-image/packer
disk-image/packer_1.4.3_linux_amd64.zip
disk-image/npb/npb-image/npb
disk-image/npb/NPB3.3.1
disk-image/packer_cache
gem5
linux-stable/
```

gem5art relies on Python 3, so we suggest creating a virtual environment before using gem5art.

```sh
virtualenv -p python3 venv
source venv/bin/activate
```

gem5art can be installed (if not already) using pip:

```sh
pip install gem5art-artifact gem5art-run gem5art-tasks
```

## Building gem5

Next clone gem5 from googlesource:

```sh
git clone https://gem5.googlesource.com/public/gem5
```

Before building gem5, we need to apply some changes to the source.
These changes are needed to run gem5 in KVM mode on Intel platforms and also to run some gem5 magic instructions in KVM mode.
We will get these changes from darchr/gem5 (GitHub).
Run the following apply changes and build gem5:

```sh
cd gem5
git remote add darchr https://github.com/darchr/gem5
git fetch darchr
git cherry-pick 6450aaa7ca9e3040fb9eecf69c51a01884ac370c
git cherry-pick 3403665994b55f664f4edfc9074650aaa7ddcd2c
scons build/X86/gem5.opt -j8
```

Also make sure to build the m5 utility which will be moved to the disk image eventually.
m5 utility allows to trigger simulation tasks from inside the simulated system.
For example, it can be used dump simuation statistics when the simulated system triggers to do so.
We will need m5 mainly to exit the simulation when the simulated system will be done with the execution of a particular NPB benchmark.

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
cd disk-image/npb
git clone https://github.com/darchr/npb-hooks.git
git checkout gem5art-npb-tutorial
```

This source of NPB has ROI (region of interest) annotations for each benchmark which will be used by gem5 to
separate out simulation statistics of the important parts of a program from the rest of the program.
Basically, gem5 magic instructions are used before and after the ROI to exit the guest and transfer control to gem5 run script which can then do things like dumping or reseting stats or switching to cpu of interest.

Next, we will add few other files in npb/ which will be used for compilation of NPB inside the disk image and eventually running of these benchmarks with gem5.
These files will be moved from host to the disk image using npb.json file as we will soon seee.

First, create a file npb-install.sh, which will be executed inside the disk image (once it is built) and will install NPB on the disk image:

```sh
# install build-essential (gcc and g++ included) and gfortran

#Compile NPB

echo "12345" | sudo apt-get install build-essential gfortran

cd /home/gem5/NPB3.3-OMP/

mkdir bin

make suite HOOKS=1
```

We are specifically compiling OpenMP (OMP) version of class A, B, C and D of NPB workloads.

To configure the benchmark build process, the source of NPB we are using relies on modified make.def and suite.def files (build system files). Look [here](https://github.com/darchr/npb-hooks/blob/master/NPB3.3.1/NPB3.3-OMP/README.install) in order to understand the build process of NAS parallel benchmarks.
'suite.def' file is used to determine which workloads (and of which class) do we want to compile when we run 'make suite' command (as in the above script).
You can look at the modified suite.def file [here](https://github.com/darchr/npb-hooks/blob/gem5art-npb-tutorial/NPB3.3.1/NPB3.3-OMP/config/suite.def).

The make.def file we are using add OMP flags to the compiler flags to compile OMP version of the benchmarks. We also add another flag '-DM5OP_ADDR=0xFFFF0000' to the compiler flags, which makes sure that the gem5 magic instructions added to the benchmarks will also work in KVM mode.
You can look at the complete file [here](https://github.com/darchr/npb-hooks/blob/gem5art-npb-tutorial/NPB3.3.1/NPB3.3-OMP/config/make.def).

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

This post-installation.sh script (which is a script to run after Ubuntu is installed on the disk image) installs m5 and copies the contents of runscript.sh to .bashrc.
Therefore, we need to add those things in runscript.sh which we want to execute as soon as the sytem boots up.
Create runscript.sh in npb/ and add following lines to it:

```sh
#!/bin/sh

m5 readfile > script.sh
if [ -s script.sh ]; then
    # if the file is not empty, execute it
    chmod +x script.sh
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
            "source": "npb/npb-hooks/NPB3.3.1/NPB3.3-OMP",
            "destination": "/home/gem5/"
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
Now, to build the disk image inside the disk-image folder, run:

```
./packer validate npb/npb.json

./packer build npb/npb.json
```

## Compiling the linux kernel

In this tutorial, we will use the latest LTS (long term support) release of linux kernel v4.19.83 with gem5 to run NAS parallel benchmarks.
First, get the linux kernel config file from [here](https://github.com/darchr/gem5art/blob/master/docs/linux-configs/config.4.19.83), and place it in npb-tests folder.
Then, we will get the linux source of version 4.19.83:

```
git clone --branch v4.19.83 --depth 1 https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git
mv linux linux-stable
cd linux-stable
```
Compile the linux kernel from its source (using already downloaded config file config.4.19.83):

```
cp ../config.4.19.83 .config
make -j8
cp vmlinux vmlinux-4.19.83
```

## gem5 run scripts

Next, we need to add gem5 run scripts. We will do that in a folder named configs-npb-tests.
Get the run script named run_npb.py from [here](https://github.com/darchr/gem5art/blob/master/docs/configs-npb-tests/run_npb.py), and other system configuration files from
[here](https://github.com/darchr/gem5art/blob/master/docs/configs-npb-tests/system/).
The run script (run_npb.py) takes the following arguments:
- kernel: compiled kernel to be used for simulation
- disk: built disk image to be used for simulation
- cpu: the cpu model to use (e.g. kvm or atomic)
- benchmark: NPB workload to run (e.g. is.C.x, ep.C.x, bt.C.x)
- num_cpus: number of parallel cpus to be simulated

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
Finally, we will create a launch script with the name launch_npb_tests.py, which will be responsible for registering the artifacts to be used and then launching gem5 jobs.

The first thing to do in the launch script is to import required modules and classes:

```python
import os
import sys
from uuid import UUID

from gem5art.artifact import Artifact
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

For our npb-tests repo,

```python
experiments_repo = Artifact.registerArtifact(
    command = 'git clone https://your-remote-add/npb-tests.git',
    typ = 'git repo',
    name = 'npb-tests',
    path =  './',
    cwd = '../',
    documentation = 'main repo to run npb with gem5'
)
```

Note that the name of the artifact (returned by the registerArtifact method) is totally up to the user as well as most of the other attributes of these artifacts.

For all other artifacts, add following lines in launch_npb_tests.py:

```python
gem5_repo = Artifact.registerArtifact(
    command = '''
        git clone https://gem5.googlesource.com/public/gem5;
        cd gem5;
        git remote add darchr https://github.com/darchr/gem5;
        git fetch darchr;
        git cherry-pick 6450aaa7ca9e3040fb9eecf69c51a01884ac370c;
        git cherry-pick 3403665994b55f664f4edfc9074650aaa7ddcd2c;
    ''',
    typ = 'git repo',
    name = 'gem5',
    path =  'gem5/',
    cwd = './',
    documentation = 'cloned gem5 master branch from googlesource (Nov 18, 2019) and cherry-picked 2 commits from darchr/gem5'
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
    command = 'packer build npb.json',
    typ = 'disk image',
    name = 'npb',
    cwd = 'disk-image/npb',
    path = 'disk-image/npb/npb-image/npb',
    inputs = [packer, experiments_repo, m5_binary,],
    documentation = 'Ubuntu with m5 binary and NPB (with ROI annotations: darchr/npb-hooks/gem5art-npb-tutorial) installed.'
)

gem5_binary = Artifact.registerArtifact(
    command = 'scons build/X86/gem5.opt',
    typ = 'gem5 binary',
    name = 'gem5',
    cwd = 'gem5/',
    path =  'gem5/build/X86/gem5.opt',
    inputs = [gem5_repo,],
    documentation = 'default gem5 x86'
)

linux_repo = Artifact.registerArtifact(
    command = '''git clone --branch v4.19.83 --depth 1 https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git;
    mv linux linux-stable''',
    typ = 'git repo',
    name = 'linux-stable',
    path =  'linux-stable/',
    cwd = './',
    documentation = 'linux kernel source code repo'
)

linux_binary = Artifact.registerArtifact(
    name = 'vmlinux-4.19.83',
    typ = 'kernel',
    path = 'linux-stable/vmlinux-4.19.83',
    cwd = 'linux-stable/',
    command = '''
    cp ../config.4.19.83 .config;
    make -j8;
    cp vmlinux vmlinux-4.19.83;
    ''',
    inputs = [experiments_repo, linux_repo,],
    documentation = "kernel binary for v4.19.83",
)
```

Once, all of the artifacts are registered, the next step is to launch all gem5 jobs. To do that, add the following lines in your script (complete launch script is available [here](https://github.com/darchr/gem5art/blob/master/docs/launch_npb_tests.py)):

```python
if __name__ == "__main__":
    num_cpus = ['1', '4']
    benchmarks = ['is.x', 'ep.x', 'cg.x', 'mg.x','ft.x', 'bt.x', 'sp.x', 'lu.x']

    classes = ['A', 'B', 'C', 'D']
    cpus = ['kvm', 'atomic']

for cpu in cpus:
    for num_cpu in num_cpus:
        for clas in classes:
            for bm in benchmarks:
                if cpu == 'atomic' and clas != 'A':
                    continue
                run = gem5Run.createFSRun(
                    'gem5/build/X86/gem5.opt',
                    'configs-npb-tests/run_npb.py',
                    f'''results/run_npb/{bm}/{clas}/{cpu}/{num_cpu}''',
                    gem5_binary, gem5_repo, experiments_repo,
                    'linux-stable/vmlinux-4.19.83',
                    'disk-image/npb/npb-image/npb',
                    linux_binary, disk_image,
                    cpu, bm.replace('.x', f'.{clas}.x'), num_cpu
                    )
                run_gem5_instance.apply_async((run,))
```
The above lines are responsible for looping through all possible combinations of variables involved in this experiment.
For each combination, a gem5Run object is created and eventually passed to run_gem5_instance to be
executed asynchronously using Celery.
We are running class A,B,C and D of NPB with KVM cpu and only class A with atomic cpu.

The complete launch script is available [here:](https://github.com/darchr/gem5art/blob/master/docs/launch_npb_tests.py).
Finally, make sure you are in python virtual env and then run the script:

```python
python launch_npb_tests.py
```

Once you run the launch script, the declared artifacts will be registered by gem5art and stored in the database.
Celery will run as many jobs in parallel as allowed by the user (at the time of starting the server).
As soon as a gem5 job finishes, a compressed version of the results will be stored in the database as well.
User can also query the database using the methods discussed in the [Artifacts](artifacts.md) section previously.

