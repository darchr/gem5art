
from .artifactdb import ArtifactDB

import hashlib
from inspect import cleandoc
import os
from pymongo import MongoClient
import subprocess
import time
from uuid import UUID, uuid4


_db = ArtifactDB()

def getHash(path):
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

def getGit(path):
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

    @classmethod
    def registerArtifact(cls, command, name, cwd, typ, path, documentation,
                         inputs=[]):
        """Constructs a new artifact.

        This assume either it's not in the database or it is the exact same as
        when it was added to the database
        """

        # Dictionary with all of the kwargs for construction.
        self = {}

        self['name'] = name
        self['type'] = typ
        self['documentation'] = cleandoc(documentation)
        if len(self['documentation']) < 10: # 10 characters is arbitrary
            raise Exception(cleandoc("""Must provide longer documentation!
                This documentation is how your future self will remember what
                this artifact is and how it was created."""))

        self['command'] = cleandoc(command)

        self['path'] = path
        if os.path.isfile(path):
            self['hash'] = getHash(path)
            self['git'] = None
        elif os.path.isdir(path):
            self['git'] = getGit(path)
            self['hash'] = self['git']['hash']
        else:
            raise Exception("Path {} doesn't exist".format(path))

        self['cwd'] = cwd
        if not os.path.exists(cwd):
            raise Exception("cwd {} doesn't exits.".format(cwd))

        self['inputs'] = [i._id for i in inputs]

        if self['hash'] in _db:
            old_artifact = Artifact(_db.get(self['hash']))
            self['_id'] = old_artifact._id

            # Now that we have a complete object, construct it
            self = cls(self)
            if old_artifact != self:
                print(f"Current: {vars(self)}")
                print(f"From DB: {vars(old_artifact)}")
                raise Exception("Found matching hash in DB, but object "
                    "doesn't match. Use the UUID constructor instead.")
        else:
            self['_id'] = uuid4()

            # Now that we have a complete object, construct it
            self = cls(self)
            _db.put(self._id, self)

            # Upload the file if there is one.
            if os.path.isfile(self.path):
                _db.upload(self._id, self.path)

        return self

    def __init__(self, other):
        """Constructs the object from the database based on a UUID or
        dictionary from the database
        """
        if isinstance(other, str):
            other = UUID(other)
        if isinstance(other, UUID):
            other = _db.get(other)

        if not other:
            raise Exception("Cannot construct artifact")

        self._id = other['_id']
        self.name = other['name']
        self.type = other['type']
        self.documentation = other['documentation']
        self.command = other['command']
        self.path = other['path']
        self.hash = other['hash']
        self.git = other['git']
        self.cwd = other['cwd']
        self.inputs = other['inputs']

    def __repr__(self):
        return "\n    ".join([self.name, f'id: {self._id}',
                              f'type: {self.type}', f'path: {self.path}',
                              f'inputs: {self.inputs}',
                              self.documentation])

    def __eq__(self, other):
        """checks if two artifacts are the same.

        Two artifacts are the same if they have the same UUID and the same
        hash. We emit a warning if other fields are different. If other fields
        are different and the hash is the same, this is suggestive that the
        user is doing something wrong.
        """

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

def _getByType(typ, limit):
    data = _db.artifacts.find({'type':typ}, limit=limit)

    for d in data:
        yield Artifact(d)

def getDiskImages(limit = 0):
    """Returns a generator of disk images (type = disk image).

    Limit specifies the maximum number of results to return.
    """

    return _getByType('disk image', limit)

def getgem5Binaries(limit = 0):
    """Returns a generator of gem5 binaries (type = gem5 binary).

    Limit specifies the maximum number of results to return.
    """

    return _getByType('gem5 binary', limit)


def getLinuxBinaries(limit = 0):
    """Returns a generator of Linux kernel binaries (type = kernel).

    Limit specifies the maximum number of results to return.
    """

    return _getByType('kernel', limit)

def getByName(name, limit = 0):
    """Returns all objects mathching `name` in database.

    Limit specifies the maximum number of results to return.
    """
    data = _db.artifacts.find({'name': name}, limit=limit)

    for d in data:
        yield Artifact(d)
