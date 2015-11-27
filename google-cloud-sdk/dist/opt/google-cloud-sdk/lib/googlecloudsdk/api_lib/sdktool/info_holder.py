# Copyright 2015 Google Inc. All Rights Reserved.
#
"""Contains utilities for holding and formatting install information.

This is useful for the output of 'gcloud info', which in turn is extremely
useful for debugging issues related to weird installations, out-of-date
installations, and so on.
"""

import os
import re
import StringIO
import sys
import textwrap

from googlecloudsdk.core import config
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.updater import update_manager
from googlecloudsdk.core.util import platforms


class InfoHolder(object):
  """Base object to hold all the configuration info."""

  def __init__(self):
    self.basic = BasicInfo()
    self.installation = InstallationInfo()
    self.config = ConfigInfo()
    self.logs = LogsInfo()

  def __str__(self):
    out = StringIO.StringIO()
    out.write(str(self.basic) + '\n')
    out.write(str(self.installation) + '\n')
    out.write(str(self.config) + '\n')
    out.write(str(self.logs) + '\n')
    return out.getvalue()


class BasicInfo(object):
  """Holds basic information about your system setup."""

  def __init__(self):
    platform = platforms.Platform.Current()
    self.version = config.CLOUD_SDK_VERSION
    self.operating_system = platform.operating_system
    self.architecture = platform.architecture
    self.python_version = sys.version
    self.site_packages = 'site' in sys.modules

  def __str__(self):
    return textwrap.dedent("""\
        Google Cloud SDK [{version}]

        Platform: [{os}, {arch}]
        Python Version: [{python_version}]
        Python Location: [{python_location}]
        Site Packages: [{site_packages}]
        """.format(
            version=self.version,
            os=self.operating_system.name,
            arch=self.architecture.name,
            python_location=sys.executable,
            python_version=self.python_version.replace('\n', ' '),
            site_packages='Enabled' if self.site_packages else 'Disabled'))


class InstallationInfo(object):
  """Holds information about your Cloud SDK installation."""

  def __init__(self):
    self.sdk_root = config.Paths().sdk_root
    self.release_channel = config.INSTALLATION_CONFIG.release_channel
    self.repo_url = config.INSTALLATION_CONFIG.snapshot_url
    repos = properties.VALUES.component_manager.additional_repositories.Get(
        validate=False)
    self.additional_repos = repos.split(',') if repos else []
    self.path = os.environ.get('PATH', '')

    if self.sdk_root:
      manager = update_manager.UpdateManager()
      self.components = manager.GetCurrentVersionsInformation()
      self.old_tool_paths = manager.FindAllOldToolsOnPath()
      paths = [os.path.realpath(p) for p in self.path.split(os.pathsep)]
      this_path = os.path.realpath(
          os.path.join(self.sdk_root,
                       update_manager.UpdateManager.BIN_DIR_NAME))
      # TODO(markpell): Validate symlinks in /usr/local/bin when we start
      # creating them.
      self.on_path = this_path in paths
    else:
      self.components = {}
      self.old_tool_paths = []
      self.on_path = False

  def __str__(self):
    out = StringIO.StringIO()
    out.write('Installation Root: [{0}]\n'.format(
        self.sdk_root if self.sdk_root else 'Unknown'))
    if config.INSTALLATION_CONFIG.IsAlternateReleaseChannel():
      out.write('Release Channel: [{0}]\n'.format(self.release_channel))
      out.write('Repository URL: [{0}]\n'.format(self.repo_url))
    if self.additional_repos:
      out.write('Additional Repositories:\n  {0}\n'.format(
          '\n  '.join(self.additional_repos)))

    if self.components:
      components = ['{0}: [{1}]'.format(name, value) for name, value in
                    self.components.iteritems()]
      out.write('Installed Components:\n  {0}\n'.format(
          '\n  '.join(components)))

    out.write('System PATH: [{0}]\n'.format(self.path))
    out.write('Cloud SDK on PATH: [{0}]\n'.format(self.on_path))

    if self.old_tool_paths:
      out.write('\nWARNING: There are old versions of the Google Cloud '
                'Platform tools on your system PATH.\n  {0}\n'
                .format('\n  '.join(self.old_tool_paths)))
    return out.getvalue()


class ConfigInfo(object):
  """Holds information about where config is stored and what values are set."""

  def __init__(self):
    self.paths = config.Paths()
    self.account = properties.VALUES.core.account.Get(validate=False)
    self.project = properties.VALUES.core.project.Get(validate=False)
    self.properties = properties.VALUES.AllValues()

  def __str__(self):
    out = StringIO.StringIO()
    out.write(textwrap.dedent("""\
        Installation Properties: [{installation_properties}]
        User Config Directory: [{global_config}]
        User Properties: [{user_properties}]
        Current Workspace: [{workspace}]
        Workspace Config Directory: [{workspace_config}]
        Workspace Properties: [{workspace_properties}]

        Account: [{account}]
        Project: [{project}]

        """.format(
            installation_properties=self.paths.installation_properties_path,
            global_config=self.paths.global_config_dir,
            user_properties=self.paths.user_properties_path,
            workspace=self.paths.workspace_dir,
            workspace_config=self.paths.workspace_config_dir,
            workspace_properties=self.paths.workspace_properties_path,
            account=self.account,
            project=self.project)))

    out.write('Current Properties:\n')
    for section, props in self.properties.iteritems():
      out.write('  [{section}]\n'.format(section=section))
      for name, value in props.iteritems():
        out.write('    {name}: [{value}]\n'.format(
            name=name, value=value))
    return out.getvalue()


def RecentLogFiles(logs_dir, num=1):
  """Finds the most recent (not current) gcloud log files.

  Args:
    logs_dir: str, The path to the logs directory being used.
    num: the number of log files to find

  Returns:
    A list of full paths to the latest num log files, excluding the current
    log file. If there are fewer than num log files, include all of
    them. They will be in chronological order.
  """
  date_dirs = FilesSortedByName(logs_dir)
  if not date_dirs:
    return []

  found_files = []
  for date_dir in reversed(date_dirs):
    log_files = reversed(FilesSortedByName(date_dir) or [])
    found_files.extend(log_files)
    if len(found_files) >= num + 1:
      return found_files[1:num+1]

  return found_files[1:]


def LastLogFile(logs_dir):
  """Finds the last (not current) gcloud log file.

  Args:
    logs_dir: str, The path to the logs directory being used.

  Returns:
    str, The full path to the last (but not the currently in use) log file
    if it exists, or None.
  """
  files = RecentLogFiles(logs_dir)
  if files:
    return files[0]
  return None


def FilesSortedByName(directory):
  """Gets the list of files in the given directory, sorted by name.

  Args:
    directory: str, The path to the directory to list.

  Returns:
    [str], The full paths of the files, sorted by file name, or None.
  """
  if not os.path.isdir(directory):
    return None
  dates = os.listdir(directory)
  if not dates:
    return None
  return [os.path.join(directory, date) for date in sorted(dates)]


class LogData(object):
  """Representation of a log file.

  Stores information such as the name of the log file, its contents, and the
  command run.
  """

  # This precedes the traceback in the log file.
  TRACEBACK_MARKER = '\nTraceback (most recent call last):\n'

  # This shows the command run in the log file
  COMMAND_REGEXP = r'Running (gcloud\.[a-z.]+)'

  def __init__(self, filename, command, contents, traceback):
    self.filename = filename
    self.command = command
    self.contents = contents
    self.traceback = traceback

  def __str__(self):
    logs_dir = config.Paths().logs_dir
    log_path = self.filename
    if self.filename.startswith(logs_dir):
      # Just keep the parts of the log paths that aren't common
      log_path = self.filename[len(logs_dir + os.path.sep):]
    crash_detected = ' (crash detected)' if self.traceback else ''
    return '[{0}]: [{1}]{2}'.format(log_path, self.command, crash_detected)

  @classmethod
  def FromFile(cls, log_file):
    """Parse the file at the given path into a LogData.

    Args:
      log_file: str, the path to the log file to read

    Returns:
      LogData, representation of the log file
    """
    with open(log_file) as log_fp:
      contents = log_fp.read()
      traceback = None
      command = None
      match = re.search(cls.COMMAND_REGEXP, contents)
      if match:
        # ex. gcloud.group.subgroup.command
        dotted_cmd_string, = match.groups()
        command = ' '.join(dotted_cmd_string.split('.'))
      if cls.TRACEBACK_MARKER in contents:
        traceback = (cls.TRACEBACK_MARKER +
                     contents.split(cls.TRACEBACK_MARKER)[-1])
        # Trim any log lines that follow the traceback
        traceback = re.split(log.LOG_PREFIX_PATTERN, traceback)[0]
        traceback = traceback.strip()
      return cls(log_file, command, contents, traceback)


class LogsInfo(object):
  """Holds information about where logs are located."""

  NUM_RECENT_LOG_FILES = 5

  def __init__(self):
    paths = config.Paths()
    self.logs_dir = paths.logs_dir
    self.last_log = LastLogFile(self.logs_dir)
    self.last_logs = RecentLogFiles(self.logs_dir, self.NUM_RECENT_LOG_FILES)

  def __str__(self):
    return textwrap.dedent("""\
        Logs Directory: [{logs_dir}]
        Last Log File: [{log_file}]
        """.format(logs_dir=self.logs_dir, log_file=self.last_log))

  def LastLogContents(self):
    if not self.last_log:
      return ''
    with open(self.last_log) as fp:
      return fp.read()

  def GetRecentRuns(self):
    """Return the most recent runs, as reported by info_holder.LogsInfo.

    Returns:
      A list of LogData
    """
    return [LogData.FromFile(log_file) for log_file in self.last_logs]
