#!/usr/bin/env python
#
# Copyright 2013 Google Inc. All Rights Reserved.
#

"""A convenience wrapper for starting bq."""

import sys

import bootstrapping

from google.cloud.sdk.core import config


def main():
  """Launches bq."""

  project, account = bootstrapping.GetActiveProjectAndAccount()
  json_path = config.Paths().LegacyCredentialsJSONPath(account)

  args = ['--credential_file', json_path]
  if project:
    args += ['--project', project]

  bootstrapping.ExecutePythonTool(
      'platform/bigquery', 'bq.py', *args)


if __name__ == '__main__':
  bootstrapping.CommandStart('bq', component_id='bq')
  blacklist = {
      'init': 'To authenticate, run gcloud auth.',
  }
  bootstrapping.CheckForBlacklistedCommand(sys.argv, blacklist,
                                           warn=True, die=True)
  bootstrapping.PrerunChecks()
  main()
