# Copyright 2013 Google Inc. All Rights Reserved.

"""General console printing utilities used by the Cloud SDK."""

import logging
import sys
import textwrap

from google.cloud.sdk.core import log
from google.cloud.sdk.core import properties


class TablePrinter(object):
  """Provides the ability to print a list of items as a formatted table.

  Using this class helps you adhere to the gcloud style guide.

  The table will auto size the columns to fit the maximum item length for that
  column.  You can also choose how to justify each column and to add extra
  padding to each column.
  """

  JUSTIFY_LEFT = '<'
  JUSTIFY_RIGHT = '>'
  JUSTIFY_CENTER = '^'

  def __init__(self, headers, title=None,
               justification=None, column_padding=None):
    """Creates a new TablePrinter.

    Args:
      headers: A tuple of strings that represent the column headers titles.
        This can be a tuple of empty strings or None's if you do not want
        headers displayed.  The number of empty elements in the tuple must match
        the number of columns you want to display.
      title: str, An optional title for the table.
      justification: A tuple of JUSTIFY_LEFT, JUSTIFY_RIGHT, JUSTIFY_CENTER that
        describes the justification for each column.  This must have the same
        number of items as the headers tuple.
      column_padding: A tuple of ints that describes the extra padding that
        should be added to each column.  This must have the same
        number of items as the headers tuple.

    Raises:
      ValueError: If the justification or column_padding tuples are not of the
        correct type or length.
    """
    self.__headers = [h if h else '' for h in headers]
    self.__title = title
    self.__num_columns = len(self.__headers)
    self.__header_widths = [len(str(x)) for x in self.__headers]

    self.__column_padding = column_padding
    if self.__column_padding is None:
      self.__column_padding = tuple([0] * self.__num_columns)
    if (not isinstance(self.__column_padding, (tuple)) or
        len(self.__column_padding) != self.__num_columns):
      raise ValueError('Column padding tuple does not have {} columns'
                       .format(self.__num_columns))

    self.__justification = justification
    if self.__justification is None:
      self.__justification = tuple([TablePrinter.JUSTIFY_LEFT] *
                                   self.__num_columns)
    if (not isinstance(self.__justification, tuple) or
        len(self.__justification) != self.__num_columns):
      raise ValueError('Justification tuple does not have {} columns'
                       .format(self.__num_columns))
    for value in self.__justification:
      if not (value is TablePrinter.JUSTIFY_LEFT or
              value is TablePrinter.JUSTIFY_RIGHT or
              value is TablePrinter.JUSTIFY_CENTER):
        raise ValueError('Justification values must be one of JUSTIFY_LEFT, '
                         'JUSTIFY_RIGHT, or JUSTIFY_CENTER')

  def SetTitle(self, title):
    """Sets the title of the table.

    Args:
      title: str, The new title.
    """
    self.__title = title

  def Log(self, rows, logger=None, level=logging.INFO):
    """Logs the given rows to the given logger.

    Args:
      rows: list of tuples, The rows to log the formatted table for.
      logger: logging.Logger, The logger to do the logging.  If None, the root
        logger will be used.
      level: logging level, An optional override for the logging level, INFO by
        default.
    """
    if not logger:
      logger = log.ConsoleLogger()
    lines = self.GetLines(rows)
    for line in lines:
      logger.log(level, line)

  def Print(self, rows, output_stream=None, indent=0):
    """Prints the given rows to stdout.

    Args:
      rows: list of tuples, The rows to print the formatted table for.
      output_stream: file-like object, The stream to wire the rows to.  Defaults
        to log.ConsoleWriter() if not given.
      indent: int, The number of spaces to indent all lines of the table.
    """
    if not output_stream:
      output_stream = log.ConsoleWriter()
    lines = self.GetLines(rows, indent=indent)
    for line in lines:
      output_stream.write(line + '\n')

  def GetLines(self, rows, indent=0):
    """Gets a list of strings of formatted lines for the given rows.

    Args:
      rows: list of tuples, The rows to get the formatted table for.
      indent: int, The number of spaces to indent all lines of the table.

    Returns:
      list of str, The lines of the formatted table that can be printed.

    Raises:
      ValueError: If any row does not have the correct number of columns.
    """
    column_widths = list(self.__header_widths)
    for row in rows:
      if len(row) != self.__num_columns:
        raise ValueError('Row [{row}] does not have {rows} columns'
                         .format(row=row, rows=self.__num_columns))
      # Find the max width of each column
      for i in range(self.__num_columns):
        column_widths[i] = max(column_widths[i], len(str(row[i])))

    # Add padding
    column_widths = [column_widths[i] + self.__column_padding[i]
                     for i in range(self.__num_columns)]
    total_width = (len(column_widths) - 1) * 3
    for width in column_widths:
      total_width += width

    edge_line = ('--' +
                 '---'.join(['-' * width for width in column_widths]) +
                 '--')
    title_divider_line = ('|-' +
                          '---'.join(['-' * width for width in column_widths]) +
                          '-|')
    divider_line = ('|-' +
                    '-+-'.join(['-' * width for width in column_widths]) +
                    '-|')
    lines = [edge_line]

    if self.__title:
      title_line = '| {{title:{justify}{width}s}} |'.format(
          justify=TablePrinter.JUSTIFY_CENTER, width=total_width).format(
              title=self.__title)
      lines.append(title_line)
      lines.append(title_divider_line)

    # Generate format strings with the correct width for each column
    column_formats = []
    for i in range(self.__num_columns):
      column_formats.append('{{i{i}:{justify}{width}s}}'.format(
          i=i, justify=self.__justification[i], width=column_widths[i]))
    pattern = '| ' + ' | '.join(column_formats) + ' |'

    def _ParameterizedArrayDict(array):
      return dict(('i{i}'.format(i=i), array[i]) for i in range(len(array)))

    if [h for h in self.__headers if h]:
      # Only print headers if there is at least one non-empty header
      lines.append(pattern.format(**_ParameterizedArrayDict(self.__headers)))
      lines.append(divider_line)

    lines.extend([pattern.format(**_ParameterizedArrayDict(row))
                  for row in rows])
    lines.append(edge_line)

    if indent:
      return [(' ' * indent) + l for l in lines]
    return lines


class ListPrinter(object):
  """Provides the ability to print a list of items as a formatted list.

  Using this class helps you adhere to the gcloud style guide.
  """

  def __init__(self, title):
    """Create a titled list printer that can print rows to stdout.

    Args:
      title: A string for the title of the list.
    """
    self.__title = title

  def Print(self, rows, output_stream=None):
    """Print this list with the provided rows to stdout.

    Args:
      rows: A list of objects representing the rows of this list. Before being
          printed, they will be converted to strings.
      output_stream: file-like object, The stream to wire the rows to.  Defaults
        to log.ConsoleWriter() if not given.
    """
    if not output_stream:
      output_stream = log.ConsoleWriter()
    output_stream.write(self.__title + '\n')
    for row in rows:
      output_stream.write(' - ' + str(row) + '\n')


TEXTWRAP = textwrap.TextWrapper(replace_whitespace=False, drop_whitespace=False)


def _DoWrap(message):
  """Text wrap the given message and correctly handle newlines in the middle.

  Args:
    message: str, The message to wrap.  It may have newlines in the middle of
      it.

  Returns:
    str, The wrapped message.
  """
  return '\n'.join([TEXTWRAP.fill(line) for line in message.splitlines()])


def PromptContinue(message=None, prompt_string=None):
  """Prompts the user a yes or no question and asks if they want to continue.

  Args:
    message: str, The prompt to print before the question.
    prompt_string: str, An alternate yes/no prompt to display.  If None, it
      defaults to 'Do you want to continue'.

  Returns:
    bool, False if the user said no, True if the user said anything else or if
    prompts are disabled.
  """
  if properties.VALUES.core.disable_prompts.GetBool():
    return True
  if not prompt_string:
    prompt_string = 'Do you want to continue'
  if message:
    sys.stdout.write(_DoWrap(message) + '\n\n')

  sys.stdout.write(_DoWrap(prompt_string + ' (Y/n)?  '))
  while True:
    answer = raw_input()
    if not answer or answer in ['y', 'Y']:
      sys.stdout.write('\n')
      return True
    elif answer in ['n', 'N']:
      sys.stdout.write('\n')
      return False
    else:
      sys.stdout.write("Please enter 'y' or 'n':  ")


def PromptResponse(message):
  """Prompts the user for a string.

  Args:
    message: str, The prompt to print before the question.

  Returns:
    str, The string entered by the user, or None if prompts are disabled.
  """
  if properties.VALUES.core.disable_prompts.GetBool():
    return None
  response = raw_input(_DoWrap(message))
  return response


def PromptChoice(options, default=0, message=None, prompt_string=None):
  """Prompt the user to select a choice from a list of items.

  Args:
    options:  [object], A list of objects to print as choices.  Their str()
      method will be used to display them.
    default: int, The default index to return if prompting is disabled or if
      they do not enter a choice.
    message: str, An optional message to print before the choices are displayed.
    prompt_string: str, A string to print when prompting the user to enter a
      choice.  If not given, a default prompt is used.

  Raises:
    ValueError: If no options are given or if the default is not in the range of
      available options.

  Returns:
    The index of the item in the list that was chosen, or the deafult if prompts
    are disabled.
  """
  if not options:
    raise ValueError('You must provide at least one option.')
  maximum = len(options)
  if default < 0 or default >= maximum:
    raise ValueError(
        'Default option [{default}] is not a valid index for the options list '
        '[{maximum} options given]'.format(default=default, maximum=maximum))
  if properties.VALUES.core.disable_prompts.GetBool():
    return default

  if message:
    sys.stdout.write(_DoWrap(message) + '\n')
  for i, option in enumerate(options):
    sys.stdout.write('  [{index}]  {option}\n'.format(
        index=i+1, option=str(option)))

  if not prompt_string:
    prompt_string = 'Please enter your numeric choice'
  sys.stdout.write(_DoWrap(prompt_string + ' ({default}):  '.format(
      default=default+1)))
  while True:
    answer = raw_input()
    if not answer:
      sys.stdout.write('\n')
      return default
    try:
      num_choice = int(answer)
      if num_choice < 1 or num_choice > maximum:
        raise ValueError('Choice must be between 1 and {maximum}'.format(
            maximum=maximum))
      sys.stdout.write('\n')
      return num_choice - 1
    except ValueError:
      sys.stdout.write('Please enter a value between 1 and {maximum}:  '
                       .format(maximum=maximum))
