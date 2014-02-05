#!/usr/bin/env python
#
# Copyright 2013 Google Inc. All Rights Reserved.
#

"""Do initial setup for the Cloud SDK."""

import bootstrapping

# pylint:disable=g-bad-import-order
import argparse
import os
import re
import shutil
import sys
import textwrap

from google.cloud.sdk.calliope import exceptions
from google.cloud.sdk.core import config
from google.cloud.sdk.core import log
from google.cloud.sdk.core import properties
from google.cloud.sdk.core.credentials import gce as c_gce
from google.cloud.sdk.core.util import console_io
from google.cloud.sdk.core.util import platforms
from google.cloud.sdk.gcloud import gcloud


def ParseArgs():
  """Parse args for the installer, so interactive prompts can be avoided."""

  def Bool(s):
    return s.lower() in ['true', '1']

  parser = argparse.ArgumentParser()

  parser.add_argument('--usage-reporting',
                      default=None, type=Bool, nargs=1,
                      help='(true/false) Disable anonymous usage reporting.')
  parser.add_argument('--update-rc', type=Bool, nargs=1,
                      help=('(true/false) Do not attempt to update any'
                            ' profiles.'))
  parser.add_argument('--rc-path',
                      help='Profile to update with PATH and completion.')
  parser.add_argument('--bash-completion',
                      default=None, type=Bool, nargs=1,
                      help=('(true/false) If updating a profile, add a line for'
                            ' bash completion.'))
  parser.add_argument('--disable-installation-options', action='store_true',
                      help='Do not ask about special installation options.')

  return parser.parse_args()


def Prompts(usage_reporting):
  """Display prompts to opt out of usage reporting.

  Args:
    usage_reporting: bool, If True, enable usage reporting. If None, ask.
  """
  if usage_reporting is None:
    print """
The Google Cloud SDK is currently in developer preview. To help improve the
quality of this product, we collect anonymized data on how the SDK is used.
You may choose to opt out of this collection now (by choosing 'N' at the below
prompt), or at any time in the future by running the following command:
    gcloud config --global-only set disable_usage_reporting true
"""

    usage_reporting = console_io.PromptContinue(
        prompt_string='Do you want to help improve the Google Cloud SDK')
  properties.PersistProperty(properties.VALUES.core.disable_usage_reporting,
                             not usage_reporting, force_global=True)


# pylint:disable=unused-argument
def UpdatePathForWindows(bin_path):
  """Update the Windows system path to include bin_path.

  Args:
    bin_path: str, The absolute path to the directory that will contain
        Cloud SDK binaries.
  """

  # pylint:disable=g-import-not-at-top, we want to only attempt these imports
  # on windows.
  try:
    import win32con
    import win32gui
    import _winreg
  except ImportError:
    print """\
The installer is unable to automatically update your system PATH. Please add
  {path}
to your system PATH to enable easy use of the Cloud SDK Command Line Tools.
""".format(path=bin_path)
    return

  def GetEnv(name):
    root = _winreg.HKEY_CURRENT_USER
    subkey = 'Environment'
    key = _winreg.OpenKey(root, subkey, 0, _winreg.KEY_READ)
    try:
      value, _ = _winreg.QueryValueEx(key, name)
    # pylint:disable=undefined-variable, This variable is defined in windows.
    except WindowsError:
      return ''
    return value

  def SetEnv(name, value):
    key = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, 'Environment', 0,
                          _winreg.KEY_ALL_ACCESS)
    _winreg.SetValueEx(key, name, 0, _winreg.REG_EXPAND_SZ, value)
    _winreg.CloseKey(key)
    win32gui.SendMessage(
        win32con.HWND_BROADCAST, win32con.WM_SETTINGCHANGE, 0, 'Environment')
    return value

  def Remove(paths, value):
    while value in paths:
      paths.remove(value)

  def PrependEnv(name, values):
    paths = GetEnv(name).split(';')
    for value in values:
      if value in paths:
        Remove(paths, value)
      paths.insert(0, value)
    SetEnv(name, ';'.join(paths))

  PrependEnv('Path', [bin_path])

  print textwrap.dedent("""\
The following directory has been added to your PATH.
  {bin_path}

Create a new command shell for the changes to take effect.
""".format(bin_path=bin_path))


def _CreateBashCompletionRC(rc_path):
  script_dir = os.path.join(bootstrapping.SDK_ROOT, 'lib', 'argcomplete',
                            'scripts')
  bootstrapping.ExecutePythonToolWriteOutputNoExitNoArgs(
      script_dir, 'register-python-argcomplete', rc_path,
      'gcloud')


def UpdatePath(bash_completion, rc_path, bin_path):
  """Update the system path to include bin_path.

  Args:
    bash_completion: bool, Whether or not to do bash completion. If None, ask.
    rc_path: str, The path to the rc file to update. If None, ask.
    bin_path: str, The absolute path to the directory that will contain
        Cloud SDK binaries.
  """

  host_os = platforms.OperatingSystem.Current()
  if host_os == platforms.OperatingSystem.WINDOWS:
    UpdatePathForWindows(bin_path)
    return

  if not rc_path:
    # figure out what file to edit
    if host_os == platforms.OperatingSystem.LINUX:
      if c_gce.Metadata().connected:
        file_name = '.bash_profile'
      else:
        file_name = '.bashrc'
    elif host_os == platforms.OperatingSystem.MACOSX:
      file_name = '.bash_profile'
    elif host_os == platforms.OperatingSystem.CYGWIN:
      file_name = '.bashrc'
    elif host_os == platforms.OperatingSystem.MSYS:
      file_name = '.profile'
    else:
      file_name = '.bashrc'
    rc_path = os.path.expanduser(os.path.join('~', file_name))

    rc_path_update = console_io.PromptResponse(
        ('Enter path to a file to append the PATH update to, or leave blank '
         'to use {rc_path}:  ').format(rc_path=rc_path))
    if rc_path_update:
      rc_path = os.path.expanduser(rc_path_update)

  if os.path.exists(rc_path):
    with open(rc_path) as rc_file:
      rc_data = rc_file.read()
      cached_rc_data = rc_data
  else:
    rc_data = ''
    cached_rc_data = ''

  path_comment = r'# The next line updates PATH for the Google Cloud SDK.'
  path_subre = re.compile(r'\n*'+path_comment+r'\nexport PATH=.*$',
                          re.MULTILINE)

  path_line = '{comment}\nexport PATH={bin_path}:$PATH\n'.format(
      comment=path_comment, bin_path=bin_path)
  filtered_data = path_subre.sub('', rc_data)
  rc_data = '{filtered_data}\n{path_line}'.format(
      filtered_data=filtered_data,
      path_line=path_line)

  if bash_completion is None:
    bash_completion = console_io.PromptContinue(
        prompt_string='\nDo you want to enable command-line completion?')

  if bash_completion:
    arg_rc_path = os.path.join(bootstrapping.SDK_ROOT, 'arg_rc')
    _CreateBashCompletionRC(arg_rc_path)

    complete_comment = r'# The next line enables bash completion for gcloud.'
    complete_subre = re.compile(r'\n*'+complete_comment+r'\nsource.*$',
                                re.MULTILINE)

    complete_line = '{comment}\nsource {rc_path}\n'.format(
        comment=complete_comment, rc_path=arg_rc_path)
    filtered_data = complete_subre.sub('', rc_data)
    rc_data = '{filtered_data}\n{complete_line}'.format(
        filtered_data=filtered_data,
        complete_line=complete_line)

  if cached_rc_data != rc_data:
    if os.path.exists(rc_path):
      rc_backup = rc_path+'.backup'
      print 'Backing up "{rc}" to "{backup}".'.format(
          rc=rc_path, backup=rc_backup)
      shutil.copyfile(rc_path, rc_backup)

    with open(rc_path, 'w') as rc_file:
      rc_file.write(rc_data)
  else:
    print 'No changes necessary for "{rc}".'.format(rc=rc_path)

  print textwrap.dedent("""\
{rc_path} has been updated. Start a new shell for the changes to take effect.
      """.format(rc_path=rc_path))


def Install(disable_installation_options):
  """Do the normal installation of the Cloud SDK."""
  # Install the OS specific wrapper scripts for gcloud and any pre-configured
  # components for the SDK.
  to_install = bootstrapping.GetDefaultInstalledComponents()

  print """
This will install all the core command line tools necessary for working with
the Google Cloud Platform.
"""
  # See if there are additional configurations to choose from.
  installation_options = bootstrapping.GetComponentInstallationOptions()
  if not disable_installation_options and installation_options:
    # Prompt the user to choose from one of the registered configurations.
    options = [option['name'] for option in installation_options]
    result = console_io.PromptChoice(
        options, default=len(options) - 1,
        message='If you are developing an App Engine application, please '
        'select the language your application is written in.  This will '
        'install the required tools and runtimes for working in that '
        'language.  If necessary, you can add and remove languages later '
        'through the gcloud component manager.')
    selected_components = installation_options[result]['default_components']
    if selected_components:
      to_install.extend(selected_components)

  components = InstallComponents(to_install)

  # Show the list of components if there were no pre-configured ones.
  if not to_install:
    components.list()


def ReInstall(component_ids):
  """Do a forced reinstallation of the Cloud SDK.

  Args:
    component_ids: [str], The components that should be automatically installed.
  """
  to_install = bootstrapping.GetDefaultInstalledComponents()
  to_install.extend(component_ids)
  InstallComponents(component_ids)


def InstallComponents(component_ids):
  # Installs the selected configuration or the wrappers for core at a minimum.
  components = gcloud.gcloud(verbosity=log.DEFAULT_CLI_VERBOSITY,
                             quiet=True).components
  components.update(component_ids=component_ids, allow_no_backup=True)
  return components


if __name__ == '__main__':
  pargs = ParseArgs()
  reinstall_components = os.environ.get('CLOUDSDK_REINSTALL_COMPONENTS')
  try:
    if reinstall_components:
      ReInstall(reinstall_components.split(','))
    else:
      Prompts(pargs.usage_reporting)
      bootstrapping.CommandStart('INSTALL', component_id='core')
      if not config.INSTALLATION_CONFIG.disable_updater:
        Install(pargs.disable_installation_options)

      if pargs.update_rc is None:
        pargs.update_rc = console_io.PromptContinue(
            prompt_string=('Do you want to update your system path to include'
                           ' the Google Cloud SDK'))
      if pargs.update_rc:
        UpdatePath(
            bash_completion=pargs.bash_completion,
            rc_path=pargs.rc_path,
            bin_path=bootstrapping.BIN_DIR,
        )

      print 'For more information on how to get started, please visit:'
      print '  https://developers.google.com/cloud/sdk/gettingstarted'
      print
  except exceptions.ToolException as e:
    print e
    sys.exit(1)
