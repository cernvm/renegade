#!/usr/bin/python
#
# Copyright 2012 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for the project commands."""



import path_initializer
path_initializer.InitSysPath()

import copy
import os
import tempfile


import gflags as flags
import unittest

from gcutil_lib import gcutil_errors
from gcutil_lib import gcutil_unittest
from gcutil_lib import mock_api
from gcutil_lib import old_mock_api
from gcutil_lib import project_cmds

FLAGS = flags.FLAGS


class ProjectCmdsTest(gcutil_unittest.GcutilTestCase):

  def setUp(self):
    self.mock, self.api = mock_api.CreateApi(self.version)

  def testGetProjectWithFullyQualifiedPathGeneratesCorrectRequest(self):
    project = 'cool-project'

    command = self._CreateAndInitializeCommand(project_cmds.GetProject,
                                               'getproject',
                                               self.version)

    qualified_project = 'projects/%s' % project

    project_call = self.mock.Respond('compute.projects.get', {})
    command.Handle(qualified_project)

    request = project_call.GetRequest()

    self.assertEquals(project, request.parameters['project'])


class OldProjectCmdsTest(unittest.TestCase):
  def testGetProjectGeneratesCorrectRequest(self):
    flag_values = copy.deepcopy(FLAGS)

    command = project_cmds.GetProject('getproject', flag_values)

    expected_project = 'test_project'
    flag_values.project = expected_project

    command.SetFlags(flag_values)
    command.SetApi(old_mock_api.CreateMockApi())
    command._InitializeContextParser()

    result = command.Handle()

    self.assertEqual(result['project'], expected_project)

  def testSetCommonInstanceMetadataGeneratesCorrectRequest(self):

    class SetCommonInstanceMetadata(object):

      def __call__(self, project, body):
        self._project = project
        self._body = body
        return self

      def execute(self):
        return {'project': self._project, 'body': self._body}

    flag_values = copy.deepcopy(FLAGS)
    command = project_cmds.SetCommonInstanceMetadata(
        'setcommoninstancemetadata', flag_values)

    expected_project = 'test_project'
    flag_values.project = expected_project
    flag_values.service_version = 'v1beta15'
    handle, path = tempfile.mkstemp()
    try:
      with os.fdopen(handle, 'w') as metadata_file:
        metadata_file.write('foo:bar')
        metadata_file.flush()

        flag_values.metadata_from_file = ['sshKeys:%s' % path]

        command.SetFlags(flag_values)
        command.SetApi(old_mock_api.CreateMockApi())
        command._InitializeContextParser()
        command.api.projects.get = old_mock_api.CommandExecutor(
            {'commonInstanceMetadata': [{'key': 'sshKeys', 'value': ''}]})
        command.api.projects.setCommonInstanceMetadata = (
            SetCommonInstanceMetadata())

        result = command.Handle()
        self.assertEquals(expected_project, result['project'])
        self.assertEquals(
            {'kind': 'compute#metadata',
             'items': [{'key': 'sshKeys', 'value': 'foo:bar'}]},
            result['body'])
    finally:
      os.remove(path)

  def testSetCommonInstanceMetadataChecksForOverwrites(self):
    flag_values = copy.deepcopy(FLAGS)
    command = project_cmds.SetCommonInstanceMetadata(
        'setcommoninstancemetadata', flag_values)

    expected_project = 'test_project'
    flag_values.project = expected_project
    flag_values.service_version = 'v1beta15'
    command.SetFlags(flag_values)
    command.SetApi(old_mock_api.CreateMockApi())
    command._InitializeContextParser()
    command.api.projects.get = old_mock_api.CommandExecutor(
        {'commonInstanceMetadata': [{'key': 'sshKeys', 'value': 'foo:bar'}]})

    self.assertRaises(gcutil_errors.CommandError, command.Handle)

if __name__ == '__main__':
  unittest.main(testLoader=gcutil_unittest.GcutilLoader())
