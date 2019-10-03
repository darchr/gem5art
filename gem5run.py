"""
This file defines a celery app for gem5.
There is one task, `run`, which will run a gem5 instance.
"""

from . import artifact

import hashlib
import json
import os
import signal
import subprocess
import time
import shutil
from uuid import UUID


class gem5Run:
    """
    This class holds all of the info required to run gem5. If you want to also
    track other information (e.g., the binary you are running in SE mode or
    the disk image/kernel in FS mode) you should extend this class.
    """

    def __init__(self, gem5_binary, run_script,
                 gem5_artifact, gem5_git_artifact, run_script_git_artifact,
                 *params, timeout=60*15):
        """
        gem5_binary and run_script are the paths to the binary to run
        and the script to pass to gem5. Full paths are better.

        The artifact parameters (gem5_artifact, gem5_git_artifact, and
        run_script_git_artifact) are used to ensure this is reproducible run.

        Further parameters can be passed via extra arguments. These
        parameters will be passed in order to the gem5 run script.
        timeout is the time in seconds to run the subprocess before killing it.

        Note: When instantiating this class for the first time, it will create
        a file `info.json` in the outdir which contains a serialized version
        of this class.
        """
        self.gem5_binary = gem5_binary
        self.run_script = run_script
        self.extra_params = list(params)
        self.gem5_artifact = gem5_artifact
        self.gem5_git_artifact = gem5_git_artifact
        self.run_script_git_artifact = run_script_git_artifact
        self.artifacts = [gem5_artifact, gem5_git_artifact,
                          run_script_git_artifact]
        self.timeout = timeout

        # Assumes **/<gem5_name>/gem5.<anything>
        self.gem5_name = os.path.split(os.path.split(self.gem5_binary)[0])[1]
        # Assumes **/<script_name>.py
        self.script_name = os.path.split(self.run_script)[1].split('.')[0]

        self.outdir = os.path.abspath(self.getOutdir())
        # Make the directory if it doesn't exist
        os.makedirs(self.outdir, exist_ok=True)
        # The relative path is useful for printing
        self.relative_outdir = self.getOutdir()

        self.command = [
            self.gem5_binary,
            '-re', '--outdir={}'.format(self.outdir),
            self.run_script]
        self.command += list(params)

        self.running = False

        self.enqueue_time = time.time()
        self.start_time = 0
        self.end_time = 0

        self.return_code = None
        self.kill_reason = None
        self.status = "Created"

        self.pid = 0
        self.task_id = None

        # Initially, there are no results
        self.results = None

        # If this is the first time this has been run, dump the info
        # Note: we don't want to overwrite the last run!
        if not os.path.exists(os.path.join(self.outdir, 'info.json')):
            self.dumpJson('info.json')

    def checkArtifacts(self):
        """Checks to make sure all of the artifacts are up to date

        This should happen just before running gem5. This function will return
        False if the artifacts don't check and true if they are all the same.
        For the git repos, this checks the git hash, for binary artifacts this
        checks the md5 hash.
        """
        for v in self.artifacts:
            if v.type == 'git repo':
                new = artifact.getGit(v.path)['hash']
                old = v.git['hash']
            else:
                new = artifact.getHash(v.path)
                old = v.hash

            if new != v.hash:
                status = f"Failed artifact check for {v.path}"
                return False

        return True

    def __repr__(self):
        return repr(self.__dict__)

    def getOutdir(self):
        """
        Constructs the output directory from the gem5 build opts (e.g., X86,
        ARM, MOESI_hammer), the gem5 run script, and the extra parameters.
        """
        return os.path.join('results',
                            self.gem5_name,
                            self.script_name,
                            *self.extra_params)

    def checkKernelPanic(self):
        """
        Returns true if the gem5 instance specified in args has a kernel panic
        Note: this gets around the problem that gem5 doesn't exit on panics.
        """
        term_path = os.path.join(self.outdir, 'system.pc.com_1.device')
        if not os.path.exists(term_path):
            return False

        with open(term_path, 'rb') as f:
            try:
                f.seek(-1000, os.SEEK_END)
            except OSError:
                return False
            last = f.readlines()[-1].decode()
            if 'Kernel panic' in last:
                return True
            else:
                return False

    def _getSerializable(self):
        """Returns a dictionary that can be used to recreate this object"""
        # Grab all of the member variables
        d = vars(self).copy()
        # Replace the artifacts with their UUIDs
        d['gem5_artifact'] = self.gem5_artifact._id
        d['gem5_git_artifact'] = self.gem5_git_artifact._id
        d['run_script_git_artifact'] = self.run_script_git_artifact._id
        if d['results']: d['results'] = self.results._id
        # Remove list of artifacts
        del d['artifacts']

        d['hash'] = self._getHash()
        return d

    def _getHash(self):
        """Return a single value that uniquely identifies this run

        To uniquely identify this run, the gem5 binary, gem5 scripts, and
        parameters should all match. Thus, let's make a single hash out of the
        artifacts + the runscript + parameters
        """
        to_hash = [self.gem5_artifact._id.bytes,  # UUID of gem5 binary
                   self.gem5_git_artifact._id.bytes, # UUID of gem5 git
                   self.run_script_git_artifact._id.bytes, # UUID of cur repo
                   self.run_script.encode(), # Script we're running
                   ' '.join(self.extra_params).encode(), # string of parameters
                  ]

        return hashlib.md5(b''.join(to_hash)).hexdigest()

    @classmethod
    def _convertForJson(cls, d):
        for k,v in d.items():
            if isinstance(v, UUID):
                d[k] = str(v)
        return d

    def dumpJson(self, filename):
        """
        Dump all info into a json file. This could be used to reconstruct
        this instance, but that functionality doesn't exist, yet.
        """
        d = self._convertForJson(self._getSerializable())
        with open(os.path.join(self.outdir, filename), 'w') as f:
            json.dump(d, f)

    def dumpsJson(self):
        """
        Like dumpJson except returns string
        """
        d = self._convertForJson(self._getSerializable())
        return json.dumps(d)

    @classmethod
    def loadJson(cls, filename):
        with open(filename) as f:
            d = json.load(f)
        try:
            return cls.loadFromDict(d)
        except KeyError:
            print("Incompatible json file: {}!".format(filename))
            raise

    @classmethod
    def loadFromDict(cls, d):
        return cls(d['gem5_binary'], d['run_script'],
                   artifact.Artifact(UUID(d['gem5_artifact'])),
                   artifact.Artifact(UUID(d['gem5_git_artifact'])),
                   artifact.Artifact(UUID(d['run_script_git_artifact'])),
                  *d['extra_params'], timeout=d['timeout'])

    def run(self, task = None):
        """
        Actually run the test. Just calls Popen with the command.
        Then, this function polls the process every 5 seconds to check if it
        has finished or not. Each time it checks, it dumps the json info so
        other applications can poll those files.
        task is the celery task that is running this gem5 instance.
        """
        self.status = "Begin run"
        self.dumpJson('info.json')

        if not self.checkArtifacts():
            self.dumpJson('info.json')
            return

        self.status = "Spawning"

        self.start_time = time.time()
        self.task_id = task.request.id if task else None
        self.dumpJson('info.json')

        # Start running the gem5 command
        proc = subprocess.Popen(self.command)

        # Register handler in case this process is killed while the gem5
        # instance is running. Note: there's a bit of a race condition here,
        # but hopefully it's not a big deal
        def handler(signum, frame):
            proc.kill()
            self.kill_reason = 'sigterm'
            self.dumpJson('info.json')
            # Note: We'll fall out of the while loop after this.

        # This makes it so if you term *this* process, it will actually kill
        # the subprocess and then this process will die.
        signal.signal(signal.SIGTERM, handler)

        # Do this until the subprocess is done (successfully or not)
        while proc.poll() is None:
            self.status = "Running"
            # Still running
            self.current_time = time.time()
            self.pid = proc.pid
            self.running = True

            if self.current_time - self.start_time > self.timeout:
                proc.kill()
                self.kill_reason = 'timeout'

            if self.checkKernelPanic():
                proc.kill()
                self.kill_reason = 'kernel panic'

            self.dumpJson('info.json')

            # Check again in five seconds
            time.sleep(5)

        print("Done running {}".format(' '.join(self.command)))

        # Done executing
        self.running = False
        self.end_time = time.time()
        self.return_code = proc.returncode

        if self.return_code == 0:
            self.status = "Finished"
        else:
            self.status = "Failed"

        self.dumpJson('info.json')

        shutil.make_archive('results', 'zip', self.getOutdir())

        self.results = artifact.Artifact.registerArtifact(
                command = 'zip results.zip -r' + self.getOutdir(),
                name = 'results',
                typ = 'directory',
                path =  './results.zip',
                cwd = './',
                documentation = 'Compressed version of the results directory'
        )


        os.remove('./results.zip')


class gem5RunFS(gem5Run):

    def __init__(self, gem5_binary, run_script,
                gem5_artifact, gem5_git_artifact, run_script_git_artifact,
                linux_binary, disk_image,
                linux_binary_artifact, disk_image_artifact,
                *params):
        """
        gem5_binary and run_script are the paths to the binary to run
        and the script to pass to gem5.
        The linux_binary is the kernel to run and the disk_image is the path
        to the disk image to use.
        Further parameters can be passed via extra arguments. These
        parameters will be passed in order to the gem5 run script.
        """
        # Must set up name parameters before calling supper __init__ so that
        # the outdir will be created correctly.
        self.linux_binary = linux_binary
        self.disk_image = disk_image
        self.local_extra_params = params
        self.linux_binary_artifact = linux_binary_artifact
        self.disk_image_artifact = disk_image_artifact

        # Assumes **/<linux_name>
        self.linux_name = os.path.split(self.linux_binary)[1]
        # Assumes **/<disk_name>
        self.disk_name = os.path.split(self.disk_image)[1]

        super(gem5RunFS, self).__init__(
            gem5_binary, run_script,
            gem5_artifact, gem5_git_artifact, run_script_git_artifact,
            linux_binary, disk_image,
            *params, timeout=3600*5
        )

        self.artifacts.extend([disk_image_artifact, linux_binary_artifact])

    def getOutdir(self):
        return os.path.join('results',
                            self.gem5_name,
                            self.script_name,
                            self.linux_name,
                            self.disk_name,
                            *self.local_extra_params)

    def _getSerializable(self):
        """Returns a dictionary that can be used to recreate this object"""
        d = super(gem5RunFS, self)._getSerializable()
        d['linux_binary_artifact'] = self.linux_binary_artifact._id
        d['disk_image_artifact'] = self.disk_image_artifact._id
        return d

    @classmethod
    def loadFromDict(cls, d):
        return cls(d['gem5_binary'], d['run_script'],
                   artifact.Artifact(UUID(d['gem5_artifact'])),
                   artifact.Artifact(UUID(d['gem5_git_artifact'])),
                   artifact.Artifact(UUID(d['run_script_git_artifact'])),
                   d['linux_binary'], d['disk_image'],
                   artifact.Artifact(UUID(d['linux_binary_artifact'])),
                   artifact.Artifact(UUID(d['disk_image_artifact'])),
                  *d['local_extra_params'])


    def _getHash(self):
        to_hash = [self.gem5_artifact._id.bytes,  # UUID of gem5 binary
                   self.gem5_git_artifact._id.bytes, # UUID of gem5 git
                   self.run_script_git_artifact._id.bytes, # UUID of cur repo
                   self.linux_binary_artifact._id.bytes, # UUID of vmlinux
                   self.disk_image_artifact._id.bytes, # UUID of disk image
                   self.run_script.encode(), # Script we're running
                   ' '.join(self.local_extra_params).encode(),
                  ]

        return hashlib.md5(b''.join(to_hash)).hexdigest()



