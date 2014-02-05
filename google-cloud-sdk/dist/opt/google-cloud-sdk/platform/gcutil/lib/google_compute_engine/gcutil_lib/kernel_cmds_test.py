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

"""Unit tests for the kernel commands."""



import path_initializer
path_initializer.InitSysPath()

import copy

import gflags as flags
import unittest

from gcutil_lib import command_base
from gcutil_lib import gcutil_unittest
from gcutil_lib import kernel_cmds
from gcutil_lib import mock_api
from gcutil_lib import old_mock_api

FLAGS = flags.FLAGS


class KernelCmdsTest(gcutil_unittest.GcutilTestCase):
  _SUPPORTED_API_VERSIONS = ('v1beta15', 'v1beta16')

  def setUp(self):
    self.mock, self.api = mock_api.CreateApi(self.version)

  def testGetKernelGeneratesCorrectRequest(self):
    expected_project = 'test_project'
    expected_kernel = 'test_kernel'

    set_flags = {
        'project': expected_project
        }

    command = self._CreateAndInitializeCommand(
        kernel_cmds.GetKernel, 'getKernel', self.version, set_flags)

    kernelcall = self.mock.Respond('compute.kernels.get', {})

    command.Handle(expected_kernel)

    request = kernelcall.GetRequest()

    self.assertEqual(request.parameters['project'], expected_project)
    self.assertEqual(request.parameters['kernel'], expected_kernel)

  def testFullyQualifiedKernelGeneratesCorrectRequest(self):
    expected_project = 'test_project'
    expected_kernel = 'test_kernel'

    set_flags = {
        'project': 'wrong_project'
        }

    command = self._CreateAndInitializeCommand(
        kernel_cmds.GetKernel, 'getKernel', self.version, set_flags)

    qualified_path = command.NormalizeGlobalResourceName(expected_project,
                                                         'kernels',
                                                         expected_kernel)

    kernelcall = self.mock.Respond('compute.kernels.get', {})

    command.Handle(qualified_path)
    request = kernelcall.GetRequest()

    self.assertEqual(request.parameters['project'], expected_project)
    self.assertEqual(request.parameters['kernel'], expected_kernel)


class OldKernelCmdsTest(unittest.TestCase):

  def testNewestKernelsFilter(self):
    flag_values = copy.deepcopy(FLAGS)
    command = kernel_cmds.ListKernels('listkernels', flag_values)
    command.SetFlags(flag_values)

    def KernelSelfLink(name):
      return ('https://www.googleapis.com/compute/v1beta15/projects/'
              'google.com:myproject/global/kernels/%s') % name

    kernels = [
        {'selfLink': KernelSelfLink('versionlesskernel1')},
        {'selfLink': KernelSelfLink('kernel-v20130408')},
        {'selfLink': KernelSelfLink('kernel-v20130409')},
        {'selfLink': KernelSelfLink('kernel-v20130410')},
        {'selfLink': KernelSelfLink('kernel-x20130410')},
        {'selfLink': KernelSelfLink('kernel-x20130411')},
    ]

    flag_values.old_kernels = False
    validate = command_base.NewestKernelsFilter(flag_values, kernels)
    self.assertEqual(3, len(validate))
    self.assertEqual(
        KernelSelfLink('versionlesskernel1'), validate[0]['selfLink'])
    self.assertEqual(
        KernelSelfLink('kernel-v20130410'), validate[1]['selfLink'])
    self.assertEqual(
        KernelSelfLink('kernel-x20130411'), validate[2]['selfLink'])

    flag_values.old_kernels = True
    validate = command_base.NewestKernelsFilter(flag_values, kernels)
    self.assertEqual(6, len(validate))
    for i in range(len(kernels)):
      self.assertEqual(kernels[i]['selfLink'], validate[i]['selfLink'])

  def testPromptForKernels(self):
    flag_values = copy.deepcopy(FLAGS)
    flag_values.project = 'myproject'
    command = kernel_cmds.ListKernels('addkernel', flag_values)
    command.SetFlags(flag_values)

    class MockListApi(object):
      def __init__(self):
        self.projects = set()
        self.calls = 0

      # pylint: disable=redefined-builtin
      # pylint: disable=unused-argument
      def list(
          self, project=None, maxResults=None, filter=None, pageToken=None):
        self.projects.add(project)
        self.calls += 1
        return old_mock_api.MockRequest({'items': []})

    list_api = MockListApi()
    kernel = command._presenter.PromptForKernel(list_api)

    self.assertEquals(None, kernel)
    expected_projects = command_base.STANDARD_KERNEL_PROJECTS + ['myproject']
    self.assertEquals(len(expected_projects), list_api.calls)
    for project in expected_projects:
      self.assertTrue(project in list_api.projects)


if __name__ == '__main__':
  unittest.main(testLoader=gcutil_unittest.GcutilLoader())
