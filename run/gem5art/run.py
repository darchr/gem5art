"""
This file defines a gem5Run object which contains all information needed to
run a single gem5 test.

This class works closely with the artifact module to ensure that the gem5
experiment is reproducible and the output is saved to the database.
"""

import hashlib
import json
import os
import signal
import subprocess
import time
from typing import Any, Dict, Iterable, Optional, Union
from uuid import UUID, uuid4
import zipfile

from gem5art import artifact
from gem5art.artifact.artifact import Artifact

_db: artifact.ArtifactDB = artifact.getDBConnection()

class gem5Run:
    """
    This class holds all of the info required to run gem5. If you want to also
    track other information (e.g., the binary you are running in SE mode or
    the disk image/kernel in FS mode) you should extend this class.
    """

    def __init__(self,
                 gem5_binary: str,
                 run_script: str,
                 gem5_artifact: Artifact,
                 gem5_git_artifact: Artifact,
                 run_script_git_artifact: Artifact,
                 *params: str,
                 timeout: int = 60*15) -> None:
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
        self._id = uuid4()
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
        self.start_time = 0.0
        self.end_time = 0.0

        self.return_code = 0
        self.kill_reason = ''
        self.status = "Created"

        self.pid = 0
        self.task_id = None

        # Initially, there are no results
        self.results: Optional[Artifact] = None

        self.hash = self._getHash()

        self.dumpJson('info.json')

    def checkArtifacts(self) -> bool:
        """Checks to make sure all of the artifacts are up to date

        This should happen just before running gem5. This function will return
        False if the artifacts don't check and true if they are all the same.
        For the git repos, this checks the git hash, for binary artifacts this
        checks the md5 hash.
        """
        for v in self.artifacts:
            if v.type == 'git repo':
                new = artifact.artifact.getGit(v.path)['hash']
                old = v.git['hash']
            else:
                new = artifact.artifact.getHash(v.path)
                old = v.hash

            if new != v.hash:
                status = f"Failed artifact check for {v.path}"
                return False

        return True

    def __repr__(self) -> str:
        return repr(self.__dict__)

    def getOutdir(self) -> str:
        """
        Constructs the output directory from the gem5 build opts (e.g., X86,
        ARM, MOESI_hammer), the gem5 run script, and the extra parameters.
        """
        return os.path.join('results',
                            self.gem5_name,
                            self.script_name,
                            *self.extra_params)

    def checkKernelPanic(self) -> bool:
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

    def _getSerializable(self) -> Dict[str, Union[str, UUID]]:
        """Returns a dictionary that can be used to recreate this object

        Note: All artifacts must be manually converted to a UUID instead of
        an artifact class.
        """
        # Grab all of the member variables
        d = vars(self).copy()
        # Replace the artifacts with their UUIDs
        d['gem5_artifact'] = self.gem5_artifact._id
        d['gem5_git_artifact'] = self.gem5_git_artifact._id
        d['run_script_git_artifact'] = self.run_script_git_artifact._id
        if d['results']: d['results'] = self.results._id
        d['type'] = 'gem5 run'
        # Remove list of artifacts
        del d['artifacts']

        return d

    def _getHash(self) -> str:
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
    def _convertForJson(cls, d: Dict[str, Any]) -> Dict[str, str]:
        """Converts UUID objects to strings for json compatibility"""
        for k,v in d.items():
            if isinstance(v, UUID):
                d[k] = str(v)
        return d

    def dumpJson(self, filename: str) -> None:
        """Dump all info into a json file"""
        d = self._convertForJson(self._getSerializable())
        with open(os.path.join(self.outdir, filename), 'w') as f:
            json.dump(d, f)

    def dumpsJson(self) -> str:
        """Like dumpJson except returns string"""
        d = self._convertForJson(self._getSerializable())
        return json.dumps(d)

    @classmethod
    def loadJson(cls, filename: str) -> Artifact:
        with open(filename) as f:
            d = json.load(f)
            for k,v in d.iteritems():
                # Convert string version of UUID to UUID object
                if k.endswith('_artifact'):
                    d[k] = UUID(v)
        try:
            return cls.loadFromDict(d)
        except KeyError:
            print("Incompatible json file: {}!".format(filename))
            raise

    @classmethod
    def loadFromDict(cls, d: Dict[str, str]) -> 'gem5Run':
        """Returns new gem5Run instance from the dictionary of values in d"""
        return cls(d['gem5_binary'], d['run_script'],
                   artifact.Artifact(d['gem5_artifact']),
                   artifact.Artifact(d['gem5_git_artifact']),
                   artifact.Artifact(d['run_script_git_artifact']),
                  *d['extra_params'], timeout = int(d['timeout']))

    def run(self, task: Any = None) -> None:
        """Actually run the test.

        Calls Popen with the command to fork a new process.
        Then, this function polls the process every 5 seconds to check if it
        has finished or not. Each time it checks, it dumps the json info so
        other applications can poll those files.
        task is the celery task that is running this gem5 instance.
        """
        # Check if the run is already in the database
        if self.hash in _db:
            print(f"Error: Have already run {self.command}. Exiting!")
            return

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

        self.saveResults()

        # Store current gem5 run in the database
        _db.put(self._id, self._getSerializable())

    def saveResults(self) -> None:
        """Zip up the output directory and store the results in the database.
        """
        files = filter(lambda f: f != 'results.zip',
                       os.listdir(self.getOutdir()))

        with zipfile.ZipFile(os.path.join(self.outdir, 'results.zip'), 'w',
                             zipfile.ZIP_DEFLATED) as zipf:
            for f in files:
                zipf.write(os.path.join(self.getOutdir(), f))

        self.results = Artifact.registerArtifact(
                command = f'zip results.zip -r {self.getOutdir()}',
                name = 'results',
                typ = 'directory',
                path =  os.path.join(self.getOutdir(), 'results.zip'),
                cwd = './',
                documentation = 'Compressed version of the results directory'
        )

    def __str__(self) -> str:
        gem5_info = f"{self.gem5_name} {self.script_name}"
        params = ' '.join(self.extra_params)
        return  gem5_info + ' ' + params + ' -> ' + self.status

class gem5RunFS(gem5Run):

    def __init__(self,
                 gem5_binary: str,
                 run_script: str,
                 gem5_artifact: Artifact,
                 gem5_git_artifact: Artifact,
                 run_script_git_artifact: Artifact,
                 linux_binary: str,
                 disk_image: str,
                 linux_binary_artifact: Artifact,
                 disk_image_artifact: Artifact,
                *params: str) -> None:
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

    def getOutdir(self) -> str:
        return os.path.join('results',
                            self.gem5_name,
                            self.script_name,
                            self.linux_name,
                            self.disk_name,
                            *self.local_extra_params)

    def _getSerializable(self) -> Dict[str, Union[str, UUID]]:
        d = super(gem5RunFS, self)._getSerializable()
        d['linux_binary_artifact'] = self.linux_binary_artifact._id
        d['disk_image_artifact'] = self.disk_image_artifact._id
        d['type'] = 'gem5 run fs'
        return d

    @classmethod
    def loadFromDict(cls, d: Dict[str,str]) -> 'gem5RunFS':
        return cls(d['gem5_binary'], d['run_script'],
                   artifact.Artifact(d['gem5_artifact']),
                   artifact.Artifact(d['gem5_git_artifact']),
                   artifact.Artifact(d['run_script_git_artifact']),
                   d['linux_binary'], d['disk_image'],
                   artifact.Artifact(d['linux_binary_artifact']),
                   artifact.Artifact(d['disk_image_artifact']),
                  *d['local_extra_params'])


    def _getHash(self) -> str:
        to_hash = [self.gem5_artifact._id.bytes,  # UUID of gem5 binary
                   self.gem5_git_artifact._id.bytes, # UUID of gem5 git
                   self.run_script_git_artifact._id.bytes, # UUID of cur repo
                   self.linux_binary_artifact._id.bytes, # UUID of vmlinux
                   self.disk_image_artifact._id.bytes, # UUID of disk image
                   self.run_script.encode(), # Script we're running
                   ' '.join(self.local_extra_params).encode(),
                  ]

        return hashlib.md5(b''.join(to_hash)).hexdigest()

    def __str__(self) -> str:
        gem5_info = f"{self.gem5_name} {self.script_name}"
        fs_info = f"{self.linux_name} {self.disk_name}"
        params = ' '.join(self.local_extra_params)
        return  gem5_info + ' ' + fs_info + ' ' + params + ' -> ' + self.status

def getRuns(fs_only: bool = False, limit: int = 0) -> Iterable[gem5Run]:
    """Returns a generator of gem5Run objects.

    If fs_only is True, then only full system runs will be returned.
    Limit specifies the maximum number of runs to return.
    """

    if not fs_only:
        runs = _db.artifacts.find({'type':'gem5 run'}, limit=limit)
        for run in runs:
            yield gem5Run.loadFromDict(run)

    fsruns = _db.artifacts.find({'type':'gem5 run fs'}, limit=limit)
    for run in fsruns:
        yield gem5RunFS.loadFromDict(run)
