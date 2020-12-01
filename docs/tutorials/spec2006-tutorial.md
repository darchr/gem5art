---
Authors:
  - Hoa Nguyen
---

# Tutorial: Run SPEC CPU 2006 Benchmarks in Full System Mode with gem5art

## Introduction
In this tutorial, we will demonstrate how to utilize gem5art to run SPEC CPU 2006 benchmarks in gem5 full system mode.
The full example with all of the gem5art tutorials can be found [here](https://github.com/darchr/gem5art-experiments).
The scripts in this tutorial work with gem5art-* v1.1.0 and gem5 20.1.0.2 stable.

### SPEC CPU 2006 Benchmarks
**Important:** The usage of this tutorial is just for the purpose of demonstration.
Those benchmarks [have been retired](https://www.spec.org/cpu2006/) [1].
More details about those benchmarks are [here](https://dl.acm.org/citation.cfm?id=1186737) [2].
The Appendix II section of this tutorial shows how to use the SPEC 2006 scripts to run SPEC 2017 experiments.

Examples of the usage of SPEC CPU 2006 benchmark in the literature are [here](https://ieeexplore.ieee.org/abstract/document/4378787) [3] and in the book [4].
Another example of the usage of SPEC CPU benchmarks is [here](https://cacm.acm.org/magazines/2019/2/234352-a-new-golden-age-for-computer-architecture/fulltext) [5].

### gem5 Full System Mode
Different from the gem5 SE (syscall emulation) mode, the full system mode uses an actual Linux kernel instead of emulating responsibilities of a typical modern OS, such as managing page tables, taking care of syscalls.
Therefore, the results would be more realistic when using gem5 FS, especially when the interactions between the workload and the OS are significant parts of the simulation.


In order to run gem5 in the full system mode, gem5 requires a built Linux kernel, which is configurable.
gem5 does not support all configurations in Linux, including the default Linux kernel configuration.
To accomondate this, we will provide Linux configurations that are to known to work with gem5.
(Please prefer to the [gem5's benchmark status page](https://www.gem5.org/documentation/benchmark_status) for details on what Linux has been tested with gem5.)
Other than that, a gem5 full system configuration is also a requirement to run gem5 full system mode.
In this tutorial, we will provide working Linux configurations, the necessary steps to build a Linux kernel, and a working gem5 full system configuration.

### Outline of the Experiment
We structure the experiment as follows (note that there are many more ways to structure the experiments, and the following is one of them),
* root folder
  * gem5: a folder containing gem5 source code and gem5 binaries.
  * disk-image: a folder containing inputs to produce a disk image containing SPEC CPU 2006 benchmarks.
  * linux-configs: a folder containing different Linux configurations for different Linux kernel versions.
  * gem5-fullsystem-configs: a folder containing a gem5 configuration that is made specifically to run SPEC benchmarks as described in the below figure.
  * results: a folder storing the experiment's results. This folder will have a certain structure in order to make sure that every gem5 run does not overwrite other gem5 runs results.
  * launch_spec2006_experiments.py: a script that does the following,
    * Documenting the experiment using Artifacts objects.
    * Running the experiment in gem5 full system mode.

### An Overview of Host System - gem5 Interactions
![**Figure 1.**]( ../images/spec_tutorial_figure1.png "")
A visual depict of how gem5 interacts with the host system.
gem5 is configured to do the following: booting the Linux kernel, running the benchmark, and copying the SPEC outputs to the host system.
However, since we are interested in getting the stats only for the benchmark, we will configure gem5 to exit after the kernel is booted, and then we reset the stats before running the benchmark.
We use KVM for Linux booting process to quickly boot the system, and after the process is complete, we switch to the desired detailed CPU to run the benchmark.
Similarly, after the benchmark is complete, gem5 exits to host, which allows us to get the stats at that point.
After that, optionally, we switch the CPU back to KVM, which allows us to quickly write the SPEC output files to the host.

**Important:** gem5 will output the stats again when the gem5 run is complete.
Therefore, we will see two stats in one file in stats.txt.
The stats of the benchmark is the the first part of stats.txt, while the second part of the file contains the stats of the benchmark AND the process of writing output files back to the host.
We are only interested in the first part of stats.txt.


## Documenting the Preparing Steps
### Setting up the Experiment Folder
We set up a folder to contain (almost) all materials of the experiment.
We use git to keep track of changes in the folder.

```sh
mkdir spec2006-experiments
cd spec2006-experiments
git init
```

We need add a remote to the repository.

```sh
git remote add origin https://your-remote-add/spec-experiment.git
```

We document the root folder of the experiment in launch_spec2006_experiments.py as follows,

```sh
experiments_repo = Artifact.registerArtifact(
    command = '',
    typ = 'git repo',
    name = 'experiment',
    path =  './',
    cwd = './',
    documentation = 'local repo to run spec 2006 experiments with gem5 full system mode'
)
```

We use .gitignore file to ignore changes of certain files or folders.
In this experiment, we will use this .gitignore file,

```
*.pyc
m5out
.vscode
results
gem5art-env
disk-image/packer
disk-image/spec2006/spec2006-image/spec2006
disk-image/packer_cache
disk-image/spec2006/CPU2006v1.0.1.iso
gem5
linux-4.19.83/
```

Essentially, we will ignore files and folders that we use gem5art to keep track of them, or the presence of those files and folders do not affect the experiment's results.

### Building gem5
In this step, we download the source code and build gem5 v20.1.0.2.

```sh
git clone -b v20.1.0.2 https://gem5.googlesource.com/public/gem5
cd gem5
scons build/X86/gem5.opt -j8
```

We have two artifacts: one is the gem5 source code (the gem5 git repo), and the gem5 binary (`gem5.opt`).
The documentation of this step would be how we get the source code and how we compile the gem5 binary.
In launch_spec2006_experiments.py, we document the step in Artifact objects as follows,

```python
gem5_repo = Artifact.registerArtifact(
    command = '''
        git clone -b v20.1.0.2 https://gem5.googlesource.com/public/gem5
        cd gem5
        scons build/X86/gem5.opt -j8
    ''',
    typ = 'git repo',
    name = 'gem5',
    path =  'gem5/',
    cwd = './',
    documentation = 'cloned gem5 v20.1.0.2'
)


gem5_binary = Artifact.registerArtifact(
    command = 'scons build/X86/gem5.opt -j8',
    typ = 'gem5 binary',
    name = 'gem5-20.1.0.2',
    cwd = 'gem5/',
    path =  'gem5/build/X86/gem5.opt',
    inputs = [gem5_repo,],
    documentation = 'compiled gem5 v20.1.0.2 binary'
)
```

### Building m5
m5 is a binary that facilitates the communication between the host system and the guest system (gem5).
The examples of how m5 is used could be found in the runscripts that we will describe later.
m5 binary will be copied to the disk image, so that the guest could run m5 binary during the experiment.
Therefore, m5 binary should be compiled before we build the disk image.

**Note:** it's important to compile the m5 binary with -DM5_ADDR=0xFFFF0000 as is default in the SConscript.
If you don't compile with -DM5_ADDR and try to run with KVM, you'll get an illegal instruction error.

To compile m5 binary,

```sh
cd gem5/util/m5/
scons build/x86/out/m5
```

In launch_spec2006_experiments.py, we document the step in an Artifact object as follows,

```python
m5_binary = Artifact.registerArtifact(
    command = 'scons build/x86/out/m5',
    typ = 'binary',
    name = 'm5',
    path =  'gem5/util/m5/build/x86/out/m5',
    cwd = 'gem5/util/m5',
    inputs = [gem5_repo,],
    documentation = 'm5 utility'
)
```

### Preparing Scripts to Modify the Disk Image
In this step, we will prepare the scripts that will modify the disk image after the Ubuntu installation process has finished, and before the first time we use the disk image in gem5.
We will keep the related files in the disk-image folder of the experiment.
The files that are made specifically for SPEC 2006 benchmarks will be in `disk-image/spec2006`, and the files that are commonly used accross most benchmarks will be in `disk-image/shared`.

In the root folder of the experiment,

```sh
mkdir disk-image
mkdir disk-image/spec2006
mkdir disk-image/shared
```

The first script is the `runscript.sh` script, which will be appended to the end of `.bashrc` file.
As a result, that script will run when we use the disk image in gem5 after the Linux booting process has finished.
Figure 1 describes how this script interacts with the gem5 config file.
The script could be found [here](https://gem5.googlesource.com/public/gem5-resources/+/a9db8cf1e2ea3c4b3ba84103afcdecfe345494c5/src/spec-2006/disk-image/spec-2006/runscript.sh).

To download the script, in the root folder of the experiment,

```sh
cd disk-image/spec2006
wget -O - https://gem5.googlesource.com/public/gem5-resources/+/a9db8cf1e2ea3c4b3ba84103afcdecfe345494c5/src/spec-2006/disk-image/spec-2006/runscript.sh?format=TEXT | base64 --decode > runscript.sh
```

**Notes:** Due to the code hosting software at gem5.googlesource.com (Gitiles) only allows download the content of a file encrypted in base64, the above command downloads the encrypted content and pipelines it to `base64` utils, which decrypts the content and pipelines it to the `runscript.sh` file.

The second script is `post-installation.sh` script, which will copy the "auto logging in" script to the correct place, and copy the m5 binary to /sbin/ in the disk image.
This script will also append the above script (runscript.sh) to the end of `.bashrc`.
The script could be found [here](https://gem5.googlesource.com/public/gem5-resources/+/a9db8cf1e2ea3c4b3ba84103afcdecfe345494c5/src/spec-2006/disk-image/spec-2006/post-installation.sh).

To download the script, in the root folder of the experiment,

```sh
cd disk-image/spec2006
wget -O - https://gem5.googlesource.com/public/gem5-resources/+/a9db8cf1e2ea3c4b3ba84103afcdecfe345494c5/src/spec-2006/disk-image/spec-2006/post-installation.sh?format=TEXT | base64 --decode > post-installation.sh
```

The third script is the `install-spec2006.sh` script, which installs the dependencies required to compile and run the SPEC 2006 benchmarks, which will be compiled and built in the script.
We figure out that the dependencies include `g++`, `gcc`, and `gfortran`.
So we will get the `build-essential` and `gfortran` packages from Debian (note that "12345" is the default password, this could be modified in the `spec2006.json` file).
The script also modifies the default config script to make the benchmarks work with this set up.
The script could be found [here](https://gem5.googlesource.com/public/gem5-resources/+/a9db8cf1e2ea3c4b3ba84103afcdecfe345494c5/src/spec-2006/disk-image/spec-2006/install-spec2006.sh).

To download the script, in the root folder of the experiment,

```sh
cd disk-image/spec2006
wget -O - https://gem5.googlesource.com/public/gem5-resources/+/a9db8cf1e2ea3c4b3ba84103afcdecfe345494c5/src/spec-2006/disk-image/spec-2006/install-spec2006.sh?format=TEXT | base64 --decode > install-spec2006.sh
```

We also need two other files: the auto logging in script and Ubuntu preseed.
Those files are usually reused by other benchmarks, so we will keep them in disk-image/shared.
The auto logging in script is [here](https://gem5.googlesource.com/public/gem5-resources/+/a9db8cf1e2ea3c4b3ba84103afcdecfe345494c5/src/spec-2006/disk-image/shared/preseed.cfg), and the Ubuntu preseed configuration is [here](https://gem5.googlesource.com/public/gem5-resources/+/a9db8cf1e2ea3c4b3ba84103afcdecfe345494c5/src/spec-2006/disk-image/shared/serial-getty%40.service).

In the root folder of the experiment,

```sh
cd disk-image/shared
wget -O - https://gem5.googlesource.com/public/gem5-resources/+/a9db8cf1e2ea3c4b3ba84103afcdecfe345494c5/src/spec-2006/disk-image/shared/preseed.cfg?format=TEXT | base64 --decode > preseed.cfg
 wget -O - https://gem5.googlesource.com/public/gem5-resources/+/a9db8cf1e2ea3c4b3ba84103afcdecfe345494c5/src/spec-2006/disk-image/shared/serial-getty%40.service?format=TEXT | base64 --decode > serial-getty@.service
```

We don't make Artifact objects for those scripts.
Instead, we let the Artifact repository object of the root folder to keep track of the changes in the above scripts.

### Building the Disk Image
Having prepared necessary scripts to create the disk image, in this step, we will build the disk image using [packer](https://www.packer.io/).

First, we download the packer binary.
The current version of packer as of November 2020 is 1.6.5.

```sh
cd disk-image/
wget https://releases.hashicorp.com/packer/1.6.5/packer_1.6.5_linux_amd64.zip
unzip packer_1.6.5_linux_amd64.zip
rm packer_1.6.5linux_amd64.zip
```

In launch_spec2006_experiments.py, we document how we obtain the binary as follows,

```python
packer = Artifact.registerArtifact(
    command = '''
        wget https://releases.hashicorp.com/packer/1.6.5/packer_1.6.5_linux_amd64.zip;
        unzip packer_1.6.5_linux_amd64.zip;
    ''',
    typ = 'binary',
    name = 'packer',
    path =  'disk-image/packer',
    cwd = 'disk-image',
    documentation = 'Program to build disk images. Downloaded sometime in November from hashicorp.'
)
```

Second, we create a packer script (a json file) that describes how the disk image will be built.
In this step, we assume that we have the SPEC 2006 ISO file in the disk-image/spec2006 folder.
In this script, the ISO file name is CPU2006v1.0.1.iso.
The script is available [here](https://gem5.googlesource.com/public/gem5-resources/+/a9db8cf1e2ea3c4b3ba84103afcdecfe345494c5/src/spec-2006/disk-image/spec-2006/spec-2006.json), and we save the file at `disk-image/spec2006/spec2006.json`.

In the root folder of experiment,

```sh
cd disk-image/spec2006/
wget https://gem5.googlesource.com/public/gem5-resources/+/a9db8cf1e2ea3c4b3ba84103afcdecfe345494c5/src/spec-2006/disk-image/spec-2006/spec-2006.json?format=TEXT | base64 --decode > spec-2006.json
```

To build the disk image,

```sh
cd disk-image/
./packer validate spec2006/spec2006.json # validate the script, including checking the input files
./packer build spec2006/spec2006.json
```

The process should take about than an hour to complete on a fairly recent machine with a cable internet speed.
The disk image will be in disk-image/spec2006/spec2006-image/spec2006.

**Note:**: Packer will output a VNC port that could be used to inspect the building process.
Ubuntu has a built-in VNC viewer, namely Remmina.

**Note:**: [More about using packer and building disk images](../main-doc/disks.md).

Now, in launch_spec2006_experiments.py, we make an Artifact object of the disk image.

```python
disk_image = Artifact.registerArtifact(
    command = './packer build spec2006/spec2006.json',
    typ = 'disk image',
    name = 'spec2006',
    cwd = 'disk-image/',
    path = 'disk-image/spec2006/spec2006-image/spec2006',
    inputs = [packer, experiments_repo, m5_binary,],
    documentation = 'Ubuntu Server with SPEC 2006 installed, m5 binary installed and root auto login'
)
```

### Compiling Linux Kernel
In this step, we will download Linux kernel source code and compile the Linux kernel.
The file of interest in this step is the vmlinux file.

First, we download the Linux kernel source code.
Version 4.19.83 has been tested with gem5 as discussed [in the other tutorial](boot-tutorial.md).
We suggest using config files that have been tested with gem5.
The following command will shallow clone the linux stable repository as well as checking out the tag v4.19.83, which contains the code for linux kernel version 4.19.83.
The git command also works well for other version numbers.

In the root of the experiment folder,

```sh
git clone --branch v4.19.83 --depth 1 https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/
mv linux linux-4.19.83
```

Now, in launch_spec2006_experiments.py, we make an Artifact object of the Linux stable git repo.

```python
linux_repo = Artifact.registerArtifact(
    command = '''
    	git clone git clone --branch v4.19.83 --depth 1 https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/;
    	mv linux linux-4.19.83
    ''',
    typ = 'git repo',
    name = 'linux-4.19.83',
    path =  'linux-4.19.83',
    cwd = './',
    documentation = 'Linux kernel 4.19 source code repo obtained in November 2020'
)
```

Next, we compile the Linux kernel.
We will make a folder named linux-configs containing all working linux configs.
Working Linux configs and documentations for generating a Linux config are discussed here [here](boot-tutorial.md).

In the root folder of the experiment,

```sh
mkdir linux-configs
```

To download the linux-4.19.83 configs,

```sh
cd linux-configs
wget -O - https://gem5.googlesource.com/public/gem5-resources/+/a9db8cf1e2ea3c4b3ba84103afcdecfe345494c5/src/linux-kernel/linux-configs/config.4.19.83?format=TEXT | base64 --decode > config.4.19.83
```

The following commands will copy the linux config and compile the linux kernel.
In the root folder of the experiment,

```sh
cp linux-configs/config.4.19.83 linux-4.19.83/.config
cd linux-4.19.83
make -j8
cp vmlinux vmlinux-4.19.83
```

Now, in launch_spec2006_experiments.py, we make an Artifact object of the Linux kernel binary.

```python
linux_binary = Artifact.registerArtifact(
    name = 'vmlinux-4.19.83',
    typ = 'kernel',
    path = 'linux-4.19.83/vmlinux-4.19.83',
    cwd = './',
    command = '''
        cp linux-configs/config.4.19.83 linux-4.19.83/.config
        cd linux-4.19.83
        make -j8
        cp vmlinux vmlinux-4.19.83
    ''',
    inputs = [experiments_repo, linux_repo,],
    documentation = "kernel binary for v4.19.83",
)
```

### The gem5 Run Script/gem5 Configuration
In this step, we take a look at the final missing piece: the gem5 run script.
The script is where we specify the simulated system.
We offer example scripts in the [spec-2006/configs folder](https://gem5.googlesource.com/public/gem5-resources/+/a9db8cf1e2ea3c4b3ba84103afcdecfe345494c5/src/spec-2006/configs/).

First, we create a folder named gem5-configs containing all gem5 configs.
Since gem5art requires a git repo for the run scripts, we will make a local git repo for the run scripts.

In the root folder of the experiment,

```sh
mkdir gem5-configs
cd gem5-configs
git init
git remote add origin https://your-remote-add/run-spec-config.git
```

Then we copy all the scripts in configs-spec-tests folder to gem5-configs.

In the root folder of the experiment,

```sh
cd gem5-configs
wget https://raw.githubusercontent.com/darchr/gem5art/master/docs/gem5-configs/configs-spec-tests/run_spec.py
mkdir -p system
cd system
wget https://raw.githubusercontent.com/darchr/gem5art/master/docs/gem5-configs/configs-spec-tests/system/__init__.py
wget https://raw.githubusercontent.com/darchr/gem5art/master/docs/gem5-configs/configs-spec-tests/system/caches.py
wget https://raw.githubusercontent.com/darchr/gem5art/master/docs/gem5-configs/configs-spec-tests/system/fs_tools.py
wget https://raw.githubusercontent.com/darchr/gem5art/master/docs/gem5-configs/configs-spec-tests/system/system.py
cd ..
git add *
git commit -m "Add run scripts for SPEC2006"
```

In launch_spec2006_experiments.py, we make an Artifact object of the Linux kernel binary.

```python
run_script_repo = Artifact.registerArtifact(
    command = '''
        wget https://raw.githubusercontent.com/darchr/gem5art/master/docs/gem5-configs/configs-spec-tests/run_spec.py
        mkdir -p system
        cd system
        wget https://raw.githubusercontent.com/darchr/gem5art/master/docs/gem5-configs/configs-spec-tests/system/__init__.py
        wget https://raw.githubusercontent.com/darchr/gem5art/master/docs/gem5-configs/configs-spec-tests/system/caches.py
        wget https://raw.githubusercontent.com/darchr/gem5art/master/docs/gem5-configs/configs-spec-tests/system/fs_tools.py
        wget https://raw.githubusercontent.com/darchr/gem5art/master/docs/gem5-configs/configs-spec-tests/system/system.py
    ''',
    typ = 'git repo',
    name = 'gem5-configs',
    path =  'gem5-configs',
    cwd = './',
    documentation = 'gem5 run scripts made specifically for SPEC benchmarks'
)
```

The gem5 run script, [run_spec.py](https://github.com/darchr/gem5art/blob/master/docs/gem5-configs/configs-spec-tests/run_spec.py), takes the following parameters:
* --kernel: (required) the path to vmlinux file.
* --disk: (required) the path to spec image.
* --cpu: (required) name of the detailed CPU model.
Currently, we are supporting the following CPU models: kvm, o3, atomic, timing.
More CPU models could be added to getDetailedCPUModel() in run_spec.py.
* --benchmark: (required) name of the SPEC CPU 2006 benchmark.
The availability of the benchmarks could be found at the end of the tutorial.
* --size: (required) size of the benchmark. There are three options: ref, train, test.
* --no-copy-logs: this is an optional parameter specifying whether the spec log files should be copied to the host system.
* --no-listeners: this is an optional parameter specifying whether gem5 should open ports so that gdb or telnet could connect to.

We don't use another Artifact object to document this file.
The Artifact repository object of the root folder will keep track of the changes of the script.

**Note:** The first two parameters of the gem5 run script for full system simulation should always be the path to the linux binary and the path to the disk image, in that order.

## Run the Experiment
### Setting up the Python virtual environment
gem5art code works with Python 3.5 or above.

The following script will set up a python3 virtual environment named gem5art-env. In the root folder of the experiment,

```sh
virtualenv -p python3 gem5art-env
```

To activate the virtual environment, in the root folder of the experiment,

```sh
source gem5art-env/bin/activate
```

To install the gem5art dependency (this should be done when we are in the virtual environment),

```sh
pip install gem5art-artifact gem5art-run gem5art-tasks
```

To exit the virtual environment,

```sh
deactivate
```

**Note:** the following steps should be done while using the Python virtual environment.

### Running the Database Server
The following script will run the MongoDB database server in a docker container.

The -p 27017:27017 option maps the port 27017 in the container to port 27017 on the host.
The -v /path/in/host:/data/db option mounts the /data/db folder in the docker container to the folder /path/in/host in the host.
The path of the host folder should an absoblute path, and the database files created by MongoDB will be in that folder.
The --name mongo-1 option specifies the name of the docker container.
We can use this name to identify to the container.
The -d option will let the container run in the background.
mongo is the name of [the offical mongo image](https://hub.docker.com/_/mongo).

```sh
docker run -p 27017:27017 -v /path/in/host:/data/db --name mongo-1 -d mongo
```

### Running Celery Server
Inisde the path in the host specified above,

```sh
celery -E -A gem5art.tasks.celery worker --autoscale=[number of workers],0
```

### Creating the Launch Script Running the Experiment
Now, we can put together the run script!
In launch_spec2006_experiments.py, we import the required modules and classes at the beginning of the file,

```python
import os
import sys
from uuid import UUID

from gem5art.artifact import Artifact
from gem5art.run import gem5Run
from gem5art.tasks.tasks import run_gem5_instance
```

And then, we put the launch function at the end of launch_spec2006_experiments.py,

```python
if __name__ == "__main__":
    cpus = ['kvm', 'atomic', 'o3', 'timing']
    benchmark_sizes = {'kvm':    ['test', 'ref'],
                       'atomic': ['test'],
                       'o3':     ['test'],
                       'timing': ['test']
                      }
    benchmarks = ['401.bzip2','403.gcc','410.bwaves','416.gamess','429.mcf',
                  '433.milc','434.zeusmp','435.gromacs','436.cactusADM',
                  '437.leslie3d','444.namd','445.gobmk','453.povray',
                  '454.calculix','456.hmmer','458.sjeng','459.GemsFDTD',
                  '462.libquantum','464.h264ref','465.tonto','470.lbm',
                  '471.omnetpp','473.astar','481.wrf','482.sphinx3',
                  '998.specrand','999.specrand']
    # unavailable benchmarks: 400.perlbench,447.dealII,450.soplex,483.xalancbmk

    for cpu in cpus:
        for size in benchmark_sizes[cpu]:
            for benchmark in benchmarks:
                run = gem5Run.createFSRun(
                    'gem5 19 spec 2006 experiment',
                    'gem5/build/X86/gem5.opt', # gem5_binary
                    'gem5-configs/run_spec.py', # run_script
                    'results/{}/{}/{}'.format(cpu, size, benchmark), # relative_outdir
                    gem5_binary, # gem5_artifact
                    gem5_repo, # gem5_git_artifact
                    run_script_repo, # run_script_git_artifact
                    'linux-4.19.83/vmlinux-4.19.83', # linux_binary
                    'disk-image/spec2006/spec2006-image/spec2006', # disk_image
                    linux_binary, # linux_binary_artifact
                    disk_image, # disk_image_artifact
                    cpu, benchmark, size, # params
                    timeout = 5 * 24 * 60 * 60 # 5 days
                )
                run_gem5_instance.apply_async((run,))

```
The above launch function will run the all the available benchmarks with kvm, atomic, timing, and o3 cpus.
For kvm, both test and ref sizes will be run, while for the rest, only benchmarks of size test will be run.

Note that the line `'results/{}/{}/{}'.format(cpu, size, benchmark), # relative_outdir` specifies how the results folder is structured.
The results folder should be carefully structured so that there does not exist two gem5 runs write to the same place.

### Run the Experiment
Having celery and mongoDB servers running, we can start the experiment.

In the root folder of the experiment,

```sh
python3 launch_spec2006_experiment.py
```

## Getting the Results
The results folder of each benchmark has a folder named `speclogs`, which contains the logs of the run spec commands. There are two logs in this folder: `CPU2006.001.log` and `CPU2006.002.log`. The former is the log of compiling SPEC benchmarks, which is generated when we compile SPEC benchmarks while we create the disk image. The latter is the log of the benchmark run. So, we only interest in `CPU2006.002.log`.

If the benchmark run is successful, there will be a line starting with `Success: 1x` followed by `benchmark_name`. We will look for this line in each `CPU2006.002.log` file.

[This Python notebook shows how the Appendix I. Working SPEC 2006 Benchmarks x CPU Model table is generated](https://github.com/darchr/gem5art-experiments/blob/master/spec2006-experiments/results.ipynb).

## References
[1]  “Standard Performance Evaluation Corporation,” *SPEC CPU® 2006*. [Online]. Available: https://www.spec.org/cpu2006/. [Accessed: 12-Nov-2019].

[2] J. L. Henning, “SPEC CPU2006 benchmark descriptions,” *ACM SIGARCH Computer Architecture News*, vol. 34, no. 4, pp. 1–17, Jan. 2006.

[3] J. Owens, W. Dally, R. Ho, D. Jayasimha, S. Keckler, and L.-S. Peh, “Research Challenges for On-Chip Interconnection Networks,” IEEE Micro, vol. 27, no. 5, pp. 96–108, 2007.

[4] M. McCool, A. Robison, and J. Reinders, Structured parallel programming: patterns for efficient computation. Waltham, MA: Morgan Kaufmann, 2012.

[5] J. L. Hennessy and D. A. Patterson, “A new golden age for computer architecture,” *Communications of the ACM*, vol. 62, no. 2, pp. 48–60, 2019.


## Appendix I. Working SPEC 2006 Benchmarks x CPU Model table
Not all benchmarks are compiled in the above set up as of March 2020.
The following are compiled benchmarks:

| Benchmarks         | KVM/test        | KVM/ref         | AtomicCPU/test  | O3CPU/test      | TimingSimpleCPU/test |
|--------------------|-----------------|-----------------|-----------------|-----------------|----------------------|
| 401.bzip2          | Success         | Success         | Success         | Success         | Success              |
| 403.gcc            | Success         | Success         | Success         | Success         | Success              |
| 410.bwaves         | Success         | Success         | Success         | Success         | Success              |
| 416.gamess         | Success         | Success         | Success         | Success         | Success              |
| 429.mcf            | Success         | Success         | Success         | Success         | Success              |
| 433.milc           | Success         | Success         | Success         | Success         | Success              |
| 434.zeusmp         | Success         | Success         | Success         | No logs         | Success              |
| 435.gromacs        | Success         | Success         | Success         | Success         | Success              |
| 436.cactusADM      | Success         | Success         | Success         | Success         | Success              |
| 437.leslie3d       | Success         | Success         | Success         | Success         | Success              |
| 444.namd           | Success         | Success         | Success         | Success         | Success              |
| 445.gobmk          | Success         | Success         | Success         | TimeOut         | Success              |
| 453.povray         | Success         | Success         | Success         | Success         | Success              |
| 454.calculix       | Success         | Success         | Success         | Success         | Success              |
| 456.hmmer          | Success         | Success         | Success         | Success         | Success              |
| 458.sjeng          | Success         | Success         | Success         | Success         | Success              |
| 459.GemsFDTD       | Success         | Success         | Success         | Success         | Success              |
| 462.libquantum     | Success         | Success         | Success         | Success         | Success              |
| 464.h264ref        | Success         | Success         | Success         | Success         | Success              |
| 465.tonto          | Success         | Success         | Success         | Success         | Success              |
| 470.lbm            | Success         | Success         | Success         | Success         | Success              |
| 471.omnetpp        | Success         | Success         | Success         | Success         | Success              |
| 473.astar          | Success         | Success         | Success         | Success         | Success              |
| 481.wrf            | Success         | Success         | Success         | Success         | Success              |
| 482.sphinx3        | Success         | Success         | Success         | Success         | Success              |
| 998.specrand       | Success         | Success         | Success         | Success         | Success              |
| 999.specrand       | Success         | Success         | Success         | Success         | Success              |


Benchmarks that are not available:
```
Build errors:
400.perlbench
447.dealII
450.soplex
483.xalancbmk
```

## Appendix II. Transtition to SPEC 2017
As mentioned earlier, SPEC 2006 benchmark suite has been retired, and the newer version, SPEC 2017, is available.
This section will show how to reuse the scripts made for SPEC 2006 to run SPEC 2017 experiments.
Changes are minimal, ie. changing `2006` to `2017`, updating the location of the ISO file, changing SPEC 2006 run command (`runspec`) to SPEC 2017 run command (`runcpu`), and manipulating the SPEC 2017 config.
### Updating Disk Image Scripts
The disk image scripts to generate the SPEC 2017 disk image [could be found here](https://github.com/darchr/gem5art/tree/master/docs/disks/spec2017).
[The changes could be found here.](https://github.com/darchr/gem5art/commit/70019fd0196d946a65efd96bb9b2b692c0dd04be)

**Note:** In the example SPEC 2017 config, the workloads are compiled using the flag `-march=native`.
However, since workloads are compiled while the disk image is being building by packer, the binaries would be built accordingly to the configuration of the CPU simulated by packer.
This is definitely not ideal to run those binaries on gem5, which is not guaranteed to support all instructions of all hardware.
Hence, the `-march=native` flag is removed.
Other tuning flags should be manually added.
### Updating the Launch Script
The new launch script [could be found here](https://github.com/darchr/gem5art/blob/master/docs/launch-scripts/launch_spec2017_experiments.py).
Names of SPEC 2017 workloads are updated.

