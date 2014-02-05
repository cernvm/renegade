#!/usr/bin/python
#
# Copyright 2013 Google Inc. All Rights Reserved.
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

"""Unit tests for the API version support."""

import path_initializer
path_initializer.InitSysPath()

import unittest
from gcutil_lib import gcutil_unittest
from gcutil_lib import version


class VersionTest(gcutil_unittest.GcutilTestCase):

  def testApiVersion(self):
    api_version = version.get(self.version)
    self.assertTrue(api_version is not None)
    self.assertEqual(self.version.split('_')[-1], api_version._name)

  def testValidateSupportedVersions(self):
    base_version = version._ApiVersions._ExtractBaseVersion(self.version)
    self.assertEqual(self.version.split('_')[-1], base_version)

  def testApiVersionsAreModuleGlobals(self):
    base_version = version._ApiVersions._ExtractBaseVersion(self.version)
    self.assertTrue(hasattr(version, base_version))
    version_object = getattr(version, base_version)
    self.assertEqual(base_version, version_object._name)


class SimpleVersionTest(unittest.TestCase):

  def testKnownVersionsExist(self):
    self.assertEqual('v1beta15', version.v1beta15._name)
    self.assertEqual('v1beta16', version.v1beta16._name)

  def testValidateAndExtractBaseVersion(self):
    valid_versions = (
        'v1',
        'v2',
        'v1beta1',
        'v1alpha2',
        'v1beta15')
    for valid in valid_versions:
      base_version = version._ApiVersions._ExtractBaseVersion(valid)
      self.assertEqual(valid.split('_')[-1], base_version)

  def testValidateAndExtractBaseVersionInvalid(self):
    invalid_versions = (
        'v',
        '1',
        'beta',
        'beta15',
        'vbeta',
        'v1beta',
        'v1beta1a'
        '1beta17')
    for invalid in invalid_versions:
      self.assertRaises(
          ValueError, version._ApiVersions._ExtractBaseVersion, invalid)

  def testVersionComparison(self):
    versions = version._ApiVersions(('v1beta15', 'v1beta16', 'v1'))
    v1beta15 = versions.get('v1beta15')
    v1beta16 = versions.get('v1beta16')

    self.assertEqual(0, v1beta15._index)
    self.assertEqual(1, v1beta16._index)
    self.assertEqual(2, versions.get('v1')._index)

    self.assertTrue(v1beta15 < v1beta16)
    self.assertTrue(v1beta15 != v1beta16)
    self.assertTrue(v1beta15 <= v1beta16)
    self.assertFalse(v1beta15 > v1beta16)
    self.assertFalse(v1beta15 >= v1beta16)
    self.assertFalse(v1beta15 == v1beta16)

    self.assertTrue(v1beta16 > v1beta15)
    self.assertTrue(v1beta16 != v1beta15)
    self.assertTrue(v1beta16 >= v1beta15)
    self.assertFalse(v1beta16 < v1beta15)
    self.assertFalse(v1beta16 <= v1beta15)
    self.assertFalse(v1beta16 == v1beta15)

    self.assertEqual(v1beta15, v1beta15)
    self.assertEqual(v1beta15, version._ApiVersion('v1beta15', 0, versions))

  def testVersionStringComparison(self):
    versions = version._ApiVersions(('v1', 'v2', 'v3'))
    v2 = versions.get('v2')
    self.assertTrue(v2 < 'v3')
    self.assertTrue('v1' < v2)
    self.assertEqual('v2', v2)
    self.assertEqual(v2, 'v2')
    self.assertNotEqual(v2, versions.get('v3'))
    self.assertNotEqual(v2, 'v1')

  def testVersionGetItem(self):
    versions = version._ApiVersions(('v1', 'v2', 'v3'))
    v1 = versions['v1']
    v2 = versions['v2']
    v3 = versions['v3']
    self.assertTrue(v1 < v2 < v3)


if __name__ == '__main__':
  unittest.main(testLoader=gcutil_unittest.GcutilLoader())
