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

"""Tests for the Artifact object and associated functions"""

import hashlib
from os.path import exists
import unittest
from uuid import uuid4

from gem5art import artifact

class TestGit(unittest.TestCase):
    def test_keys(self):
        git = artifact.artifact.getGit('.')
        self.assertSetEqual(set(git.keys()), set(['origin', 'hash', 'name']),
                            "git keys wrong")

    def test_origin(self):
        git = artifact.artifact.getGit('.')
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
            'git': artifact.artifact.getGit('.'),
            'cwd': '/',
            'inputs': [],
        })

    def test_dirs(self):
        self.assertTrue(exists(self.artifact.cwd))
        self.assertTrue(exists(self.artifact.path))

class TestArtifactSimilarity(unittest.TestCase):

    def setUp(self):
        self.artifactA = artifact.Artifact({
            '_id': uuid4(),
            'name': 'artifact-A',
            'type': 'type-A',
            'documentation': "This is a description of artifact A",
            'command': ['ls', '-l'],
            'path': '/',
            'hash': hashlib.md5().hexdigest(),
            'git': artifact.artifact.getGit('.'),
            'cwd': '/',
            'inputs': [],
        })

        self.artifactB = artifact.Artifact({
            '_id': uuid4(),
            'name': 'artifact-B',
            'type': 'type-B',
            'documentation': "This is a description of artifact B",
            'command': ['ls', '-l'],
            'path': '/',
            'hash': hashlib.md5().hexdigest(),
            'git': artifact.artifact.getGit('.'),
            'cwd': '/',
            'inputs': [],
        })

        self.artifactC = self.artifactA

    def test_not_same(self):
        self.assertTrue(self.artifactA != self.artifactB)
    def test_same(self):
        self.assertTrue(self.artifactA == self.artifactC)


if __name__ == '__main__':
    unittest.main()
