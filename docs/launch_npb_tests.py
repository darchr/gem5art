import os
import sys
from uuid import UUID

from gem5art.artifact.artifact import Artifact
from gem5art.run import gem5Run
from gem5art.tasks.tasks import run_gem5_instance

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

experiments_repo = Artifact.registerArtifact(
    command = 'git clone https://your-remote-add/npb-tests.git',
    typ = 'git repo',
    name = 'npb',
    path =  './',
    cwd = '../',
    documentation = 'main repo to run npb with gem5'
)

gem5_repo = Artifact.registerArtifact(
    command = 'git clone https://gem5.googlesource.com/public/gem5',
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
    command = 'packer build npb.json',
    typ = 'disk image',
    name = 'npb',
    cwd = 'disk-image/npb',
    path = 'disk-image/npb/npb-image/npb',
    inputs = [packer, experiments_repo, m5_binary,],
    documentation = 'Ubuntu with m5 binary installed and root auto login'
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
    command = '''git clone https://github.com/torvalds/linux.git;
    mv linux linux-stable''',
    typ = 'git repo',
    name = 'linux-stable',
    path =  'linux-stable/',
    cwd = './',
    documentation = 'linux kernel source code repo from Sep 23rd'
)

linux_binary = Artifact.registerArtifact(
    name = 'vmlinux-5.2.3',
    typ = 'kernel',
    path = 'linux-stable/vmlinux-5.2.3',
    cwd = 'linux-stable/',
    command = '''git checkout v{version};
    cp ../config.5.2.3 .config;
    make -j8;
    cp vmlinux vmlinux-5.2.3;
    ''',
    inputs = [experiments_repo, linux_repo,],
    documentation = "kernel binary for v5.2.3",
)


if __name__ == "__main__":
    num_cpus = ['1', '4']
    benchmarks = ['is.C.x', 'ep.C.x', 'cg.C.x', 'mg.C.x',
            'ft.C.x', 'bt.C.x', 'sp.C.x', 'lu.C.x']

for num_cpu in num_cpus:
	for bm in benchmarks:
		run = gem5Run.createFSRun(
			'gem5/build/X86/gem5.opt',
			'configs-npb-tests/run_npb.py',
			gem5_binary, gem5_repo, experiments_repo,
			'linux-stable/vmlinux-5.2.3',
			'disk-image/npb/npb-image/npb',
			linux_binary, disk_image,
			bm, num_cpu
			)
		run_gem5_instance.apply_async((run,))