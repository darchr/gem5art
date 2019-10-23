"""File contains the Artifact class and helper functions
"""

import hashlib
from inspect import cleandoc
import os
import subprocess
import time
import typing
from typing import Any, Dict, Iterator, List, Union
from uuid import UUID, uuid4

from . import getDBConnection


_db = getDBConnection()

def getHash(path: str) -> str:
    """
    Returns an md5 hash for the file in self.path.
    """
    BUF_SIZE = 65536
    md5 = hashlib.md5()
    with open(path, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data: break
            md5.update(data)

    return md5.hexdigest()

def getGit(path: str) -> Dict[str,str]:
    """
    Returns dictionary with origin, current commit, and repo name for the
    base repository for `path`.
    An exception is generated if the repo is dirty or doesn't exist
    """
    path = os.path.abspath(path)

    if os.path.isfile(path):
        path = os.path.dirname(path)

    command = ['git', 'status', '--porcelain', '--ignore-submodules',
                '--untracked-files=no']
    res = subprocess.run(command, stdout=subprocess.PIPE, cwd=path)
    if res.returncode != 0:
        raise Exception("git repo doesn't exist for {}".format(path))
    if res.stdout:
        raise Exception("git repo dirty for {}".format(path))

    command = ['git', 'remote', 'get-url', 'origin']
    origin = subprocess.check_output(command, cwd=path)

    command = ['git', 'log', '-n1', '--pretty=format:%H']
    hsh = subprocess.check_output(command, cwd=path)

    command = ['git', 'rev-parse', '--show-toplevel']
    name = subprocess.check_output(command, cwd=path)

    return {
        'origin': str(origin.strip(), 'utf-8'),
        'hash': str(hsh.strip(), 'utf-8'),
        'name': str(name.strip(), 'utf-8'),
    }

class Artifact:
    """
    A base artifact class.
    It holds following attributes of an artifact:

    1) name: name of the artifact
    2) command: bash command used to generate the artifact
    3) path: path of the location of the artifact
    4) time: time of creation of the artifact
    5) documentation: a string to describe the artifact
    6) ID: unique identifier of the artifact
    7) inputs: list of the input artifacts used to create this artifact stored
       as a list of uuids
    """

    _id: UUID
    name: str
    type: str
    documentation: str
    command: str
    path: str
    hash: str
    git: Dict[str,str]
    cwd: str
    inputs: List['Artifact']

    @classmethod
    def registerArtifact(cls,
                         command: str,
                         name: str,
                         cwd: str,
                         typ: str,
                         path: str,
                         documentation: str,
                         inputs: List['Artifact'] = []
                         ) -> 'Artifact':
        """Constructs a new artifact.

        This assume either it's not in the database or it is the exact same as
        when it was added to the database
        """

        # Dictionary with all of the kwargs for construction.
        data: Dict[str, Any] = {}

        data['name'] = name
        data['type'] = typ
        data['documentation'] = cleandoc(documentation)
        if len(data['documentation']) < 10: # 10 characters is arbitrary
            raise Exception(cleandoc("""Must provide longer documentation!
                This documentation is how your future data will remember what
                this artifact is and how it was created."""))

        data['command'] = cleandoc(command)

        data['path'] = path
        if os.path.isfile(path):
            data['hash'] = getHash(path)
            data['git'] = {}
        elif os.path.isdir(path):
            data['git'] = getGit(path)
            data['hash'] = data['git']['hash']
        else:
            raise Exception("Path {} doesn't exist".format(path))

        data['cwd'] = cwd
        if not os.path.exists(cwd):
            raise Exception("cwd {} doesn't exits.".format(cwd))

        data['inputs'] = [i._id for i in inputs]

        if data['hash'] in _db:
            old_artifact = Artifact(_db.get(data['hash']))
            data['_id'] = old_artifact._id

            # Now that we have a complete object, construct it
            self = cls(data)
            if old_artifact != self:
                print(f"Current: {vars(self)}")
                print(f"From DB: {vars(old_artifact)}")
                raise Exception("Found matching hash in DB, but object "
                    "doesn't match. Use the UUID constructor instead.")
        else:
            data['_id'] = uuid4()

            # Now that we have a complete object, construct it
            self = cls(data)
            _db.put(self._id, self._getSerializable())

            # Upload the file if there is one.
            if os.path.isfile(self.path):
                _db.upload(self._id, self.path)

        return self

    def __init__(self, other: Union[str, UUID, Dict[str, Any]]) -> None:
        """Constructs the object from the database based on a UUID or
        dictionary from the database
        """
        if isinstance(other, str):
            other = UUID(other)
        if isinstance(other, UUID):
            other = _db.get(other)

        if not other:
            raise Exception("Cannot construct artifact")

        assert isinstance(other['_id'], UUID)
        self._id = other['_id']
        self.name = other['name']
        self.type = other['type']
        self.documentation = other['documentation']
        self.command = other['command']
        self.path = other['path']
        self.hash = other['hash']
        assert isinstance(other['git'], dict)
        self.git = other['git']
        self.cwd = other['cwd']
        self.inputs = [Artifact(i) for i in other['inputs']]

    def __str__(self) -> str:
        inputs = ', '.join([i.name+':'+str(i._id) for i in self.inputs])
        return "\n    ".join([self.name, f'id: {self._id}',
                              f'type: {self.type}', f'path: {self.path}',
                              f'inputs: {inputs}',
                              self.documentation])

    def __repr__(self) -> str:
        return vars(self).__repr__()

    def _getSerializable(self) -> Dict[str, Union[str, UUID]]:
        data = vars(self)
        data['inputs'] = [input._id for input in self.inputs]
        return data

    def __eq__(self, other: object) -> bool:
        """checks if two artifacts are the same.

        Two artifacts are the same if they have the same UUID and the same
        hash. We emit a warning if other fields are different. If other fields
        are different and the hash is the same, this is suggestive that the
        user is doing something wrong.
        """
        if not isinstance(other, Artifact):
            return NotImplemented

        if self.hash != other.hash or self._id != other._id:
            return False

        if self.name != other.name:
            print(f"WARNING: name mismatch for {self.name}! "
                  f"{self.name} != {other.name}")
        if self.documentation != other.documentation:
            print(f"WARNING: documentation mismatch for {self.name}! "
                  f"{self.documentation} != {other.documentation}")
        if self.command != other.command:
            print(f"WARNING: command mismatch for {self.name}! "
                  f"{self.command} != {other.command}")
        if self.path != other.path:
            print(f"WARNING: path mismatch for {self.name}! "
                  f"{self.path} != {other.path}")
        if self.cwd != other.cwd:
            print(f"WARNING: cwd mismatch for {self.name}! "
                  f"{self.cwd} != {other.cwd}")
        if self.git != other.git:
            print(f"WARNING: git mismatch for {self.name}! "
                  f"{self.git} != {other.git}")
        mismatch = set(self.inputs).symmetric_difference(other.inputs)
        if mismatch:
            print(f"WARNING: input mismatch for {self.name}! {mismatch}")

        return True

    def __hash__(self) -> int:
        return self._id.int

def _getByType(typ: str, limit: int) -> Iterator[Artifact]:
    data = _db.artifacts.find({'type':typ}, limit=limit)

    for d in data:
        yield Artifact(d)

def getDiskImages(limit: int = 0) -> Iterator[Artifact]:
    """Returns a generator of disk images (type = disk image).

    Limit specifies the maximum number of results to return.
    """

    return _getByType('disk image', limit)

def getgem5Binaries(limit: int = 0) -> Iterator[Artifact]:
    """Returns a generator of gem5 binaries (type = gem5 binary).

    Limit specifies the maximum number of results to return.
    """

    return _getByType('gem5 binary', limit)


def getLinuxBinaries(limit: int = 0) -> Iterator[Artifact]:
    """Returns a generator of Linux kernel binaries (type = kernel).

    Limit specifies the maximum number of results to return.
    """

    return _getByType('kernel', limit)

def getByName(name: str, limit: int = 0) -> Iterator[Artifact]:
    """Returns all objects mathching `name` in database.

    Limit specifies the maximum number of results to return.
    """
    data = _db.artifacts.find({'name': name}, limit=limit)

    for d in data:
        yield Artifact(d)
