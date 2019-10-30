# Disk Images

## Introduction

We provide guide to help you create gem5-compatible disk images with Ubuntu Server installed. We make use of packer to do this which makes use of a .json template files to build and configure a disk image. These template files can be configured to build a disk image with specific benchmarks installed.



## Build a Simple Disk Image with Packer
<a name="packerbriefly"></a>
### a. How It Works, Briefly
We utilize [Packer](https://www.packer.io/) and [QEMU](https://www.qemu.org/) in order to facilitate the automation process.
Essentially, QEMU will be responsible for setting up a virtual machine and all interactions with the disk image during the building process.
The interactions include installing Ubuntu Server to the disk image, copying files from your machine to the disk image, and running scripts after Ubuntu is installed.
However, we will not use QEMU directly.
Packer provides a simpler way to interact with QEMU using a JSON script, which is more expressive than using QEMU from command line.
<a name="dependencies"></a>
### b. Install Required Software/Dependencies
To install QEMU,
```shell
sudo apt-get install qemu
```
Download the Packer binary from [the official website](https://www.packer.io/downloads.html).
<a name="customizing"></a>
### c. Customize the Packer Script
The script should be able to run out-of-the-box; however, there are variables that you should modify to make the building process more efficient.
The variables that should be modified appear at the end of `template.json` file, in `variables` section.
By VM, we refer to the virtual machine run by QEMU.
The files to be modified are as follows,
```shell
disk-image/
  template.json: packer script
  scripts/
    post-installation.sh: shell script that is executed after Ubuntu is installed
  http/
    preseed.cfg: preseeded configuration to install Ubuntu
```

<a name="customizingVM"></a>
#### i. Customize the VM
In `template.json`,

| Variable         | Purpose     | Example  |
| ---------------- |-------------|----------|
| [vm_cpus](https://www.packer.io/docs/builders/qemu.html#cpus) **(should be modified)** | number of host CPUs used by VM | "2": 2 CPUs are used by the VM |
| [vm_memory](https://www.packer.io/docs/builders/qemu.html#memory) **(should be modified)** | amount of memory used by VM, in megabytes | "2048": 2 GB of RAM are used by the VM |
| [vm_accelerator](https://www.packer.io/docs/builders/qemu.html#accelerator) **(should be modified)** | accelerator used by the VM, e.g. kvm | "kvm": kvm will be used |

<a name="customizingscripts"></a>
#### ii. Customize the Disk Image
In `template.json`,

| Variable        | Purpose     | Example  |
| ---------------- |-------------|----------|
| [image_size](https://www.packer.io/docs/builders/qemu.html#disk_size) **(should be modified)** | size of the disk image, in megabytes | "8192": the image has the size of 8 GB  |

<a name="customizingscripts2"></a>
#### iii. File Transfer
In `template.json`, under `provisioners`, you could add the following,
```shell
{
    "type": "file",
    "source": "examples/helloworld.sh",
    "destination": "/home/gem5/",
    "direction": "upload"
}
```
The above example copy the file `example/helloworld.sh` from the host to `/home/gem5/` in the disk image.
This method is also capable of copy a folder from host to the disk image and vice versa.
**Note: this is important** Trailing slash affects the copying process. [More details](https://www.packer.io/docs/provisioners/file.html#directory-uploads)
The following are some notable examples of the effect of using slash at the end of the paths.

| `source`        | `destination`     | `direction`  |  `Effect`  |
| ---------------- |-------------|----------|-----|
| `foo.txt` | `/home/gem5/bar.txt` | `upload` | copy file (host) to file (image) |
| `foo.txt` | `bar/` | `upload` | copy file (host) to folder (image) |
| `/foo` | `/tmp` | `upload` | `mkdir /tmp/foo` (image);  `cp -r /foo/* (host) /tmp/foo/ (image)`; |
| `/foo/` | `/tmp` | `upload` | `cp -r /foo/* (host) /tmp/ (image)` |

If `direction` is `download`, the files will be copied from the image to the host.
**Note**: [This is a way to run script once after installing Ubuntu without copying to the disk image](#customizingscripts3).

<a name="customizingscripts3"></a>
#### iv. Install Benchmark Dependencies
To install the dependencies, we utilize the bash script `scripts/post_installation.sh`, which will be run after the Ubuntu installation and file copying is done.
For example, if we want to install `gfortran` In `scripts/post_installation.sh`, add the following
```shell
echo '12345' | sudo apt-get install gfortran;
```
In the above example, we assume that the user password is `12345`.
This is essentially a bash script that is executed on the VM after the file copying is done, you could modify the script as a bash script to fit any purpose.
<a name="customizingscripts4"></a>
#### v. Running Other Scripts on Disk Image
In `template.json`, we could add more scripts to `provisioners`.
Note that the files are on the host, but the effects are on the disk image.
For example, the following example runs `scripts/post_installation.sh` and `example/helloworld.sh` after Ubuntu is installed,
```shell
{
    "type": "shell",
    "execute_command": "echo '{{ user `ssh_password` }}' | {{.Vars}} sudo -E -S bash '{{.Path}}'",
    "scripts":
    [
        "scripts/post-installation.sh",
        "examples/helloworld.sh"
    ]
}
```
<a name="buildsimple"></a>
### d. Build the Disk Image
<a name="simplebuild"></a>
#### i. Build
To validate the Packer script,
```shell
./packer validate template.json
```
To build the disk image,
```shell
./packer build template.json
```
On a fairly recent machine, the building process should not take more than 15 minutes to complete.
The image will be on `ubuntu-image` folder.
[We recommend to use a VNC viewer in order to inspect the building process](#inspect).
<a name="inspect"></a>
#### ii. Inspect the Building Process
You can use a VNC viewer to view the process using the VNC address provided by Packer.
VNC stands for Virtual Network Computing.
While the building process takes place, Packer will run a VNC server and you will be able to see the building process by connect to the VNC server from a VNC client.
There are plenty of choices for VNC client. When you run the Packer script, it will tell you which port is the VNC server using. For example, if it says `qemu: Connecting to VM via VNC (127.0.0.1:5932)`, the VNC port is 5932.
To connect to VNC server from the VNC client, use the address `127.0.0.1:5932`. The address might vary.
If you need port forwarding to forward the VNC port from another machine to your machine, use SSH tunneling
```shell
ssh -L 5932:127.0.0.1:5932 <username>@<host>
```
This command will forward port 5932 from the host machine to your machine, and then you will be able to connect to the VNC server using the address `127.0.0.1:5932` from your VNC viewer.
More details could be found [here](https://www.cl.cam.ac.uk/research/dtg/attarchive/vnc/sshvnc.html).
**Note**: While Packer is installing Ubuntu, the terminal screen will display "waiting for SSH" without any update for a long time.
This is not an indicator of whether the Ubuntu installation produces any errors.
Therefore, we strongly recommend using VNCviewer at least once to validate the whole image building process.
<a name="checking"></a>


The template file is first validated using:
```sh
./packer validate template.json
```
The template file is then used to build the disk image:
```sh
./packer build template.json
```
