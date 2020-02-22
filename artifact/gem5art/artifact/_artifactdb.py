# -*- coding: utf-8 -*-
# Copyright (c) 2019 The Regents of the University of California
# All Rights Reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met: redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer;
# redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution;
# neither the name of the copyright holders nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# Authors: Jason Lowe-Power

from abc import ABC, abstractmethod

import gridfs # type: ignore
from pathlib import Path
from pymongo import MongoClient # type: ignore
from typing import Any, Dict, Iterable, Union, Type
from uuid import UUID

class ArtifactDB(ABC):
    """
    Abstract base class for all artifact DBs.
    """

    @abstractmethod
    def put(self, key: UUID, artifact: Dict[str,Union[str,UUID]]) -> None:
        """Insert the artifact into the database with the key"""
        pass

    @abstractmethod
    def upload(self, key: UUID, path: Path) -> None:
        """Upload the file at path to the database with _id of key"""
        pass

    @abstractmethod
    def __contains__(self, key: Union[UUID, str]) -> bool:
        """Key can be a UUID or a string. Returns true if item in DB"""
        pass

    @abstractmethod
    def get(self, key: Union[UUID,str]) -> Dict[str,str]:
        """Key can be a UUID or a string. Returns a dictionary to construct
        an artifact.
        """
        pass

    @abstractmethod
    def downloadFile(self, key: UUID, path: Path) -> None:
        """Download the file with the _id key to the path. Will overwrite the
        file if it currently exists."""
        pass

    def searchByName(self, name: str, limit: int) -> Iterable[Dict[str, Any]]:
        """Returns an iterable of all artifacts in the database that match
        some name. Note: Not all DB implementations will implement this
        function"""
        raise NotImplementedError()

    def searchByType(self, typ: str, limit: int) -> Iterable[Dict[str, Any]]:
        """Returns an iterable of all artifacts in the database that match
        some type. Note: Not all DB implementations will implement this
        function"""
        raise NotImplementedError()

    def searchByNameType(self, name: str, typ: str, limit: int) -> Iterable[Dict[str, Any]]:
        """Returns an iterable of all artifacts in the database that match
        some name and type. Note: Not all DB implementations will implement
        this function"""
        raise NotImplementedError()

    def searchByLikeNameType(self, name: str, typ: str, limit: int) -> Iterable[Dict[str, Any]]:
        """Returns an iterable of all artifacts in the database that match
        some type and a regex name. Note: Not all DB implementations will implement
        this function"""
        raise NotImplementedError()



class ArtifactMongoDB(ArtifactDB):
    """
    This is a mongodb database connector for storing Artifacts (as defined in
    artifact.py).

    This database stores the data in three collections:
    - artifacts: This stores the json serialized Artifact class
    - files and chunks: These two collections store the large files required
      for some artifacts. Within the files collection, the _id is the
      UUID of the artifact.
    """

    def __init__(self) -> None:
        # Note: Need "connect=False" so that we don't connect until the first
        # time we interact with the database. Required for the gem5 running
        # celery server
        self.db = MongoClient(connect=False).artifact_database
        self.artifacts = self.db.artifacts
        self.fs = gridfs.GridFSBucket(self.db, disable_md5=True)

    def put(self, key: UUID, artifact: Dict[str,Union[str,UUID]]) -> None:
        """Insert the artifact into the database with the key"""
        assert artifact['_id'] == key
        self.artifacts.insert_one(artifact)

    def upload(self, key: UUID, path: Path) -> None:
        """Upload the file at path to the database with _id of key"""
        with open(path, 'rb') as f:
            self.fs.upload_from_stream_with_id(key, str(path), f)

    def __contains__(self, key: Union[UUID, str]) -> bool:
        """Key can be a UUID or a string. Returns true if item in DB"""
        if isinstance(key, UUID):
            count = self.artifacts.count_documents({'_id': key}, limit = 1)
        else:
            # This is a hash. Count the number of matches
            count =  self.artifacts.count_documents({'hash': key}, limit = 1)

        return bool(count > 0)

    def get(self, key: Union[UUID,str]) -> Dict[str,str]:
        """Key can be a UUID or a string. Returns a dictionary to construct
        an artifact.
        """
        if isinstance(key, UUID):
            return self.artifacts.find_one({'_id': key}, limit = 1)
        else:
            # This is a hash.
            return self.artifacts.find_one({'hash': key}, limit = 1)

    def downloadFile(self, key: UUID, path: Path) -> None:
        """Download the file with the _id key to the path. Will overwrite the
        file if it currently exists."""
        with open(path, 'wb') as f:
            self.fs.download_to_stream(key, f)


    def searchByName(self, name: str, limit: int) -> Iterable[Dict[str, Any]]:
        """Returns an iterable of all artifacts in the database that match
        some name."""
        for d in self.artifacts.find({'name': name}, limit=limit):
            yield d

    def searchByType(self, typ: str, limit: int) -> Iterable[Dict[str, Any]]:
        """Returns an iterable of all artifacts in the database that match
        some type."""
        for d in self.artifacts.find({'type':typ}, limit=limit):
            yield d

    def searchByNameType(self, name: str, typ: str, limit: int) -> Iterable[Dict[str, Any]]:
        """Returns an iterable of all artifacts in the database that match
        some name and type."""
        for d in self.artifacts.find({'type':typ, 'name': name}, limit=limit):
            yield d

    def searchByLikeNameType(self, name: str, typ: str, limit: int) -> Iterable[Dict[str, Any]]:
        """Returns an iterable of all artifacts in the database that match
        some type and a regex name."""

        data = self.artifacts.find({'type':typ,
                                    'name': {'$regex': '{}'.format(name)}
                                   },
                                   limit=limit)
        for d in data:
            yield d

_db = None

def getDBConnection(typ: Type[ArtifactDB] = ArtifactMongoDB) -> ArtifactDB:
    """Returns the database connection

    Eventually, this should likely read from a config file to get the database
    information. However, for now, we'll use mongodb defaults
    """
    global _db

    if not _db:
        _db = typ()

    return _db
