"""Tests for mock_api."""

import path_initializer
path_initializer.InitSysPath()

import unittest
from gcutil_lib import mock_api
from gcutil_lib import mock_api_server


class MockApiTest(unittest.TestCase):
  def testCreateV1Beta15(self):
    mock, api = mock_api.CreateApi('v1beta15')
    self.assertTrue(isinstance(mock, mock_api_server.MockServer))
    self.assertTrue(api is not None)
    self.assertTrue(api.regions is not None)
    self.assertTrue(api.zones is not None)
    self.assertTrue('compute.regions.list' in api)

  def testCreateV1Beta16(self):
    mock, api = mock_api.CreateApi('v1beta16')
    self.assertTrue(isinstance(mock, mock_api_server.MockServer))
    self.assertTrue(api is not None)
    # Add tests here for presence of v1beta16-specific collections.



if __name__ == '__main__':
  unittest.main()
