
import gridfs
from pymongo import MongoClient
from uuid import UUID

class ArtifactDB:
    """
    This is a mongodb database connector for storing Artifacts (as defined in
    artifact.py).

    This database stores the data in three collections:
    - artifacts: This stores the json serialized Artifact class
    - files and chunks: These two collections store the large files required
      for some artifacts. Within the files collection, the _id is the
      UUID of the artifact.
    """

    def __init__(self):
        # Note: Need "connect=False" so that we don't connect until the first
        # time we interact with the database. Required for the gem5 running
        # celery server
        self.db = MongoClient(connect=False).artifact_database
        self.artifacts = self.db.artifacts
        self.fs = gridfs.GridFSBucket(self.db, disable_md5=True)

    def put(self, key, artifact):
        # Insert the artifact into the database
        if type(artifact) is dict:
            assert(artifact['_id'] == key)
            self.artifacts.insert_one(artifact)
        else:
            assert(artifact._id == key)
            self.artifacts.insert_one(vars(artifact))

    def upload(self, key, path):
        """Upload the file at path to the database with _id of key"""
        with open(path, 'rb') as f:
            self.fs.upload_from_stream_with_id(key, path, f)

    def __contains__(self, key):
        """Key can be a UUID or a string. Returns true if item in DB"""
        if isinstance(key, UUID):
            return self.artifacts.count_documents({'_id': key}, limit = 1) > 0
        else:
            # This is a hash. Count the number of matches
            return self.artifacts.count_documents({'hash': key}, limit = 1) > 0

    def get(self, key):
        """Key can be a UUID or a string. Returns a dictionary to construct
        an artifact.
        """
        if isinstance(key, UUID):
            return self.artifacts.find_one({'_id': key}, limit = 1)
        else:
            # This is a hash.
            return self.artifacts.find_one({'hash': key}, limit = 1)

    def downloadFile(self, key, path):
        """Download the file with the _id key to the path. Will overwrite the
        file if it currently exists."""
        with open(path, 'wb') as f:
            self.fs.download_to_stream(key, f)
