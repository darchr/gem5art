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
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union
from uuid import UUID, uuid4
import zipfile

from gem5art import artifact
from gem5art.artifact.artifact import Artifact

_db: artifact.ArtifactDB = artifact.getDBConnection()

class gem5Run:
    """
    This class holds all of the info required to run gem5.
    """

    _id: UUID
    hash: str
    type: str
    gem5_binary: str
    run_script: str
    gem5_artifact: Artifact
    gem5_git_artifact: Artifact
    run_script_git_artifact: Artifact
    params: Tuple[str, ...]
    timeout: int

    gem5_name: str
    script_name: str
    linux_name: str
    disk_name: str
    string: str
    relative_outdir: str
    outdir: str

    linux_binary: str
    disk_image: str
    linux_binary_artifact: Artifact
    disk_image_artifact: Artifact

    command: List[str]

    running: bool
    enqueue_time: float
    start_time: float
    end_time: float
    return_code: int
    kill_reason: str
    status: str
    pid: int
    task_id: Any

    results: Optional[Artifact]
    artifacts: List[Artifact]

    @classmethod
    def _create(cls,
                gem5_binary: str,
                run_script: str,
                gem5_artifact: Artifact,
                gem5_git_artifact: Artifact,
                run_script_git_artifact: Artifact,
                params: Tuple[str, ...],
                timeout: int) -> 'gem5Run':
        """
        Shared code between SE and FS when creating a run object.
        """
        run = cls()
        run.gem5_binary = gem5_binary
        run.run_script = run_script
        run.gem5_artifact = gem5_artifact
        run.gem5_git_artifact = gem5_git_artifact
        run.run_script_git_artifact = run_script_git_artifact
        run.params = params
        run.timeout = timeout

        run._id = uuid4()

        # Assumes **/<gem5_name>/gem5.<anything>
        run.gem5_name = os.path.split(os.path.split(run.gem5_binary)[0])[1]
        # Assumes **/<script_name>.py
        run.script_name = os.path.split(run.run_script)[1].split('.')[0]

        # Info about the actual run
        run.running = False
        run.enqueue_time = time.time()
        run.start_time = 0.0
        run.end_time = 0.0
        run.return_code = 0
        run.kill_reason = ''
        run.status = "Created"
        run.pid = 0
        run.task_id = None

        # Initially, there are no results
        run.results = None

        return run

    @classmethod
    def createSERun(cls,
                    gem5_binary: str,
                    run_script: str,
                    gem5_artifact: Artifact,
                    gem5_git_artifact: Artifact,
                    run_script_git_artifact: Artifact,
                    *params: str,
                    timeout: int = 60*15) -> 'gem5Run':
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

        run = cls._create(gem5_binary, run_script, gem5_artifact,
                          gem5_git_artifact, run_script_git_artifact, params,
                          timeout)

        run.artifacts = [gem5_artifact, gem5_git_artifact,
                         run_script_git_artifact]

        run.string = f"{run.gem5_name} {run.script_name}"
        run.string += ' '.join(run.params)

        # Constructs the output directory from the gem5 build opts (e.g., X86,
        # ARM, MOESI_hammer), the gem5 run script, and the extra parameters.
        # The relative path is useful for printing
        run.relative_outdir = os.path.join('results',
                                           run.gem5_name,
                                           run.script_name,
                                           *run.params)

        run.outdir = os.path.abspath(run.outdir)
        # Make the directory if it doesn't exist
        os.makedirs(run.outdir, exist_ok=True)

        run.command = [
            run.gem5_binary,
            '-re', '--outdir={}'.format(run.outdir),
            run.run_script]
        run.command += list(params)

        run.hash = run._getHash()
        run.type = 'gem5 run'

        run.dumpJson('info.json')

        return run

    @classmethod
    def createFSRun(cls,
                    gem5_binary: str,
                    run_script: str,
                    gem5_artifact: Artifact,
                    gem5_git_artifact: Artifact,
                    run_script_git_artifact: Artifact,
                    linux_binary: str,
                    disk_image: str,
                    linux_binary_artifact: Artifact,
                    disk_image_artifact: Artifact,
                    *params: str,
                    timeout: int = 60*15) -> 'gem5Run':
        """
        gem5_binary and run_script are the paths to the binary to run
        and the script to pass to gem5.
        The linux_binary is the kernel to run and the disk_image is the path
        to the disk image to use.
        Further parameters can be passed via extra arguments. These
        parameters will be passed in order to the gem5 run script.
        """

        run = cls._create(gem5_binary, run_script, gem5_artifact,
                          gem5_git_artifact, run_script_git_artifact, params,
                          timeout)
        run.linux_binary = linux_binary
        run.disk_image = disk_image
        run.linux_binary_artifact = linux_binary_artifact
        run.disk_image_artifact = disk_image_artifact

        # Assumes **/<linux_name>
        run.linux_name = os.path.split(run.linux_binary)[1]
        # Assumes **/<disk_name>
        run.disk_name = os.path.split(run.disk_image)[1]

        run.artifacts = [gem5_artifact, gem5_git_artifact,
                         run_script_git_artifact, linux_binary_artifact,
                         disk_image_artifact]

        run.string = f"{run.gem5_name} {run.script_name} "
        run.string += f"{run.linux_name} {run.disk_name} "
        run.string += ' '.join(run.params)

        # Constructs the output directory from the gem5 build opts (e.g., X86,
        # ARM, MOESI_hammer), the gem5 run script, and the extra parameters.
        # The relative path is useful for printing
        run.relative_outdir = os.path.join('results',
                                           run.gem5_name,
                                           run.script_name,
                                           run.linux_name,
                                           run.disk_name,
                                           *run.params)

        run.outdir = os.path.abspath(run.relative_outdir)
        # Make the directory if it doesn't exist
        os.makedirs(run.outdir, exist_ok=True)

        run.command = [
            run.gem5_binary,
            '-re', '--outdir={}'.format(run.outdir),
            run.run_script, run.linux_binary,
            run.disk_image]
        run.command += list(params)

        run.hash = run._getHash()
        run.type = 'gem5 run fs'

        run.dumpJson('info.json')

        return run

    @classmethod
    def loadJson(cls, filename: str) -> 'gem5Run':
        with open(filename) as f:
            d = json.load(f)
            # Convert string version of UUID to UUID object
            for k,v in d.iteritems():
                if k.endswith('_artifact'):
                    d[k] = UUID(v)
            d['_id'] = UUID(d['_id'])
        try:
            return cls.loadFromDict(d)
        except KeyError:
            print("Incompatible json file: {}!".format(filename))
            raise

    @classmethod
    def loadFromDict(cls, d: Dict[str, Union[str, UUID]]) -> 'gem5Run':
        """Returns new gem5Run instance from the dictionary of values in d"""
        run = cls()
        run.artifacts = []
        for k,v in d.items():
            if isinstance(v, UUID) and k != '_id':
                a = Artifact(v)
                setattr(run, k, a)
                run.artifacts.append(a)
            else:
                setattr(run, k, v)
        return run

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
        return str(self._getSerializable())

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

        Note: All artifacts are converted to a UUID instead of an Artifact.
        """
        # Grab all of the member variables
        d = vars(self).copy()

        # Remove list of artifacts
        del d['artifacts']

        # Replace the artifacts with their UUIDs
        for k,v in d.items():
            if isinstance(v, Artifact):
                d[k] = v._id

        return d

    def _getHash(self) -> str:
        """Return a single value that uniquely identifies this run

        To uniquely identify this run, the gem5 binary, gem5 scripts, and
        parameters should all match. Thus, let's make a single hash out of the
        artifacts + the runscript + parameters
        """
        to_hash = [art._id.bytes for art in self.artifacts]
        to_hash.append(self.run_script.encode())
        to_hash.append(' '.join(self.params).encode())

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
                       os.listdir(self.outdir))

        with zipfile.ZipFile(os.path.join(self.outdir, 'results.zip'), 'w',
                             zipfile.ZIP_DEFLATED) as zipf:
            for f in files:
                zipf.write(os.path.join(self.outdir, f))

        self.results = Artifact.registerArtifact(
                command = f'zip results.zip -r {self.outdir}',
                name = 'results',
                typ = 'directory',
                path =  os.path.join(self.outdir, 'results.zip'),
                cwd = './',
                documentation = 'Compressed version of the results directory'
        )

    def __str__(self) -> str:
        return  self.string + ' -> ' + self.status

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
        yield gem5Run.loadFromDict(run)
