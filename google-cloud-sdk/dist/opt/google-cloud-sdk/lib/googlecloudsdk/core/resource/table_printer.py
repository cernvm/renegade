# Copyright 2014 Google Inc. All Rights Reserved.

"""Table format resource printer."""

import cStringIO
import json
import operator

from googlecloudsdk.core.console import console_attr
from googlecloudsdk.core.resource import resource_printer_base


# Table output column padding.
_TABLE_COLUMN_PAD = 2


def _Stringify(value):
  """Dumps value to JSON if it's not a string."""
  if value is None:
    return ''
  elif isinstance(value, (basestring, console_attr.Colorizer)):
    return value
  elif hasattr(value, '__str__'):
    return str(value)
  else:
    return json.dumps(value, sort_keys=True)


class TablePrinter(resource_printer_base.ResourcePrinter):
  """A printer for printing human-readable tables.

  Aligned left-adjusted columns with optional title, column headings and
  sorting. This format requires a projection to define the table columns. The
  default column headings are the disambiguated right hand components of the
  column keys in ANGRY_SNAKE_CASE. For example, the projection keys
  (first.name, last.name) produce the default column heading
  ('NAME', 'LAST_NAME').

  Printer attributes:
    box: Prints a box around the entire table and each cell, including the
      title if any.
    empty-legend=_SENTENCES_: Prints _SENTENCES_ to the *status* logger if there
      are no items. The default *empty-legend* is "Listed 0 items.".
      *no-empty-legend* disables the default.
    no-heading: Disables the column headings.
    legend=_SENTENCES_: Prints _SENTENCES_ to the *out* logger after the last
      item if there is at least one item.
    log=_TYPE_: Prints the legend to the _TYPE_ logger instead of the default.
      _TYPE_ may be: *out* (the default), *status* (standard error), *debug*,
      *info*, *warn*, or *error*.
    pad=N: Sets the column horizontal pad to _N_ spaces. The default is 1 for
      box, 2 otherwise.
    page=N: If _N_ > 0 then output is grouped into tables with _N_ rows. The
      last table may have less rows. Headings, alignment and sorting are done
      per-page. The title, if any, is printed before the first table. The
      legend, if any, is printed after the last table.
    title=_TITLE_: Prints a centered _TITLE_ at the top of the table, within
      the table box if *box* is enabled.

  Attributes:
    _page_count: The output page count, incremented before each page.
    _rows_per_page: The number of rows in each resource page. 0 mean no paging.
    _rows: The list of all resource columns indexed by row.
  """

  def __init__(self, *args, **kwargs):
    """Creates a new TablePrinter."""
    self._rows = []
    super(TablePrinter, self).__init__(*args, by_columns=True, **kwargs)
    encoding = None
    for name in ['ascii', 'utf8', 'win']:
      if name in self.attributes:
        encoding = name
        break
    self._console_attr = console_attr.GetConsoleAttr(encoding=encoding,
                                                     out=self._out)
    self._rows_per_page = self.attributes.get('page', 0)
    self._page_count = 0

  def _AddRecord(self, record, delimit=True):
    """Adds a list of columns. Output delayed until Finish().

    Args:
      record: A JSON-serializable object.
      delimit: Prints resource delimiters if True.
    """
    if self._rows_per_page and len(self._rows) >= self._rows_per_page:
      self._page_count += 1
      self.Finish(last_page=False)
      self._rows = []
    self._rows.append(record)

  def Finish(self, last_page=True):
    """Prints the table.

    Args:
      last_page: True if this is the last resource page.
    """
    if last_page and not self._rows:
      # Table is empty but there might be an empty legend.
      self.AddLegend()
      return

    # Border box decorations.
    if 'box' in self.attributes:
      box = self._console_attr.GetBoxLineCharacters()
      table_column_pad = 1
    else:
      box = None
      table_column_pad = self.attributes.get('pad', _TABLE_COLUMN_PAD)
      if self._page_count > 1:
        self._out.write('\n')

    # Determine the max column widths of heading + rows
    rows = [[_Stringify(cell) for cell in row] for row in self._rows]
    heading = []
    if 'no-heading' not in self.attributes:
      labels = self._heading or self.column_attributes.Labels()
      if labels:
        heading = [[_Stringify(cell) for cell in labels]]
    col_widths = [0] * max(len(x) for x in rows + heading)
    for row in rows + heading:
      for i in range(len(row)):
        col_widths[i] = max(col_widths[i], len(row[i]))

    # Print the title if specified.
    title = self.attributes.get('title') if self._page_count <= 1 else None
    if title is not None:
      if box:
        line = box.dr
      width = 0
      sep = 2
      for i in range(len(col_widths)):
        width += col_widths[i]
        if box:
          line += box.h * (col_widths[i] + sep)
        sep = 3
      if width < len(title):
        # Title is wider than the table => pad each column to make room.
        pad = (len(title) + len(col_widths) - 1) / len(col_widths)
        width += len(col_widths) * pad
        if box:
          line += box.h * len(col_widths) * pad
        for i in range(len(col_widths)):
          col_widths[i] += pad
      if box:
        width += 3 * len(col_widths) - 1
        line += box.dl
        self._out.write(line)
        self._out.write('\n')
        line = box.v + title.center(width) + box.v
      else:
        line = title.center(width)
      self._out.write(line)
      self._out.write('\n')

    # Set up box borders.
    if box:
      t_sep = box.vr if title else box.dr
      m_sep = box.vr
      b_sep = box.ur
      t_rule = ''
      m_rule = ''
      b_rule = ''
      for i in range(len(col_widths)):
        cell = box.h * (col_widths[i] + 2)
        t_rule += t_sep + cell
        t_sep = box.hd
        m_rule += m_sep + cell
        m_sep = box.vh
        b_rule += b_sep + cell
        b_sep = box.hu
      t_rule += box.vl if title else box.dl
      m_rule += box.vl
      b_rule += box.ul
      self._out.write(t_rule)
      self._out.write('\n')
      if heading:
        line = cStringIO.StringIO()
        row = heading[0]
        heading = []
        for i in range(len(row)):
          line.write(box.v + ' ')
          line.write(row[i].center(col_widths[i]))
          line.write(' ')
        line.write(box.v)
        self._out.write(line.getvalue())
        self._out.write('\n')
        self._out.write(m_rule)
        self._out.write('\n')

    # Sort by columns if requested.
    if self.column_attributes:
      # Order() is a list of (key,reverse) tuples from highest to lowest key
      # precedence. This loop partitions the keys into groups with the same
      # reverse value. The groups are then applied in reverse order to maintain
      # the original precedence.
      groups = []  # [(keys, reverse)] LIFO to preserve precedence
      keys = []  # keys for current group
      for key_index, key_reverse in self.column_attributes.Order():
        if not keys:
          # This only happens the first time through the loop.
          reverse = key_reverse
        if reverse != key_reverse:
          groups.insert(0, (keys, reverse))
          keys = []
          reverse = key_reverse
        keys.append(key_index)
      if keys:
        groups.insert(0, (keys, reverse))
      for keys, reverse in groups:
        rows = sorted(rows, key=operator.itemgetter(*keys), reverse=reverse)
      align = self.column_attributes.Alignments()
    else:
      align = None

    # Print the left-adjusted columns with space stripped from rightmost column.
    # We must flush directly to the output just in case there is a Windows-like
    # colorizer. This complicates the trailing space logic.
    for row in heading + rows:
      pad = 0
      for i in range(len(row)):
        if box:
          self._out.write(box.v + ' ')
          width = col_widths[i]
        elif i < len(row) - 1:
          width = col_widths[i]
        else:
          width = 0
        justify = align[i] if align else lambda s, w: s.ljust(w)
        cell = row[i]
        if isinstance(cell, console_attr.Colorizer):
          if pad:
            self._out.write(' ' * pad)
            pad = 0
          # pylint: disable=cell-var-from-loop
          cell.Render(justify=lambda s: justify(s, width))
          if box:
            self._out.write(' ' * table_column_pad)
          else:
            pad = table_column_pad
        else:
          value = justify(cell, width)
          if box:
            self._out.write(value)
            self._out.write(' ' * table_column_pad)
          elif value.strip():
            if pad:
              self._out.write(' ' * pad)
              pad = 0
            stripped = value.rstrip()
            self._out.write(stripped)
            pad = table_column_pad + len(value) - len(stripped)
          else:
            pad += table_column_pad + len(value)
      if box:
        self._out.write(box.v)
      self._out.write('\n')
    if box:
      self._out.write(b_rule)
      self._out.write('\n')

    # Print the legend if any.
    if last_page:
      self.AddLegend()
