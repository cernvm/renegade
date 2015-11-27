# Copyright 2013 Google Inc. All Rights Reserved.

"""Exceptions that can be thrown by calliope tools.

The exceptions in this file, and those that extend them, can be thrown by
the Run() function in calliope tools without worrying about stack traces
littering the screen in CLI mode. In interpreter mode, they are not caught
from within calliope.
"""

from functools import wraps
import os
import sys

from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_attr_os


class ToolException(core_exceptions.Error):
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
      file_logger = log.file_only_logger
      file_logger.error('Handling the source of a tool exception, '
                        'original details follow.')
      file_logger.exception(current_exception)

    if args:
      return ToolException(*args)
    elif current_exception:
      return ToolException(*current_exception.args)
    return ToolException('An unknown error has occurred')


class ExitCodeNoError(core_exceptions.Error):
  """A special exception for exit codes without error messages.

  If this exception is raised, it's identical in behavior to returning from
  the command code, except the overall exit code will be different.
  """


class FailedSubCommand(core_exceptions.Error):
  """Exception capturing a subcommand which did sys.exit(code)."""

  def __init__(self, cmd, code):
    super(FailedSubCommand, self).__init__(
        'Failed command: [{0}] with exit code [{1}]'.format(
            ' '.join(cmd), code),
        exit_code=code)


def RaiseToolExceptionInsteadOf(*error_types):
  """RaiseToolExceptionInsteadOf is a decorator that re-raises as ToolException.

  If any of the error_types are raised in the decorated function, this decorator
  will re-raise the as a ToolException.

  Args:
    *error_types: [Exception], A list of exception types that this decorator
        will watch for.

  Returns:
    The decorated function.
  """
  def Wrap(func):
    """Wrapper function for the decorator."""
    @wraps(func)
    def TryFunc(*args, **kwargs):
      try:
        return func(*args, **kwargs)
      except error_types:
        (_, _, exc_traceback) = sys.exc_info()
        # The 3 element form takes (type, instance, traceback).  If the first
        # element is an instance, it is used as the type and instance and the
        # second element must be None.  This preserves the original traceback.
        # pylint:disable=nonstandard-exception, ToolException is an Exception.
        raise ToolException.FromCurrent(), None, exc_traceback
    return TryFunc
  return Wrap


def _TruncateToLineWidth(string, align, width, fill=''):
  """Truncate string to line width, right aligning at align.

  Examples (assuming a screen width of 10):

  >>> _TruncateToLineWidth('foo', 0)
  'foo'
  >>> # Align to the beginning. Should truncate the end.
  ... _TruncateToLineWidth('0123456789abcdef', 0)
  '0123456789'
  >>> _TruncateToLineWidth('0123456789abcdef', 0, fill='...')
  '0123456...'
  >>> # Align to the end. Should truncate the beginning.
  ... _TruncateToLineWidth('0123456789abcdef', 16)
  '6789abcdef'
  >>> _TruncateToLineWidth('0123456789abcdef', 16, fill='...')
  '...9abcdef'
  >>> # Align to the middle (note: the index is toward the end of the string,
  ... # because this function right-aligns to the given index).
  ... # Should truncate the begnining and end.
  ... _TruncateToLineWidth('0123456789abcdef', 12)
  '23456789ab'
  >>> _TruncateToLineWidth('0123456789abcdef', 12, fill='...')
  '...5678...'

  Args:
    string: string to truncate
    align: index to right-align to
    width: maximum length for the resulting string
    fill: if given, indicate truncation with this string. Must be shorter than
      terminal width / 2.

  Returns:
    str, the truncated string

  Raises:
    ValueError, if provided fill is too long for the terminal.
  """
  if len(fill) >= width / 2:
    # Either the caller provided a fill that's way too long, or the user has a
    # terminal that's way too narrow. In either case, we aren't going to be able
    # to make this look nice, but we don't want to throw an error because that
    # will mask the original error.
    log.warn('Screen not wide enough to display correct error message.')
    return string

  if len(string) <= width:
    return string

  if align > width:
    string = fill + string[align-width+len(fill):]

  if len(string) <= width:
    return string
  string = string[:width-len(fill)] + fill
  return string


_MARKER = '^ invalid character'


# pylint: disable=g-doc-bad-indent
def _FormatNonAsciiMarkerString(args_string):
  u"""Format a string that will mark the first non-ASCII character it contains.


  Example:

  >>> args = 'command.py --foo=\xce\x94'
  >>> _FormatNonAsciiMarkerString(args) == (
  ...     'command.py --foo=\u0394\n'
  ...     '                 ^ invalid character'
  ... )
  True

  Args:
    args_string: str representing the command executed

  Returns:
    unicode, a properly formatted string with two lines, the second of which
      indicates the non-ASCII character in the first.

  Raises:
    ValueError: if the given string is all ASCII characters
  """
  # idx is the first index of the first non-ASCII character in args_string
  idx = None
  for idx, char in enumerate(args_string):
    try:
      char.decode('ascii')
      # idx gets set by enumerate; unset it to indicate that the last character
      # was successfully decoded as ASCII
      idx = None
    except UnicodeError:
      # idx will remain set, indicating the first non-ASCII character
      break
  if idx is None:
    raise ValueError('Given string is composed entirely of ASCII characters.')

  # Make a string that, when printed in parallel, will point to the non-ASCII
  # character
  marker_string = ' ' * idx + _MARKER

  # Make sure that this will still print out nicely on an odd-sized screen
  align = len(marker_string)
  args_string = args_string.decode('utf-8', 'replace')
  width, _ = console_attr_os.GetTermSize()
  fill = '...'
  if width < len(_MARKER) + len(fill):
    # It's hopeless to try to wrap this and make it look nice. Preserve it in
    # full for logs and so on.
    return '\n'.join((args_string, marker_string))
  # If len(args_string) < width < len(marker_string) (ex:)
  #
  #   args_string   = 'command BAD'
  #   marker_string = '        ^ invalid character'
  #   width     = len('----------------')
  #
  # then the truncation can give a result like the following:
  #
  #   args_string   = 'command BAD'
  #   marker_string = '   ^ invalid character'
  #
  # (This occurs when args_string is short enough to not be truncated, but
  # marker_string is long enough to be truncated.)
  #
  # ljust args_string to make it as long as marker_string before passing to
  # _TruncateToLineWidth, which will yield compatible truncations. rstrip at the
  # end to get rid of the new trailing spaces.
  formatted_args_string = _TruncateToLineWidth(args_string.ljust(align), align,
                                               width, fill=fill).rstrip()
  formatted_marker_string = _TruncateToLineWidth(marker_string, align, width)
  return '\n'.join((formatted_args_string, formatted_marker_string))


class InvalidCharacterInArgException(ToolException):
  """InvalidCharacterInArgException is for non-ASCII CLI arguments."""

  def __init__(self, args, invalid_arg):
    self.invalid_arg = invalid_arg
    args = [os.path.basename(args[0])] + args[1:]

    super(InvalidCharacterInArgException, self).__init__(
        u'Failed to read command line argument [{0}] because it does '
        u'not appear to be valid 7-bit ASCII. (Argument is composed of '
        u'bytes [{1}].)\n\n'
        u'{2}'.format(
            self.invalid_arg.decode('utf-8', 'replace'),
            str(repr(invalid_arg))[1:-1],  # get rid of surrounding quotes
            _FormatNonAsciiMarkerString(' '.join(args))))


class HttpException(ToolException):
  """HttpException is raised whenever the Http response status code != 200."""

  def __init__(self, error):
    super(HttpException, self).__init__(error)
    self.error = error


class InvalidArgumentException(ToolException):
  """InvalidArgumentException is for malformed arguments."""

  def __init__(self, parameter_name, message):
    super(InvalidArgumentException, self).__init__(
        'Invalid value for [{0}]: {1}'.format(parameter_name, message))
    self.parameter_name = parameter_name


class UnknownArgumentException(ToolException):
  """UnknownArgumentException is for arguments with unexpected values."""

  def __init__(self, parameter_name, message):
    super(UnknownArgumentException, self).__init__(
        'Unknown value for [{0}]: {1}'.format(parameter_name, message))
    self.parameter_name = parameter_name


class RequiredArgumentException(ToolException):
  """An exception for when a usually optional argument is required in this case.
  """

  def __init__(self, parameter_name, message):
    super(RequiredArgumentException, self).__init__(
        'Missing required argument [{0}]: {1}'.format(parameter_name, message))
    self.parameter_name = parameter_name


class BadFileException(ToolException):
  """BadFileException is for problems reading or writing a file."""
