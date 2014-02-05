# Copyright 2013 Google Inc. All Rights Reserved.

"""Module with logging related functionality for calliope."""

import collections
import datetime
import errno
import logging
import os
import sys
import time


_VERBOSITY = collections.namedtuple('_VerbosityTuple', ['description', 'level'])
VERBOSITIES = [
    # Any number higher than CRITICAL will stop all output.  Use to to keep with
    # the convention that logging established for levels.
    _VERBOSITY('No Output', logging.CRITICAL + 10),
    _VERBOSITY('CRITICAL', logging.CRITICAL),
    _VERBOSITY('ERROR', logging.ERROR),
    _VERBOSITY('WARNING', logging.WARNING),
    _VERBOSITY('INFO', logging.INFO),
    _VERBOSITY('DEBUG', logging.DEBUG),
]
DEFAULT_CLI_VERBOSITY = 4
DEFAULT_INTERACTIVE_VERBOSITY = 3
MAX_VERBOSITY = len(VERBOSITIES) - 1


def Print(*msg):
  """Writes the given message to the output stream, and adds a newline.

  This method has the same output behavior as the build in print method but
  respects the configured verbosity.

  Args:
    *msg: str, The messages to print.
  """
  ConsoleWriter().Print(*msg)


# pylint: disable=g-bad-name, This must match the logging module.
def log(level, msg, *args, **kwargs):
  ConsoleLogger().log(level, msg, *args, **kwargs)


# pylint: disable=g-bad-name, This must match the logging module.
def debug(msg, *args, **kwargs):
  ConsoleLogger().debug(msg, *args, **kwargs)


# pylint: disable=g-bad-name, This must match the logging module.
def info(msg, *args, **kwargs):
  ConsoleLogger().info(msg, *args, **kwargs)


# pylint: disable=g-bad-name, This must match the logging module.
def warn(msg, *args, **kwargs):
  ConsoleLogger().warn(msg, *args, **kwargs)


# pylint: disable=g-bad-name, This must match the logging module.
def warning(msg, *args, **kwargs):
  ConsoleLogger().warning(msg, *args, **kwargs)


# pylint: disable=g-bad-name, This must match the logging module.
def error(msg, *args, **kwargs):
  ConsoleLogger().error(msg, *args, **kwargs)


# pylint: disable=g-bad-name, This must match the logging module.
def critical(msg, *args, **kwargs):
  ConsoleLogger().critical(msg, *args, **kwargs)


# pylint: disable=g-bad-name, This must match the logging module.
def fatal(msg, *args, **kwargs):
  ConsoleLogger().fatal(msg, *args, **kwargs)


# pylint: disable=g-bad-name, This must match the logging module.
def exception(msg, *args):
  ConsoleLogger().exception(msg, *args)


def InitLogging(verbosity=None, force=False):
  """Sets up python logging for running calliope commands.

  This clears all loggers registered in the logging module, and reinitializes
  it with the specific loggers we want for calliope.  If logging is initialized
  already, this has no effect unless force is True.

  Args:
    verbosity: int, The verbosity determines what level of logs will show in the
      console.
    force: bool, True to reset all logging if it has already been initialized.
  """
  if force or not _LogManager.instance:
    _LogManager.instance = _LogManager(verbosity)


def Shutdown():
  """Clear all settings from the active loggers.

  Since we are using the python logging module, and that is all statically
  initialized, this method does not actually turn off all the loggers.  The next
  time you call a logging method on this module, it will initialize as if it was
  the first time it was used.  If you hold references to loggers or writers
  after calling this method, it is possible they will continue to work, but
  their behavior might change when the logging framework is reinitialized in the
  future.  This is useful mainly for clearing the loggers between tests so stubs
  can get reset.
  """
  _LogManager.instance = None


def SetVerbosity(verbosity=None):
  """Controls the logging verbosity level for all loggers and writers.

  When running a single command through the shell, we generally want INFO
  messages to show up on stdout in the shell.  When in interactive mode, we want
  to log only to files.

  Args:
    verbosity: int, The verbosity determines what level of logs will show in the
      console.

  Returns:
    int, The old verbosity.
  """
  InitLogging()
  return _LogManager.instance.SetVerbosity(verbosity)


def AddFileLogging(logs_dir):
  """Adds a new logging file handler to the root logger.

  Args:
    logs_dir: str, The root directory to store logs in.
  """
  InitLogging()
  _LogManager.instance.AddLogsDir(logs_dir=logs_dir)


def FileOnlyLogger():
  """Gets the logger object that logs only to a file and never to the console.

  Returns:
    logging.Logger, The logger that outputs only to a file.
  """
  InitLogging()
  return _LogManager.instance.file_only_logger


def ConsoleLogger():
  """Gets the logger that writes to stdout in the console.

  This logger should be used for all normal logging.  This method will do
  default logging initialization if it has not already been done.

  Returns:
    logging.Logger, The configured logger.  This logger handles writing INFO
    messages and below to stdout (according to the configured verbosity).
    It also propagates to the root logger so any other messages will be handled
    normally by the stderr logger or any registered file loggers.
  """
  InitLogging()
  return _LogManager.instance.console_logger


def ConsoleWriter(stderr=False):
  """Gets the stdout wrapper for this logging configuration.

  This method will do default logging initialization if it has not already been
  done.

  Args:
    stderr: bool, True to get a writer that writes to stderr instead of stdout.

  Returns:
    ConsoleWriter, The configured stdout writer.  This writer is a stripped down
    file-like object that provides the basic writing methods.  When you write to
    this stream, it will be written to stdout only if CLI mode is enabled.  All
    strings will also be logged at DEBUG level to any registered log files.
  """
  InitLogging()
  if stderr:
    return _LogManager.instance.console_writer_stderr
  return _LogManager.instance.console_writer_stdout


class _BaseFormatter(logging.Formatter):
  """Class to set the format based on log level."""
  DEFAULT = '%(levelname)s: %(message)s'
  FORMATS = {logging.INFO: '%(message)s'}

  def format(self, record):
    self._fmt = _BaseFormatter.FORMATS.get(record.levelno,
                                           _BaseFormatter.DEFAULT)
    return logging.Formatter.format(self, record)


class _NullHandler(logging.Handler, object):
  """A replication of python2.7's logging.NullHandler.

  We recreate this class here to ease python2.6 compatibility.
  """

  def handle(self, record):
    pass

  def emit(self, record):
    pass

  def createLock(self):
    self.lock = None


class _MaximumLevelFilter(logging.Filter, object):
  """A logging filter that blocks messages greater than the given level."""

  def __init__(self, max_level):
    """Creates the filter.

    Args:
      max_level: logging level enum, The maximum level to allow through.  Levels
        greater than this are blocked.
    """
    super(_MaximumLevelFilter, self).__init__()
    self.__max_level = max_level

  def filter(self, logRecord):
    """Inherited from logging.Filter."""
    return logRecord.levelno <= self.__max_level


class _InfoFilter(logging.Filter, object):
  """A verbosity filter that treats all messages as INFO.

  This filter is used by the ConsoleWriter which does not actually use logging
  levels.  It just assumes that all messages are level INFO and determines if
  they should be printed or not.
  """

  def __init__(self, level=logging.INFO):
    """Creates the filter.

    Args:
      level: logging level, The level of logging that is enabled.
    """
    super(_InfoFilter, self).__init__()
    self.level = level

  def filter(self, unused_logRecord=None):
    return logging.INFO >= self.level


class _ConsoleWriter(object):
  """A class that wraps stdout or stderr so we can control how it gets logged.

  This class is a stripped down file-like object that provides the basic
  writing methods.  When you write to this stream, if it is enabled, it will be
  written to stdout.  All strings will also be logged at DEBUG level so they
  can be captured by the log file.
  """

  def __init__(self, logger, log_filter, stream):
    """Creates a new _ConsoleWriter wrapper.

    Args:
      logger: logging.Logger, The logger to log to.
      log_filter: logging.Filter, Used to determine whether to write or not.
      stream: output stream, stdout or stderr.
    """
    self.__logger = logger
    self.__filter = log_filter
    self.__stream = stream

  def Print(self, *msg):
    """Writes the given message to the output stream, and adds a newline.

    This method has the same output behavior as the build in print method but
    respects the configured verbosity.

    Args:
      *msg: str, The messages to print.
    """
    message = ' '.join([str(m) for m in msg])
    self.__logger.info(message)
    if self.__filter.filter():
      self.__stream.write(message + '\n')

  # pylint: disable=g-bad-name, This must match file-like objects
  def write(self, msg):
    self.__logger.info(msg)
    if self.__filter.filter():
      self.__stream.write(msg)

  # pylint: disable=g-bad-name, This must match file-like objects
  def writelines(self, lines):
    for line in lines:
      self.__logger.info(line)
    if self.__filter.filter():
      self.__stream.writelines(lines)

  # pylint: disable=g-bad-name, This must match file-like objects
  def flush(self):
    if self.__filter.filter():
      self.__stream.flush()


class _LogManager(object):
  """A class to manage the logging handlers based on how calliope is being used.

  We want to always log to a file, in addition to logging to stdout if in CLI
  mode.  This sets up the required handlers to do this.
  """
  FILE_ONLY_LOGGER_NAME = '___FILE_ONLY___'
  CONSOLE_LOGGER_NAME = '___CONSOLE___'
  FILE_FORMATTER = logging.Formatter(
      fmt='%(asctime)s %(levelname)-8s %(name)-15s %(message)s')

  MAX_AGE = 60 * 60 * 24 * 30  # 30 days' worth of seconds.

  instance = None

  def __init__(self, verbosity_num):
    """Clears all logging settings and initialize from scratch.

    The default settings logs WARNING and above to stderr.  If running in CLI
    mode, INFO will be pushed to stdout in the console.

    Args:
      verbosity_num: int, The verbosity determines what level of logs will show
        in the console.
    """
    self.verbosity_num = None
    self.logs_dirs = []
    base_formatter = _BaseFormatter()

    # Clears any existing logging handlers
    self.logger = logging.getLogger()
    self.logger.handlers[:] = []
    # Root logger accepts all levels
    self.logger.setLevel(logging.NOTSET)

    # A handler to redirect WARNING and above to stderr, this one is standard.
    self.stderr_handler = logging.StreamHandler(sys.stderr)
    self.stderr_handler.setFormatter(base_formatter)
    self.stderr_handler.setLevel(logging.WARNING)
    self.logger.addHandler(self.stderr_handler)

    # A handler to redirect INFO messages and lower to stdout.
    self.stdout_handler = logging.StreamHandler(sys.stdout)
    self.stdout_handler.setFormatter(base_formatter)
    # Above INFO will be handled by the stderr_handler.
    self.stdout_handler.addFilter(_MaximumLevelFilter(logging.INFO))
    self.console_logger = logging.getLogger(_LogManager.CONSOLE_LOGGER_NAME)
    self.console_logger.handlers[:] = []
    self.console_logger.setLevel(logging.NOTSET)
    self.console_logger.addHandler(self.stdout_handler)

    # This logger will get handlers for each output file, but will not propagate
    # to the root logger.  This allows us to log exceptions and errors to the
    # files without it showing up in the terminal.
    self.file_only_logger = logging.getLogger(_LogManager.FILE_ONLY_LOGGER_NAME)
    self.file_only_logger.handlers[:] = []
    # Accept all log levels for files.
    self.file_only_logger.setLevel(logging.NOTSET)
    self.file_only_logger.addHandler(_NullHandler())
    self.file_only_logger.propagate = False

    self.info_filter = _InfoFilter()
    self.console_writer_stdout = _ConsoleWriter(self.file_only_logger,
                                                self.info_filter, sys.stdout)
    self.console_writer_stderr = _ConsoleWriter(self.file_only_logger,
                                                self.info_filter, sys.stderr)

    self.SetVerbosity(verbosity_num)

  def SetVerbosity(self, verbosity_num):
    """Sets the active verbosity for the logger.

    Args:
      verbosity_num: int, The verbosity number from the VERBOSITIES array.

    Returns:
      int, The current verbosity number.

    Raises:
      ValueError: If the verbosity is outisde the valid range.
    """
    if verbosity_num is None:
      verbosity_num = DEFAULT_INTERACTIVE_VERBOSITY
    if verbosity_num < 0 or verbosity_num >= len(VERBOSITIES):
      raise ValueError('Invalid logging level: ' + str(verbosity_num))

    if self.verbosity_num == verbosity_num:
      return self.verbosity_num

    verbosity = VERBOSITIES[verbosity_num]

    self.stderr_handler.setLevel(max(logging.WARNING, verbosity.level))
    self.stdout_handler.setLevel(verbosity.level)
    self.info_filter.level = verbosity.level

    old_verbosity_num = self.verbosity_num
    self.verbosity_num = verbosity_num
    return old_verbosity_num

  def AddLogsDir(self, logs_dir):
    """Adds a new logging directory to the logging config.

    Args:
      logs_dir: str, Path to a directory to store log files under.  This method
        has no effect if this is None, or if this directory has already been
        registered.
    """
    if not logs_dir or logs_dir in self.logs_dirs:
      return
    self.logs_dirs.append(logs_dir)
    # A handler to write DEBUG and above to log files in the given directory
    log_file = self._SetupLogsDir(logs_dir)
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.NOTSET)
    file_handler.setFormatter(_LogManager.FILE_FORMATTER)
    self.logger.addHandler(file_handler)
    self.file_only_logger.addHandler(file_handler)

  def _SetupLogsDir(self, logs_dir):
    """Creates the necessary log directories and get the file name to log to.

    Logs are created under the given directory.  There is a sub-directory for
    each day, and logs for individual invocations are created under that.

    Deletes files in this directory that are older than MAX_AGE.

    Args:
      logs_dir: str, Path to a directory to store log files under

    Returns:
      str, The path to the file to log to
    """
    now = datetime.datetime.now()
    nowseconds = time.time()

    # First delete log files in this directory that are older than MAX_AGE.
    for (dirpath, dirnames, filenames) in os.walk(logs_dir, topdown=True):
      # We skip any directories with a too-new st_mtime. This skipping can
      # result in some false negatives, but that's ok since the files in the
      # skipped directory are at most one day too old.
      dirnames_include = []
      for dirname in dirnames:
        logdirpath = os.path.join(dirpath, dirname)
        stat_info = os.stat(logdirpath)
        age = nowseconds - stat_info.st_mtime
        if age < _LogManager.MAX_AGE:
          dirnames_include.append(dirname)
      dirnames[:] = dirnames_include

      for filename in filenames:
        # Skip if filename is not formatted like a log file.
        unused_non_ext, ext = os.path.splitext(filename)
        if ext != '.log':
          continue

        filepath = os.path.join(dirpath, filename)
        # Skip if the file is younger than MAX_AGE.
        stat_info = os.stat(filepath)
        age = nowseconds - stat_info.st_mtime
        if age < _LogManager.MAX_AGE:
          continue

        # This log file is too old.
        os.remove(filepath)

    # Second, delete any log directories that are now empty.
    for (dirpath, dirnames, filenames) in os.walk(logs_dir, topdown=False):
      # Since topdown is false, we get the children before the parents.
      if filenames or dirnames:
        continue

      # Nothing in it, so it's safe to delete.
      os.rmdir(dirpath)

    day_dir_name = now.strftime('%Y.%m.%d')
    day_dir_path = os.path.join(logs_dir, day_dir_name)
    try:
      os.makedirs(day_dir_path)
    except OSError as ex:
      if ex.errno == errno.EEXIST and os.path.isdir(day_dir_path):
        pass
      else:
        raise

    filename = '{timestamp}.log'.format(timestamp=now.strftime('%H.%M.%S.%f'))
    log_file = os.path.join(day_dir_path, filename)
    return log_file
