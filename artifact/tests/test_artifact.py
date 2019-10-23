"""Tests for the Artifact object and associated functions"""

import hashlib
from os.path import exists
import unittest
from uuid import uuid4

from gem5art.artifact import artifact

class TestGit(unittest.TestCase):
    def test_keys(self):
        git = artifact.getGit('.')
        self.assertSetEqual(set(git.keys()), set(['origin', 'hash', 'name']),
                            "git keys wrong")
    
    def test_origin(self):
        git = artifact.getGit('.')
        self.assertTrue(git['origin'].endswith('gem5art'),
                        "Origin should end with gem5art")

class TestArtifact(unittest.TestCase):

    def setUp(self):
        self.artifact = artifact.Artifact({
            '_id': uuid4(),
            'name': 'test-name',
            'type': 'test-type',
            'documentation': "This is a long test documentation that has lots of words",
            'command': ['ls', '-l'],
            'path': '/',
            'hash': hashlib.md5().hexdigest(),
            'git': artifact.getGit('.'),
            'cwd': '/',
            'inputs': [],
        })

    def test_dirs(self):
        self.assertTrue(exists(self.artifact.cwd))
        self.assertTrue(exists(self.artifact.path))
        

if __name__ == '__main__':
    unittest.main()