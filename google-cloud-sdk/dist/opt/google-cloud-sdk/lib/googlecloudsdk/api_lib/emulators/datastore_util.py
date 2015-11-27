# Copyright 2015 Google Inc. All Rights Reserved.

"""Utility functions for gcloud datastore emulator."""

import os
from googlecloudsdk.api_lib.emulators import util
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import platforms


class NoGCDError(exceptions.Error):

  def __init__(self):
    super(NoGCDError, self).__init__(
        'Unable to find the Google Cloud Datastore emulator')


class UnableToPrepareDataDir(exceptions.Error):

  def __init__(self):
    super(UnableToPrepareDataDir, self).__init__(
        'Unable to prepare the data directory for the emualtor')


def GetGCDRoot():
  """Gets the directory of the GCD emulator installation in the Cloud SDK.

  Raises:
    NoCloudSDKError: If there is no SDK root.
    NoGCDError: If the GCD installation dir does not exist.

  Returns:
    str, The path to the root of the GCD emulator installation within Cloud SDK.
  """
  sdk_root = util.GetCloudSDKRoot()
  gcd_dir = os.path.join(sdk_root, 'platform', 'gcd')
  if not os.path.isdir(gcd_dir):
    raise NoGCDError()
  return gcd_dir


def ArgsForGCDEmulator(*args):
  """Constucts an argument list for calling the GCD emulator.

  Args:
    *args: args for the emulator.

  Returns:
    An argument list to execute the GCD emulator.
  """
  current_os = platforms.OperatingSystem.Current()
  if current_os is platforms.OperatingSystem.WINDOWS:
    gcd_executable = os.path.join(GetGCDRoot(), 'gcd.cmd')
    return execution_utils.ArgsForCMDTool(gcd_executable, *args)
  else:
    gcd_executable = os.path.join(GetGCDRoot(), 'gcd.sh')
    return execution_utils.ArgsForShellTool(gcd_executable, *args)


DATASTORE = 'datastore'
DATASTORE_TITLE = 'Google Cloud Datastore emulator'


def PrepareGCDDataDir(data_dir):
  """Prepares the given directory using gcd create.

  Raises:
    UnableToPrepareDataDir: If the gcd create execution fails.

  Args:
    data_dir: str, Path of data directy to be prepared.
  """
  if os.path.isdir(data_dir) and os.listdir(data_dir):
    log.warn('Reusing existing data in [{0}].'.format(data_dir))
    return

  gcd_create_args = ['create']
  project = properties.VALUES.core.project.Get(required=True)
  gcd_create_args.append('--project_id={0}'.format(project))
  gcd_create_args.append(data_dir)
  exec_args = ArgsForGCDEmulator(*gcd_create_args)

  log.status.Print('Executing: {0}'.format(' '.join(exec_args)))
  process = util.Exec(exec_args)
  util.PrefixOutput(process, DATASTORE)
  failed = process.poll()

  if failed:
    raise UnableToPrepareDataDir()


def StartGCDEmulator(args):
  """Starts the datastore emulator with the given arguments.

  Args:
    args: Arguments passed to the start command.

  Returns:
    process, The handle of the child process running the datastore emulator.
  """
  gcd_start_args = ['start']
  gcd_start_args.append('--host={0}'.format(args.host_port.host))
  gcd_start_args.append('--port={0}'.format(args.host_port.port))
  gcd_start_args.append('--store_on_disk={0}'.format(args.store_on_disk))
  gcd_start_args.append('--consistency={0}'.format(args.consistency))
  gcd_start_args.append('--allow_remote_shutdown')
  gcd_start_args.append(args.data_dir)
  exec_args = ArgsForGCDEmulator(*gcd_start_args)

  log.status.Print('Executing: {0}'.format(' '.join(exec_args)))
  return util.Exec(exec_args)


def WriteGCDEnvYaml(args):
  """Writes the env.yaml file for the datastore emulator with provided args.

  Args:
    args: Arguments passed to the start command.
  """
  host_port = '{0}:{1}'.format(args.host_port.host, args.host_port.port)
  project_id = properties.VALUES.core.project.Get(required=True)
  env = {'DATASTORE_HOST': 'http://{0}'.format(host_port),
         'DATASTORE_LOCAL_HOST': host_port,
         'DATASTORE_DATASET': project_id,
         'DATASTORE_PROJECT_ID': project_id,
        }
  util.WriteEnvYaml(env, args.data_dir)


def GetDataDir():
  return util.GetDataDir(DATASTORE)


def GetHostPort():
  return util.GetHostPort(DATASTORE)
