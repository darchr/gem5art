# Tutorial: Run SPEC CPU 2017 Benchmarks in Full System Mode with gem5art  

## Introduction  
In this tutorial, we will demonstrate how to utilize gem5art to run SPEC CPU 2017 benchmarks in gem5 full system mode. 
The full example with all of the gem5art tutorials can be found [here](https://github.com/darchr/gem5art-experiments). 
The scripts in this tutorial work with gem5art-* v0.3.1.  

**Note**: This steps in this tutorial are mostly identical to those of [the SPEC 2006 tutorial](spec2006-tutorial.md). 
The differences are in the scripts used to create the disk image, and the name of the benchmarks.  


### SPEC CPU 2017 Benchmarks  
More details about those benchmarks are [here](https://www.spec.org/cpu2017/Docs/).  

### gem5 Full System Mode  
Different from the gem5 SE (syscall emulation) mode, the full system mode uses the Linux kernel instead of emulating syscalls. 
Therefore, the results would be more realistic if system calls are a significant portion of the benchmarks. 
In order to run gem5 in the full system mode, gem5 requires a built Linux kernel, which is configurable. 
gem5 does not support all configurations in Linux, but we will provide a Linux configuration that works with gem5. 
(See the [run exit tutorial](boot-tutorial.md) for details on what kernels are currently tested with gem5.) 
Other than that, a gem5 full system configuration is also a requirement to run gem5 full system mode. 
In this tutorial, we will provide working Linux configurations, the necessary steps to build a Linux kernel, and a working gem5 full system configuration.  

### Outline of the Experiment
We structure the experiment as follows (note that there are many more ways to structure the experiments, and the following is one of them),  
* root folder  
  * gem5: a folder containing gem5 source code and gem5 binaries.  
  * disk-image: a folder containing inputs to produce a disk image containing SPEC CPU 2017 benchmarks.  
  * linux-configs: a folder containing different Linux configurations for different Linux kernel versions.  
  * gem5-fullsystem-configs: a folder containing a gem5 configuration that is made specifically to run SPEC CPU 2017 benchmarks.  
  * results: a folder storing the experiment's results. This folder will have a certain structure in order to make sure that every gem5 run does not overwrite other gem5 runs results.  
  * launch_spec2017_experiments.py: a script that does the following,  
    * Documenting the experiment using Artifacts objects.  
    * Running the experiment in gem5 full system mode.  

### An Overview of Host System - gem5 Interactions
![**Figure 1.**]( spec_tutorial_figure1.png "")
A visual depict of how gem5 interacts with the host system. 
gem5 is configured to do the following: booting the Linux kernel, running the benchmark, and copying the SPEC outputs to the host system. 
However, since we are interested in getting the stats only for the benchmark, we configure gem5 to exit after the kernel is booted, and then we reset the stats before running the benchmark. 
We use KVM for Linux booting process as we want to quickly boot the system, and after the booting process is complete, we switch to the desired detailed CPU to run the benchmark. 
Similarly, after the benchmark is complete, gem5 exits to host, which allows us to get the stats at that point. 
After that, we switch the CPU back to KVM, which allows us to quickly write the SPEC output files to the host.  

**Important:** gem5 will output the stats again when the gem5 run is complete. 
Therefore, we will see two stats in one file in stats.txt. 
The stats of the benchmark is the the first part of stats.txt, while the second part of the file contains the stats of the benchmark AND the process of writing output files back to the host. 
We are only interested in the first part of stats.txt.

## Documenting the Preparing Steps  
### Setting up the Experiment Folder
We set up a folder to contain (almost) all materials of the experiment. 
We use git to keep track of changes in the folder. 

```sh
mkdir spec2017-experiments
cd spec2017-experiments
git init
```

We need add a remote to the repository. 

```sh
git remote add origin https://your-remote-add/spec2017-experiment.git
```

We document the root folder of the experiment in launch_spec2017_experiments.py as follows,

```sh
experiments_repo = Artifact.registerArtifact(
    command = '',
    typ = 'git repo',
    name = 'experiment',
    path =  './',
    cwd = './',
    documentation = 'local repo to run spec 2017 experiments with gem5'
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
disk-image/spec2017/spec2017-image/spec2017
disk-image/packer_cache
disk-image/spec2017/cpu2017-1.1.0.iso
gem5
linux-4.19.83/
```

Essentially, we will ignore files and folders that when we use gem5art to keep track of them, or the presence of those files and folders do not affect the experiment's results.

### Building gem5  
In this step, we download the source code and build gem5. 
In this tutorial, we use m5 writefile function to copy the file from the disk image to the host system.
That function does not work out-of-the-box in the current version of gem5 (as of December 2019). 
We need to cherry-pick two commits, one from googlesource, and one from darchr/gem5 on GitHub for that function to work. 

```sh
git clone https://gem5.googlesource.com/public/gem5
cd gem5
git remote add darchr https://github.com/darchr/gem5
git fetch darchr  
git cherry-pick 6450aaa7ca9e3040fb9eecf69c51a01884ac370c  
git cherry-pick 3403665994b55f664f4edfc9074650aaa7ddcd2c
scons build/X86/gem5.opt -j8
```

We have two artifacts: one is the gem5 source code (the gem5 git repo), and the gem5 binary. 
The documentation of this step would be how we get the source code and how we compile the gem5 binary. 
In launch_spec2017_experiments.py, we document the step in Artifact objects as follows,

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
    documentation = 'cloned gem5 master branch from googlesource and cherry-picked 2 commits on Nov 20th'
)


gem5_binary = Artifact.registerArtifact(
    command = 'scons build/X86/gem5.opt -j8',
    typ = 'gem5 binary',
    name = 'gem5',
    cwd = 'gem5/',
    path =  'gem5/build/X86/gem5.opt',
    inputs = [gem5_repo,],
    documentation = 'compiled gem5 binary right after downloading the source code, this has two cherry picked changes to fix m5 readfile in KVM'
)
```

### Building m5  
m5 is a binary that facilitates the communication between the host system and the guest system (gem5). 
The examples of how m5 is used could be found in the runscripts that we will describe later. 
m5 binary will be copied to the disk image, so that the guest could run m5 binary during the experiment. 
Therefore, m5 binary should be compiled before we build the disk image.  

**Note:** it's important to compile the m5 binary with -DM5_ADDR=0xFFFF0000 as is default in the Makefile. If you don't compile with -DM5_ADDR and try to run with KVM you'll get an illegal instruction error.  

To compile m5 binary,  

```sh
cd gem5/util/m5/
make -f Makefile.x86
```

In launch_spec2017_experiments.py, we document the step in an Artifact object as follows,  

```python
m5_binary = Artifact.registerArtifact(
    command = 'make -f Makefile.x86',
    typ = 'binary',
    name = 'm5',
    path =  'gem5/util/m5/m5',
    cwd = 'gem5/util/m5',
    inputs = [gem5_repo,],
    documentation = 'm5 utility'
)
```

### Preparing Scripts to Modify the Disk Image
In this step, we will prepare the scripts that will modify the disk image after the Ubuntu installation process has finished, and before the first time we use the disk image in gem5. 
We will keep the related files in the disk-image folder of the experiment. 
The files that are made specifically for SPEC 2017 benchmarks will be in disk-image/spec2017, and the files that are commonly used accross most benchmarks will be in disk-image/shared.  

In the root folder of the experiment,

```sh
mkdir disk-image
mkdir disk-image/spec2017
mkdir disk-image/shared
```

The first script is the runscript.sh script, which will be appended to the end of `.bashrc` file. 
Therefore, that script will run when we use the disk image in gem5, after the Linux booting process has finished. 
Figure 1 describes how this script interacts with the gem5 config file.  
The script could be found [here](https://github.com/darchr/gem5art/blob/master/docs/disks/spec2017/runscript.sh).

To download the script, in the root folder of the experiment,

```sh
cd disk-image/spec2017
wget https://raw.githubusercontent.com/darchr/gem5art/master/docs/disks/spec2017/runscript.sh
```

The second script is post-installation.sh script, which will copy the "auto logging in" script to the correct place, and copy the m5 binary to /sbin/ in the disk image. 
This script will also append the above script (runscript.sh) to the end of `.bashrc`.  
The script could be found [here](https://github.com/darchr/gem5art/blob/master/docs/disks/spec2017/post-installation.sh).

To download the script, in the root folder of the experiment,

```sh
cd disk-image/spec2017
wget https://raw.githubusercontent.com/darchr/gem5art/master/docs/disks/spec2017/post-installation.sh
```

The third script is the install-spec2017.sh script, which will install the dependencies required to compile and run the SPEC 2017 benchmarks, which will be compiled and built in the script. 
We figure out that the dependencies include g++, gcc, and gfortran. 
So we will get the build-essential and gfortran packages from Debian (note that "12345" is the default password, this could be modified in the spec2017.json file). 
The script also modifies the default config script to make the benchmarks work with this set up.  
The script could be found [here](https://github.com/darchr/gem5art/blob/master/docs/disks/spec2017/post-installation.sh).

To download the script, in the root folder of the experiment,

```sh
cd disk-image/spec2017
wget https://raw.githubusercontent.com/darchr/gem5art/master/docs/disks/spec2017/install-spec2017.sh
```

We also need two other files: the auto logging in script and Ubuntu preseed. 
Those files are usually reused by other benchmarks, so we will keep them in disk-image/shared. 
The auto logging in script is [here](https://github.com/darchr/gem5art/blob/master/docs/disks/shared/preseed.cfg), and the Ubuntu preseed configuration is [here](https://github.com/darchr/gem5art/blob/master/docs/disks/shared/serial-getty%40.service).  

In the root folder of the experiment,

```sh
cd disk-image/shared
wget https://raw.githubusercontent.com/darchr/gem5art/master/docs/disks/shared/preseed.cfg
wget https://raw.githubusercontent.com/darchr/gem5art/master/docs/disks/shared/serial-getty%40.service
```

We don't make Artifact objects for those scripts. 
Instead, we let the Artifact repository object of the root folder to keep track of the changes in the above scripts. 

### Building the Disk Image  
Having prepared necessary scripts to create the disk image, in this step, we will build the disk image using [packer](https://www.packer.io/).  

First, we download the packer binary. 
The current version of packer as of November 2019 is 1.4.5.  

```sh
cd disk-image/
wget https://releases.hashicorp.com/packer/1.4.5/packer_1.4.5_linux_amd64.zip
unzip packer_1.4.5_linux_amd64.zip
rm packer_1.4.5_linux_amd64.zip
```

In launch_spec2017_experiments.py, we document how we obtain the binary as follows, 

```python
packer = Artifact.registerArtifact(
    command = '''
        wget https://releases.hashicorp.com/packer/1.4.5/packer_1.4.5_linux_amd64.zip;
        unzip packer_1.4.5_linux_amd64.zip;
    ''',
    typ = 'binary',
    name = 'packer',
    path =  'disk-image/packer',
    cwd = 'disk-image',
    documentation = 'Program to build disk images. Downloaded sometime in November from hashicorp.'
)
```

Second, we create a packer script (a json file) that describes how the disk image will be built. 
In this step, we assume that we have the SPEC 2017 ISO file in the disk-image/spec2017 folder. 
In this script, the ISO file name is cpu2017-1.1.0.iso. 
The script is available [here](https://github.com/darchr/gem5art/blob/master/docs/disks/spec2017/spec2017.json), and we save the file at disk-image/spec2017/spec2017.json.  

In the root folder of experiment,

```sh
cd disk-image/spec2017/
wget https://raw.githubusercontent.com/darchr/gem5art/master/docs/disks/spec2017/spec2017.json
```

To build the disk image,

```sh
cd disk-image/
./packer validate spec2017/spec2017.json # validate the script, including checking the input files
./packer build spec2017/spec2017.json
```

The process should not take more than an hour on a fairly recent machine with a normal internet speed. 
The disk image will be in disk-image/spec2017/spec2017-image/spec2017.  

**Note:**: Packer will output a VNC port that could be used to inspect the building process. 
Ubuntu has a built-in VNC viewer, namely Remmina.  

**Note:**: [More about using packer and building disk images](disks.md).  

Now, in launch_spec2017_experiments.py, we make an Artifact object of the disk image.  

```python
disk_image = Artifact.registerArtifact(
    command = './packer build spec2017/spec2017.json',
    typ = 'disk image',
    name = 'spec2017',
    cwd = 'disk-image/',
    path = 'disk-image/spec2017/spec2017-image/spec2017',
    inputs = [packer, experiments_repo, m5_binary,],
    documentation = 'Ubuntu Server with SPEC 2017 installed, m5 binary installed and root auto login'
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

Now, in launch_spec2017_experiments.py, we make an Artifact object of the Linux stable git repo.

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
    documentation = 'Linux kernel 4.19 source code repo obtained in November'
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
wget https://raw.githubusercontent.com/darchr/gem5art/master/docs/linux-configs/config.4.19.83
```

The following commands will copy the linux config and compile the linux kernel. 
In the root folder of the experiment,

```sh
cp linux-configs/config.4.19.83 linux-4.19.83/.config
cd linux-4.19.83
make -j8
cp vmlinux vmlinux-4.19.83
```

Now, in launch_spec2017_experiments.py, we make an Artifact object of the Linux kernel binary.

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
We offer example scripts in the [configs-spec2017-tests folder](https://github.com/darchr/gem5art/blob/master/docs/configs-spec2017-tests/).   

First, we create a folder named gem5-configs containing all gem5 configs. 
Since gem5art requires a git repo for the run scripts, we will make a local git repo for the run scripts.  

In the root folder of the experiment,

```sh
mkdir gem5-configs
cd gem5-configs
git init
```

Then we copy all the scripts in configs-spec2017-tests folder to gem5-configs.  

In the root folder of the experiment,

```sh
cd gem5-configs
wget https://raw.githubusercontent.com/darchr/gem5art/master/docs/configs-spec-tests/run_spec.py
mkdir -p system
cd system
wget https://raw.githubusercontent.com/darchr/gem5art/master/docs/configs-spec-tests/system/__init__.py
wget https://raw.githubusercontent.com/darchr/gem5art/master/docs/configs-spec-tests/system/caches.py
wget https://raw.githubusercontent.com/darchr/gem5art/master/docs/configs-spec-tests/system/fs_tools.py
wget https://raw.githubusercontent.com/darchr/gem5art/master/docs/configs-spec-tests/system/system.py
cd ..
git add *
git commit -m "Add run scripts for SPEC2017"
```

In launch_spec2017_experiments.py, we make an Artifact object of the Linux kernel binary.  

```python
run_script_repo = Artifact.registerArtifact(
    command = '''
        wget https://raw.githubusercontent.com/darchr/gem5art/master/docs/configs-spec-tests/run_spec.py
        mkdir -p system
        cd system
        wget https://raw.githubusercontent.com/darchr/gem5art/master/docs/configs-spec-tests/system/__init__.py
        wget https://raw.githubusercontent.com/darchr/gem5art/master/docs/configs-spec-tests/system/caches.py
        wget https://raw.githubusercontent.com/darchr/gem5art/master/docs/configs-spec-tests/system/fs_tools.py
        wget https://raw.githubusercontent.com/darchr/gem5art/master/docs/configs-spec-tests/system/system.py
    ''',
    typ = 'git repo',
    name = 'gem5-configs',
    path =  'gem5-configs',
    cwd = './',
    documentation = 'gem5 run scripts made specifically for SPEC benchmarks'
)
```

The gem5 run script, [run_spec.py](https://github.com/darchr/gem5art/blob/master/docs/configs-spec2017-tests/run_spec.py), takes the following parameters:  
* --kernel: (required) the path to vmlinux file.  
* --disk: (required) the path to spec image.  
* --cpu: (required) name of the detailed CPU model. 
Currently, we are supporting the following CPU models: kvm, o3, atomic, timing. 
More CPU models could be added to getDetailedCPUModel() in run_spec.py.  
* --benchmark: (required) name of the SPEC CPU 2017 benchmark. 
The availability of the benchmarks could be found [here](#) TODO.  
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
In launch_spec2017_experiments.py, we import the required modules and classes at the beginning of the file,

```python
import os
import sys
from uuid import UUID

from gem5art.artifact import Artifact
from gem5art.run import gem5Run
from gem5art.tasks.tasks import run_gem5_instance
```

And then, we put the launch function at the end of launch_spec2017_experiments.py,

```python
if __name__ == "__main__":
    cpus = ['kvm', 'atomic', 'o3', 'timing']
    benchmark_sizes = {'kvm':    ['test', 'ref'],
                       'atomic': ['test'],
                       'o3':     ['test'],
                       'timing': ['test']
                      }
    benchmarks = [TODO]
    # unavailable benchmarks: 400.perlbench,447.dealII,450.soplex,483.xalancbmk

    for cpu in cpus:
        for size in benchmark_sizes[cpu]:
            for benchmark in benchmarks:
                run = gem5Run.createFSRun(
                    'gem5/build/X86/gem5.opt', # gem5_binary
                    'gem5-configs/run_spec.py', # run_script
                    'results/{}/{}/{}'.format(cpu, size, benchmark), # relative_outdir
                    gem5_binary, # gem5_artifact
                    gem5_repo, # gem5_git_artifact
                    run_script_repo, # run_script_git_artifact
                    'linux-4.19.83/vmlinux-4.19.83', # linux_binary
                    'disk-image/spec2017/spec2017-image/spec2017', # disk_image
                    linux_binary, # linux_binary_artifact
                    disk_image, # disk_image_artifact
                    cpu, benchmark, size, # params
                    timeout = 5*24*60*60 # 5 days
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
python3 launch_spec2017_experiment.py
```

## Getting the Results  
TODO

## Appendix I. Working SPEC 2017 Benchmarks x CPU Model Matrix
All benchmarks are compiled in the above set up as of December 2019. 
The following are compiled benchmarks:  

| Benchmarks             | KVM/test       | KVM/ref        | O3CPU/test     | AtomicCPU/test | TimingSimpleCPU/test |
|------------------------|----------------|----------------|----------------|----------------|----------------------|
| 503.bwaves_r           |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 507.cactuBSSN_r        |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 508.namd_r             |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 510.parest_r           |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 511.povray_r           |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 519.lbm_r              |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 521.wrf_r              |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 526.blender_r          |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 527.cam4_r             |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 538.imagick_r          |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 544.nab_r              |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 549.fotonik3d_r        |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 554.roms_r             |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 997.specrand_fr        |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 603.bwaves_s           |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 607.cactuBSSN_s        |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 619.lbm_s              |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 621.wrf_s              |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 627.cam4_s             | Workload segfault | Workload segfault |      gem5 error |     gem5 error |                     ?|
| 628.pop2_s             |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 638.imagick_s          |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 644.nab_s              |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 649.fotonik3d_s        |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 654.roms_s             |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 996.specrand_fs        |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 500.perlbench_r        |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 502.gcc_r              |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 505.mcf_r              |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 520.omnetpp_r          |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 523.xalancbmk_r        |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 525.x264_r             |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 531.deepsjeng_r        |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 541.leela_r            |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 548.exchange2_r        |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 557.xz_r               |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 999.specrand_ir        |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 600.perlbench_s        |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 602.gcc_s              |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 605.mcf_s              |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 620.omnetpp_s          |        Success |        Success |     gem5 error |              ? |                     ?|
| 623.xalancbmk_s        |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 625.x264_s             |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 631.deepsjeng_s        |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 641.leela_s            |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 648.exchange2_s        |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 657.xz_s               |        Success |        Success |     gem5 error |     gem5 error |                     ?|
| 998.specrand_is        |        Success |        Success |     gem5 error |     gem5 error |                     ?|


