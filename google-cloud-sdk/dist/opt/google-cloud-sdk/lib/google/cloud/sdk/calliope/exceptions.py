# Copyright 2013 Google Inc. All Rights Reserved.

"""Exceptions that can be thrown by calliope tools.

The exceptions in this file, and those that extend them, can be thrown by
the Run() function in calliope tools without worrying about stack traces
littering the screen in CLI mode. In interpreter mode, they are not caught
from within calliope.
"""

from functools import wraps
import sys

from google.cloud.sdk.core import log


class ToolException(Exception):
  """ToolException is for Run methods to throw for non-code-bug errors.

  Attributes:
    command_name: The dotted group and command name for the command that threw
        this exception. This value is set by calliope.
  """

  @staticmethod
  def FromCurrent(*args):
    """Creates a new ToolException based on the current exception being handled.

    If no exception is being handled, a new ToolException with the given args
    is created.  If there is a current exception, the original exception is
    first logged (to file only).  A new ToolException is then created with the
    same args as the current one.

    Args:
      *args: The standard args taken by the constructor of Exception for the new
        exception that is created.  If None, the args from the exception
        currently being handled will be used.

    Returns:
      The generated ToolException.
    """
    (_, current_exception, _) = sys.exc_info()

    # Log original exception details and traceback to the log file if we are
    # currently handling an exception.
    if current_exception:
      file_logger = log.FileOnlyLogger()
      file_logger.error('Handling the source of a tool exception, '
                        'original details follow.')
      file_logger.exception(current_exception)

    if args:
      return ToolException(*args)
    elif current_exception:
      return ToolException(*current_exception.args)
    return ToolException('An unknown error has occurred')

  def __init__(self, *args, **kwargs):
    super(ToolException, self).__init__(*args, **kwargs)
    self.command_name = 'Uknown Command'

  def __str__(self):
    return '({0}) {1}'.format(self.command_name,
                              super(ToolException, self).__str__())


def RaiseToolExceptionInsteadOf(*error_types):
  """RaiseToolExceptionInsteadOf is a decorator that reraises as ToolException.

  If any of the error_types are raised in the decorated function, this decorator
  will reraise the as a ToolException.

  Args:
    *error_types: [Exception], A list of exception types that this decorator
        will watch for.

  Returns:
    The decorated function.
  """
  def Wrap(func):
    @wraps(func)
    def TryFunc(*args, **kwargs):
      try:
        return func(*args, **kwargs)
      except error_types:
        # pylint:disable=nonstandard-exception, ToolException is an Exception.
        raise ToolException.FromCurrent()
    return TryFunc
  return Wrap


class InvalidArgumentException(ToolException):
  """InvalidArgumentException is for malformed arguments."""

  def __init__(self, parameter_name, message):
    self.parameter_name = parameter_name
    self.message = message
    super(InvalidArgumentException, self).__init__(
        'Invalid value for {0}: {1}'.format(
            self.parameter_name,
            self.message))


class HttpException(ToolException):
  """HttpException is raised whenever the Http response status code != 200."""

  def __init__(self, error):
    super(HttpException, self).__init__(error)
    self.error = error


class UnknownArgumentException(ToolException):
  """UnknownArgumentException is for arguments with unexpected values."""

  def __init__(self, parameter_name, message):
    self.parameter_name = parameter_name
    self.message = message
    super(UnknownArgumentException, self).__init__(
        'Unknown value for {0}: {1}'.format(
            self.parameter_name,
            self.message))


class BadFileException(ToolException):
  """BadFileException is for problems reading or writing a file."""

