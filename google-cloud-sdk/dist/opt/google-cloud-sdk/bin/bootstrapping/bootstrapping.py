# Copyright 2013 Google Inc. All Rights Reserved.

"""Common bootstrapping functionality used by the wrapper scripts."""

# Disables import order warning and unused import.  Setup changes the python
# path so cloud sdk imports will actually work, so it must come first.
# pylint: disable=C6203
# pylint: disable=W0611
import setup

import json
import os
import signal
import subprocess
import sys
import textwrap

import oauth2client.gce as gce
import oauth2client.multistore_file as multistore_file
from google.cloud.sdk.core import config
from google.cloud.sdk.core.credentials import store as c_store
from google.cloud.sdk.core import metrics
from google.cloud.sdk.core import properties
from google.cloud.sdk.core.updater import local_state
from google.cloud.sdk.core.updater import update_manager


BOOTSTRAPPING_DIR = os.path.dirname(os.path.realpath(__file__))
BIN_DIR = os.path.dirname(BOOTSTRAPPING_DIR)
SDK_ROOT = os.path.dirname(BIN_DIR)


def ParseCrossPlatformCmdLine():
  """A helper method to figure out what interpreter to use for execution.

  Looks at and consumes the first argument in sys.argv.  It uses this as the
  extension for ExecutorForExtension().

  Returns:
    A tuple of the extension and the corresponding executor.
  """
  ext = sys.argv.pop(1)
  executor = ExecutorForExtension(ext)
  return (ext, executor)


def ExecutorForExtension(ext):
  """Returns the appropriate method for shelling out to the required tool.

  Valid extensions are 'cmd', 'sh', and 'py'

  Args:
    ext: The extension to get the executor for

  Returns:
    A method that will shell out to the interpreter for that extension.

  Raises:
    ValueError: if the extension is not supported
  """
  executor = {'cmd': ExecuteCMDTool,
              'sh': ExecuteShellTool,
              'py': ExecutePythonTool}[ext]
  if not executor:
    raise ValueError('Invalid script mode.  '
                     'First arg must be "cmd", "sh", or "py"')
  return executor


def _GetPythonExecutable():
  cloudsdk_python = os.environ.get('CLOUDSDK_PYTHON')
  if cloudsdk_python:
    return cloudsdk_python
  python_bin = sys.executable
  if not python_bin:
    sys.stderr.write('Could not find Python executable.')
    sys.exit(1)
  return python_bin


def _GetShellExecutable():
  shell = os.getenv('SHELL', None)

  shells = ['/bin/bash', '/bin/sh']
  if shell:
    shells.insert(0, shell)

  for s in shells:
    if os.path.isfile(s):
      return s

  raise ValueError("You must set your 'SHELL' environment variable to a "
                   "valid shell executable to use this tool.")


def _GetToolExecutable(tool_dir, exec_name):
  return os.path.join(SDK_ROOT, tool_dir, exec_name)


def _GetToolArgs(interpreter, interpreter_args, tool_dir, exec_name, *args):
  executable = _GetToolExecutable(tool_dir, exec_name)
  tool_args = []
  if interpreter:
    tool_args.append(interpreter)
  if interpreter_args:
    tool_args.extend(interpreter_args)
  tool_args.append(executable)
  tool_args.extend(list(args))
  return tool_args


def ArgsForPythonTool(tool_dir, exec_name, *args):
  """Constructs an argument list for calling the python interpreter.

  Args:
    tool_dir: the directory the tool is located in
    exec_name: additional path to the executable under the tool_dir
    *args: args for the command

  Returns:
    An argument list to execute the python interpreter
  """
  python_executable = _GetPythonExecutable()

  python_args_str = os.environ.get('CLOUDSDK_PYTHON_ARGS')
  if not python_args_str:
    if setup.import_site_packages:
      python_args_str = ''
    else:
      python_args_str = '-S'
  python_args = python_args_str.split()
  return _GetToolArgs(
      python_executable, python_args, tool_dir, exec_name, *args)


def ArgsForShellTool(tool_dir, exec_name, *args):
  """Constructs an argument list for calling the bash interpreter.

  Args:
    tool_dir: the directory the tool is located in
    exec_name: additional path to the executable under the tool_dir
    *args: args for the command

  Returns:
    An argument list to execute the bash interpreter
  """
  shell_bin = _GetShellExecutable()
  return _GetToolArgs(shell_bin, [], tool_dir, exec_name, *args)


def ArgsForCMDTool(tool_dir, exec_name, *args):
  """Constructs an argument list for calling the cmd interpreter.

  Args:
    tool_dir: the directory the tool is located in
    exec_name: additional path to the executable under the tool_dir
    *args: args for the command

  Returns:
    An argument list to execute the cmd interpreter
  """
  return _GetToolArgs('cmd', ['/c'], tool_dir, exec_name, *args)


def ArgsForBinaryTool(tool_dir, exec_name, *args):
  """Constructs an argument list for calling a native binary.

  Args:
    tool_dir: the directory the tool is located in
    exec_name: additional path to the executable under the tool_dir
    *args: args for the command

  Returns:
    An argument list to execute the native binary
  """
  return _GetToolArgs(None, None, tool_dir, exec_name, *args)


def ExecutePythonTool(tool_dir, exec_name, *args):
  """Execute the given python script with the given args and command line.

  Args:
    tool_dir: the directory the tool is located in
    exec_name: additional path to the executable under the tool_dir
    *args: args for the command
  """
  _ExecuteTool(ArgsForPythonTool(tool_dir, exec_name, *args))


def ExecutePythonToolWriteOutputNoExitNoArgs(
    tool_dir, exec_name, output, *args):
  """Execute the given python script with the given args and command line.

  Args:
    tool_dir: the directory the tool is located in
    exec_name: additional path to the executable under the tool_dir
    output: The file to write output to.
    *args: args for the command
  """
  _ExecuteToolNoExitNoArgsWriteOutput(
      ArgsForPythonTool(tool_dir, exec_name, *args), output)


def ExecutePythonToolNoExitNoArgs(tool_dir, exec_name, *args):
  """Execute the given python script with the given args.

  Args:
    tool_dir: the directory the tool is located in
    exec_name: additional path to the executable under the tool_dir
    *args: args for the command
  """
  _ExecuteToolNoExitNoArgs(ArgsForPythonTool(tool_dir, exec_name, *args))


def ExecuteShellTool(tool_dir, exec_name, *args):
  """Execute the given bash script with the given args.

  Args:
    tool_dir: the directory the tool is located in
    exec_name: additional path to the executable under the tool_dir
    *args: args for the command
  """
  _ExecuteTool(ArgsForShellTool(tool_dir, exec_name, *args))


def ExecuteCMDTool(tool_dir, exec_name, *args):
  """Execute the given batch file with the given args.

  Args:
    tool_dir: the directory the tool is located in
    exec_name: additional path to the executable under the tool_dir
    *args: args for the command
  """
  _ExecuteTool(ArgsForCMDTool(tool_dir, exec_name, *args))


class ProcessHolder(object):
  PROCESS = None

  @staticmethod
  # pylint: disable=W0613
  def Handler(signum, frame):
    if ProcessHolder.PROCESS:
      ProcessHolder.PROCESS.terminate()
      ret_val = ProcessHolder.PROCESS.wait()
    sys.exit(ret_val)


def _GetToolEnv():
  env = dict(os.environ)
  env['CLOUDSDK_WRAPPER'] = '1'
  env['CLOUDSDK_PYTHON'] = _GetPythonExecutable()
  if 'CLOUDSDK_PYTHON_ARGS' not in env:
    if setup.import_site_packages:
      env['CLOUDSDK_PYTHON_ARGS'] = ''
    else:
      env['CLOUDSDK_PYTHON_ARGS'] = '-S'
  return env


def _ExecuteToolNoExitNoArgs(args):
  # We use subprocess instead of execv because windows does not support process
  # replacement.  The result of execv on windows is that a new processes is
  # started and the original is killed.  When running in a shell, the prompt
  # returns as soon as the parent is killed even though the child is still
  # running.  subprocess.call() waits for the new process to finish before
  # returning.
  signal.signal(signal.SIGTERM, ProcessHolder.Handler)
  p = subprocess.Popen(args, env=_GetToolEnv())
  ProcessHolder.PROCESS = p
  ret_val = p.wait()
  return ret_val


def _ExecuteToolNoExitNoArgsWriteOutput(args, output):
  # We use subprocess instead of execv because windows does not support process
  # replacement.  The result of execv on windows is that a new processes is
  # started and the original is killed.  When running in a shell, the prompt
  # returns as soon as the parent is killed even though the child is still
  # running.  subprocess.call() waits for the new process to finish before
  # returning.
  signal.signal(signal.SIGTERM, ProcessHolder.Handler)
  with open(output, 'w') as out:
    p = subprocess.Popen(args, env=_GetToolEnv(), stdout=out)
  ProcessHolder.PROCESS = p
  ret_val = p.wait()
  return ret_val


def _ExecuteTool(args):
  ret_val = _ExecuteToolNoExitNoArgs(args+sys.argv[1:])
  sys.exit(ret_val)


def _ExecuteToolWriteOutputNoExit(args, output):
  ret_val = _ExecuteToolNoExitNoArgsWriteOutput(args+sys.argv[1:], output)
  return ret_val


def CheckCredOrExit(can_be_gce=False):
  try:
    cred = c_store.Load()
    if not can_be_gce and isinstance(cred, gce.AppAssertionCredentials):
      raise c_store.NoActiveAccountException()
  except c_store.NoActiveAccountException:
    print textwrap.dedent("""\
        There is no currently active account.
        You can activate an already-authorized account with
         $ gcloud config set account <account>
        or authorize a new account with
         $ gcloud auth login
        or any of the other gcloud auth subcommands with
         $ gcloud auth --help
        """)
    sys.exit(1)
  except c_store.NoCredentialsForAccountException:
    account = properties.VALUES.core.account.Get()
    print textwrap.dedent("""\
        There are no credentials for the active account: {account}
        If this is a user account, use
         $ gcloud auth login
        to activate it. If this was a different type of account, use one of the other
        gcloud auth subcommands with
         $ gcloud auth --help
        """.format(account=account))
    sys.exit(1)


def GetDefaultInstalledComponents():
  """Gets the list of components to install by default.

  Returns:
    list(str), The component ids that should be installed.  It will return []
    if there are no default components, or if there is any error in reading
    the file with the defaults.
  """
  default_components_file = os.path.join(BOOTSTRAPPING_DIR,
                                         '.default_components')
  try:
    with open(default_components_file) as f:
      return json.load(f)
  # pylint:disable=bare-except, If the file does not exist or is malformed,
  # we don't want to expose this as an error.  Setup will just continue
  # without installing any components by default and will tell the user how
  # to install the components they want manually.
  except:
    pass
  return []


def GetComponentInstallationOptions():
  """Gets the list of available install configurations.

  Returns:
    [{name, default_components], The JSON representing the available
    configurations or None if there are no install configurations.
  """
  install_configurations_file = os.path.join(BOOTSTRAPPING_DIR,
                                             '.install_configurations')
  try:
    with open(install_configurations_file) as f:
      return json.load(f)
  # pylint:disable=bare-except, If the file does not exist or is malformed,
  # we don't want to expose this as an error.  Setup will just continue
  # without prompting for any install configurations and will tell the user how
  # to install the components they want manually.
  except:
    pass
  return None


def CheckForBlacklistedCommand(args, blacklist, warn=True, die=False):
  """Blacklist certain subcommands, and warn the user.

  Args:
    args: the command line arguments, including the 0th argument which is
        the program name.
    blacklist: a map of blacklisted commands to the messages that should be
        printed when they're run.
    warn: if true, print a warning message.
    die: if true, exit.

  Returns:
    True if a command in the blacklist is being indicated by args.

  """
  bad_arg = None
  for arg in args[1:]:
    if arg[0] is '-':
      continue
    if arg in blacklist:
      bad_arg = arg
      break

  blacklisted = bad_arg is not None

  if blacklisted:
    if warn:
      print 'It looks like you are trying to run "%s %s".' % (args[0], bad_arg)
      print ('The "%s" command is no longer needed with'
             ' the Cloud SDK.') % bad_arg
      print blacklist[bad_arg]
      answer = raw_input('Really run this command? (y/N) ')
      if answer in ['y', 'Y']:
        return False

    if die:
      sys.exit(1)

  return blacklisted


def CheckUpdates():
  """Check for updates and inform the user.

  """
  manager = update_manager.UpdateManager()
  try:
    manager.PerformUpdateCheck()
  # pylint:disable=broad-except, We never want this to escape, ever. Only
  # messages printed should reach the user.
  except Exception:
    pass


def CommandStart(command_name, component_id=None):
  """Logs that the given command is being executed.

  Args:
    command_name: str, The name of the command being executed.
    component_id: str, The component id that this command belongs to.  Used for
      version information.
  """
  version = None
  if component_id:
    version = local_state.InstallationState.VersionForInstalledComponent(
        component_id)
  metrics.Executions(command_name, version)


def PrerunChecks(can_be_gce=False):
  """Call all normal pre-command checks.

  Checks for credentials and updates. If no credentials exist, exit. If there
  are updates available, inform the user and continue.

  Silent when there are credentials and no updates.

  Args:
    can_be_gce: bool, True is the credentials may be those provided by the
        GCE metadata server.
  """
  CheckCredOrExit(can_be_gce=can_be_gce)
  CheckUpdates()


def GetActiveProjectAndAccount():
  """Get the active project name and account for the active credentials.

  For use with wrapping legacy tools that take projects and credentials on
  the command line.

  Returns:
    (str, str), A tuple whose first element is the project, and whose second
    element is the account.
  """
  project_name = properties.VALUES.core.project.Get()
  account = properties.VALUES.core.account.Get()
  return (project_name, account)
