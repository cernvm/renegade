# Copyright 2013 Google Inc. All Rights Reserved.

"""gcloud command line tool."""

import os
import sys

# If we're in a virtualenv, import site packages.
if os.environ.get('VIRTUAL_ENV'):
  # pylint:disable=unused-import
  # pylint:disable=g-import-not-at-top
  import site


def _SetPriorityCloudSDKPath():
  """Put google-cloud-sdk/lib at the beginning of sys.path.

  Modifying sys.path in this way allows us to always use our bundled versions
  of libaries, even when other versions have been installed. It also allows the
  user to install extra libraries that we cannot bundle (ie PyOpenSSL), and
  gcloud commands can use those libraries.
  """

  def _GetRootContainingGoogle():
    path = __file__
    while True:
      parent, here = os.path.split(path)
      if not here:
        break
      if here == 'google':
        return parent
      path = parent

  module_root = _GetRootContainingGoogle()

  # check if we're already set
  if sys.path and module_root == sys.path[0]:
    return
  sys.path.insert(0, module_root)

_SetPriorityCloudSDKPath()

# pylint:disable=g-import-not-at-top, We want the _SetPriorityCloudSDKPath()
# function to be called before we try to import any CloudSDK modules.
from google.cloud.sdk.core import cli
from google.cloud.sdk.core import metrics
from google.cloud.sdk.core import properties
from google.cloud.sdk.core.updater import local_state
from google.cloud.sdk.core.updater import update_manager




def UpdateCheck():
  try:
    update_manager.UpdateManager().PerformUpdateCheck()
  # pylint:disable=broad-except, We never want this to escape, ever. Only
  # messages printed should reach the user.
  except Exception:
    pass


def VersionFunc():
  _loader.Execute(['version'])

_loader = cli.CLIFromConfig(
    os.path.join(
        cli.GooglePackageRoot(),
        'cloud',
        'sdk',
        'gcloud',
        'gcloud.yaml',
    ),
    version_func=VersionFunc,
)

# Check for updates on shutdown but not for any of the updater commands.
_loader.RegisterPostRunHook(UpdateCheck,
                            exclude_commands=r'gcloud\.components\..*')
gcloud = _loader.EntryPoint()


def main():
  # TODO(user): Put a real version number here
  metrics.Executions(
      'gcloud',
      local_state.InstallationState.VersionForInstalledComponent('core'))
  _loader.Execute()

if __name__ == '__main__':
  main()
