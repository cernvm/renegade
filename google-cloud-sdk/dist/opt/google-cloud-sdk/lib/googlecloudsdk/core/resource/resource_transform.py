# Copyright 2015 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Built-in resource transform functions.

A resource transform function converts a JSON-serializable resource to a string
value. This module contains built-in transform functions that may be used in
resource projection and filter expressions.

NOTICE: Each TransformFoo() method is the implementation of a foo() transform
function. Even though the implementation here is in Python the usage in resource
projection and filter expressions is language agnostic. This affects the
Pythonicness of the Transform*() methods:
  (1) The docstrings are used to generate external user documentation.
  (2) The method prototypes are included in the documentation. In particular the
      prototype formal parameter names are stylized for the documentation.
  (3) The 'r', 'kwargs', and 'projection' args are not included in the external
      documentation. Docstring descriptions, other than the Args: line for the
      arg itself, should not mention these args. Assume the reader knows the
      specific item the transform is being applied to. When in doubt refer to
      the output of $ gcloud topic projections.
  (4) The types of some args, like r, are not fixed until runtime. Other args
      may have either a base type value or string representation of that type.
      It is up to the transform implementation to silently do the string=>type
      conversions. That's why you may see e.g. int(arg) in some of the methods.
  (5) Unless it is documented to do so, a transform function must not raise any
      exceptions related to the resource r. The `undefined' arg is used to
      handle all unusual conditions, including ones that would raise exceptions.
      Exceptions for arguments explicitly under the caller's control are OK.
"""

import datetime
import re
import StringIO
import urllib2

from googlecloudsdk.core.console import console_attr
from googlecloudsdk.core.resource import resource_exceptions
from googlecloudsdk.core.resource import resource_property
from googlecloudsdk.core.util import times


def GetBooleanArgValue(arg):
  """Returns the Boolean value for arg."""
  if arg in (True, False):
    return arg
  if not arg:
    return False
  try:
    if arg.lower() == 'false':
      return False
  except AttributeError:
    pass
  try:
    return bool(float(arg))
  except ValueError:
    pass
  return True


def _GetKeyValue(r, key, undefined=None):
  """Returns the value for key in r.

  Args:
    r: The resource object.
    key: The dotted attribute name.
    undefined: This is returned if key is not in r.

  Returns:
    The value for key in r.
  """
  # Circular dependency on resource_lex for
  #   parsed_key = resource_lex.Lexer(key).Key()
  # so we settle for simple keys here.
  parsed_key = key.split('.')
  return resource_property.Get(r, parsed_key, undefined)


def TransformAlways(r):
  """Marks a transform sequence to always be applied.

  In some cases transforms are disabled. Prepending always() to a transform
  sequence causes the sequence to always be evaluated.

  Example:
    some_field.always().foo().bar() will always apply foo() and then bar().

  Args:
    r: A resource.

  Returns:
    r.
  """
  # This method is used as a decorator in transform expressions. It is
  # recognized at parse time and discarded.
  return r


def TransformBaseName(r, undefined=''):
  """Returns the last path component.

  Args:
    r: A URI or unix/windows file path.
    undefined: Returns this value if the resource or basename is empty.

  Returns:
    The last path component.
  """
  if not r:
    return undefined
  s = unicode(r)
  for separator in ('/', '\\'):
    i = s.rfind(separator)
    if i >= 0:
      return s[i + 1:]
  return s or undefined


def TransformCollection(r, undefined=''):  # pylint: disable=unused-argument
  """Returns the current resource collection.

  Args:
    r: A JSON-serializable object.
    undefined: This value is returned if r or the collection is empty.

  Returns:
    The current resource collection, undefined if unknown.
  """
  # This method will most likely be overridden by a resource printer.
  return undefined


def TransformColor(r, red=None, yellow=None, green=None, blue=None, **kwargs):
  """Colorizes the resource string value.

  The resource string is searched for an RE pattern match in Roy.G.Biv order.
  The first pattern that matches colorizes the resource string with that color.

  Args:
    r: A JSON-serializable object.
    red: Color red resource value pattern.
    yellow: Color yellow resource value pattern.
    green: Color green resource value pattern.
    blue: Color blue resource value pattern.
    **kwargs: console_attr.Colorizer() kwargs.

  Returns:
    A console_attr.Colorizer() object if any color substring matches, r
    otherwise.
  """
  string = unicode(r)
  for color, pattern in (('red', red), ('yellow', yellow), ('green', green),
                         ('blue', blue)):
    if pattern and re.search(pattern, string):
      return console_attr.Colorizer(string, color, **kwargs)
  return string


# pylint: disable=redefined-builtin, external expression expects format kwarg.
def TransformDate(r, format='%Y-%m-%dT%H:%M:%S', unit=1, undefined='',
                  tz=None, tz_default=None):
  """Formats the resource as a strftime() format.

  Args:
    r: A timestamp number or an object with 3 or more of these fields: year,
      month, day, hour, minute, second, millisecond, microsecond, nanosecond.
    format: The strftime(3) format.
    unit: If the resource is a Timestamp then divide by _unit_ to yield seconds.
    undefined: Returns this value if the resource is not a valid time.
    tz: Return the time relative to the tz timezone if specified, the explicit
      timezone in the resource if it has one, otherwise the local timezone.
      For example, ...date(tz=EST5EDT, tz_default=UTC).
    tz_default: The default timezone if the resource does not have a timezone
      suffix.

  Returns:
    The strftime() date format for r or undefined if r does not contain a valid
    time.
  """
  # Check if r has an isoformat() method.
  try:
    r = r.isoformat()
  except (AttributeError, TypeError, ValueError):
    pass

  tz_in = times.GetTimeZone(tz_default) if tz_default else None
  # Check if r is a timestamp.
  try:
    timestamp = float(r) / float(unit)
    dt = times.GetDateTimeFromTimeStamp(timestamp, tz_in)
    return times.FormatDateTime(dt, format)
  except (TypeError, ValueError):
    pass

  # Check if r is a serialized datetime object.
  original_repr = resource_property.Get(r, ['datetime'], None)
  if original_repr and isinstance(original_repr, basestring):
    r = original_repr

  tz_out = times.GetTimeZone(tz) if tz else None
  # Check if r is a date/time string.
  try:
    dt = times.ParseDateTime(r, tz_in)
    return times.FormatDateTime(dt, format, tz_out)
  except (AttributeError, ImportError, TypeError, ValueError):
    pass

  def _FormatFromParts():
    """Returns the formatted time from broken down time parts in r.

    Raises:
      TypeError: For invalid time part errors.
      ValueError: For time conversion errors or not enough valid time parts.

    Returns:
      The formatted time from broken down time parts in r.
    """
    valid = 0
    parts = []
    now = datetime.datetime.now(tz_in)
    for part in ('year', 'month', 'day', 'hour', 'minute', 'second'):
      value = resource_property.Get(r, [part], None)
      if value is None:
        # Missing parts default to now.
        value = getattr(now, part, 0)
      else:
        valid += 1
      parts.append(int(value))
    # The last value is microseconds. Add in any subsecond parts but don't count
    # them in the validity check.
    parts.append(0)
    for i, part in enumerate(['nanosecond', 'microsecond', 'millisecond']):
      value = resource_property.Get(r, [part], None)
      if value is not None:
        parts[-1] += int(int(value) * 1000 ** (i - 1))
    # year&month&day or hour&minute&second would be OK, "3" covers those and any
    # combination of 3 non-subsecond date/time parts.
    if valid < 3:
      raise ValueError
    parts.append(tz_in)
    dt = datetime.datetime(*parts)
    return times.FormatDateTime(dt, format, tz_out)

  try:
    return _FormatFromParts()
  except (TypeError, ValueError):
    pass

  # Does anyone really know what time it is?
  return undefined


def TransformDecode(r, encoding, undefined=''):
  """Returns the decoded value of the resource that was encoded by encoding.

  Args:
    r: A JSON-serializable object.
    encoding: The encoding name. *base64* and *utf-8* are supported.
    undefined: Returns this value if the decoding fails.

  Returns:
    The decoded resource.
  """
  # Some codecs support 'replace', all support 'strict' (the default).
  for errors in ('replace', 'strict'):
    try:
      return r.decode(encoding, errors)
    except:  # pylint: disable=bare-except, undefined for any exception
      pass
  return undefined


def TransformDuration(r, start='', end='', parts=3, precision=3, calendar=True,
                      unit=1, undefined=''):
  """Formats the resource as an ISO 8601 duration string.

  The [ISO 8601 Duration](https://en.wikipedia.org/wiki/ISO_8601#Durations)
  format is: "[-]P[nY][nM][nD][T[nH][nM][n[.m]S]]". The 0 duration is "P0".
  Otherwise at least one part will always be displayed. Negative durations are
  prefixed by "-". "T" disambiguates months "P2M" to the left of "T" and minutes
  "PT5M" to the right.

  If the resource is a datetime then the duration of `resource - current_time`
  is returned.

  Args:
    r: A JSON-serializable object.
    start: The name of a start time attribute in the resource. The duration of
      the `end - start` time attributes in resource is returned. If `end` is
      not specified then the current time is used.
    end: The name of an end time attribute in the resource. Defaults to
      the current time if omitted. Ignored if `start` is not specified.
    parts: Format at most this many duration parts starting with largest
      non-zero part.
    precision: Format the last duration part with precision digits after the
      decimal point. Trailing "0" and "." are always stripped.
    calendar: Allow time units larger than hours in formated durations if true.
      Durations specifying hours or smaller units are exact across daylight
      savings time boundaries. On by default. Use calendar=false to disable.
      For example, if `calendar=true` then at the daylight savings boundary
      2016-03-13T01:00:00 + P1D => 2016-03-14T01:00:00 but 2016-03-13T01:00:00 +
      PT24H => 2016-03-14T03:00:00. Similarly, a +P1Y duration will be inexact
      but "calendar correct", yielding the same month and day number next year,
      even in leap years.
    unit: Divide the resource numeric value by _unit_ to yield seconds.
    undefined: Returns this value if the resource is not a valid timestamp.

  Returns:
    The ISO 8601 duration string for r or undefined if r is not a duration.
  """
  try:
    parts = int(parts)
    precision = int(precision)
  except ValueError:
    return undefined
  calendar = GetBooleanArgValue(calendar)

  if start:
    # Duration of ((end or Now()) - start).

    # Get the datetime of both.
    try:
      start_datetime = times.ParseDateTime(_GetKeyValue(r, start))
      end_value = _GetKeyValue(r, end) if end else None
      if end_value:
        end_datetime = times.ParseDateTime(end_value)
      else:
        end_datetime = times.Now(tzinfo=start_datetime.tzinfo)
    except (AttributeError, ImportError, TypeError, ValueError):
      return undefined

    # Finally format the duration of the delta.
    delta = end_datetime - start_datetime
    return times.GetDurationFromTimeDelta(
        delta=delta, calendar=calendar).Format(parts=parts, precision=precision)

  # Check if the resource is a float duration.
  try:
    duration = times.ParseDuration('PT{0}S'.format(float(r) / unit),
                                   calendar=calendar)
    return duration.Format(parts=parts, precision=precision)
  except (TypeError, ValueError):
    pass

  # Check if the resource is an ISO 8601 duration.
  try:
    duration = times.ParseDuration(r)
    return duration.Format(parts=parts, precision=precision)
  except (AttributeError, TypeError, ValueError):
    pass

  # Check if the resource is a datetime.
  try:
    start_datetime = times.ParseDateTime(r)
  except (AttributeError, ImportError, TypeError, ValueError):
    return undefined

  # Format the duration of (now - r).
  end_datetime = times.Now(tzinfo=start_datetime.tzinfo)
  delta = end_datetime - start_datetime
  return times.GetDurationFromTimeDelta(delta=delta, calendar=calendar).Format(
      parts=parts, precision=precision)


def TransformEncode(r, encoding, undefined=''):
  """Returns the encoded value of the resource using encoding.

  Args:
    r: A JSON-serializable object.
    encoding: The encoding name. *base64* and *utf-8* are supported.
    undefined: Returns this value if the encoding fails.

  Returns:
    The encoded resource.
  """
  # Some codecs support 'replace', all support 'strict' (the default).
  for errors in ('replace', 'strict'):
    try:
      return r.encode(encoding, errors).rstrip('\n')
    except:  # pylint: disable=bare-except, undefined for any exception
      pass
  return undefined


def TransformEnum(r, projection, enums, inverse=False, undefined=''):
  """Returns the enums dictionary description for the resource.

  Args:
    r: A JSON-serializable object.
    projection: The parent ProjectionSpec.
    enums: The name of a message enum dictionary.
    inverse: Do inverse lookup if true.
    undefined: Returns this value if there is no matching enum description.

  Returns:
    The enums dictionary description for the resource.
  """
  inverse = GetBooleanArgValue(inverse)
  type_name = GetTypeDataName(enums, 'inverse-enum' if inverse else 'enum')
  descriptions = projection.symbols.get(type_name)
  if not descriptions and inverse:
    normal = projection.symbols.get(GetTypeDataName(enums, 'enum'))
    if normal:
      # Create the inverse dict and memoize it in projection.symbols.
      descriptions = {}
      for k, v in normal.iteritems():
        descriptions[v] = k
      projection.symbols[type_name] = descriptions
  return descriptions.get(r, undefined) if descriptions else undefined


def TransformError(r, message=None):
  """Raises an Error exception that does not generate a stack trace.

  Args:
    r: A JSON-serializable object.
    message: An error message. If not specified then the resource is formatted
      as the error message.

  Raises:
    Error: This will not generate a stack trace.
  """
  if message is None:
    message = unicode(r)
  raise resource_exceptions.Error(message)


def TransformExtract(r, *keys):
  """Extract an ordered list of values from the resource for the specified keys.

  Args:
    r: A JSON-serializable object.
    *keys: The list of keys in the resource whose associated values will be
        included in the result.

  Returns:
    The list of extracted values.
  """
  try:
    return [r[k] for k in keys if k in r]
  except TypeError:
    return []


def TransformFatal(r, message=None):
  """Raises an InternalError exception that generates a stack trace.

  Args:
    r: A JSON-serializable object.
    message: An error message. If not specified then the resource is formatted
      as the error message.

  Raises:
    InternalError: This generates a stack trace.
  """
  raise resource_exceptions.InternalError(message if message is not None
                                          else str(r))


def TransformFirstOf(r, *args):
  """Returns the first non-empty .name attribute value for name in args.

  Args:
    r: A JSON-serializable object.
    *args: Names to check for resource attribute values,

  Returns:
    The first non-empty r.name value for name in args, '' otherwise.

  Example:
    x.firstof(bar_foo, barFoo, BarFoo, BAR_FOO) will check x.bar_foo, x.barFoo,
    x.BarFoo, and x.BAR_FOO in order for the first non-empty value.
  """
  for name in args:
    v = resource_property.Get(r, [name], None)
    if v is not None:
      return v
  return ''


def TransformFloat(r, precision=6, spec=None, undefined=''):
  """Returns the string representation of a floating point number.

  One of these formats is used (1) ". _precision_ _spec_" if _spec_ is specified
  (2) ". _precision_" unless 1e-04 <= abs(number) < 1e+09 (3) ".1f" otherwise.

  Args:
    r: A JSON-serializable object.
    precision: The maximum number of digits before and after the decimal point.
    spec: The printf(3) floating point format "e", "f" or "g" spec character.
    undefined: Returns this value if the resource is not a float.

  Returns:
    The string representation of the floating point number r.
  """
  # TransformFloat vs. float.str() comparison:
  #
  #   METHOD          PRECISION   NO-EXPONENT-RANGE
  #   TransformFloat()        6   1e-04 <= x < 1e+9
  #   float.str()            12   1e-04 <= x < 1e+11
  #
  # The TransformFloat default avoids implementation dependent floating point
  # roundoff differences in the fraction digits.
  #
  # round(float(r), precision) won't work here because it only works for
  # significant digits immediately after the decimal point. For example,
  # round(0.0000000000123456789, 6) is 0, not 1.23457e-11.

  try:
    number = float(r)
  except (TypeError, ValueError):
    return undefined
  if spec is not None:
    fmt = '{{number:.{precision}{spec}}}'.format(precision=precision, spec=spec)
    return fmt.format(number=number)
  fmt = '{{number:.{precision}}}'.format(precision=precision)
  representation = fmt.format(number=number)
  exponent_index = representation.find('e+')
  if exponent_index >= 0:
    exponent = int(representation[exponent_index + 2:])
    if exponent < 9:
      return '{number:.1f}'.format(number=number)
  return representation


# The 'format' transform is special: it has no kwargs and the second argument
# is the ProjectionSpec of the calling projection.
def TransformFormat(r, projection, fmt, *args):
  """Formats resource key values.

  Args:
    r: A JSON-serializable object.
    projection: The parent ProjectionSpec.
    fmt: The format string with {0} ... {nargs-1} references to the resource
      attribute name arg values.
    *args: The resource attribute key expression to format. The printer
      projection symbols and aliases may be used in key expressions. If no args
      are specified then the resource is used as the arg list if it is a list,
      otherwise the resource is used as the only arg.

  Returns:
    The formatted string.

  Example:
    --format='value(format("{0:f.1}/{0:f.1}", q.CPU.default, q.CPU.limit))'
  """
  if args:
    columns = projection.compiler('({0})'.format(','.join(args)),
                                  by_columns=True,
                                  defaults=projection).Evaluate(r)
  elif isinstance(r, list):
    columns = r
  else:
    columns = [r or '']
  return fmt.format(*columns)


def TransformGroup(r, *args):
  """Formats a [...] grouped list.

  Each group is enclosed in [...]. The first item separator is ':', subsequent
  separators are ','.
    [item1] [item1] ...
    [item1: item2] ... [item1: item2]
    [item1: item2, item3] ... [item1: item2, item3]

  Args:
    r: A JSON-serializable object.
    *args: Optional attribute names to select from the list. Otherwise
      the string value of each list item is selected.

  Returns:
    The [...] grouped formatted list, [] if r is empty.
  """
  if not r:
    return '[]'
  buf = StringIO.StringIO()
  sep = None
  for item in r:
    if sep:
      buf.write(sep)
    else:
      sep = ' '
    if not args:
      buf.write('[{0}]'.format(unicode(item)))
    else:
      buf.write('[')
      sub = None
      for attr in args:
        if sub:
          buf.write(sub)
          sub = ', '
        else:
          sub = ': '
        if isinstance(item, dict):
          value = item.get(attr)
        else:
          value = getattr(item, attr, None)
        if value is not None:
          buf.write(unicode(value))
      buf.write(']')
  return buf.getvalue()


def TransformIf(r, expr):
  """Disables the projection key if the flag name filter expr is false.

  Args:
    r: A JSON-serializable object.
    expr: A command flag filter name expression. See `gcloud topic filters` for
      details on filter expressions. The expression variables are flag names
      without the leading *--* prefix and dashes replaced by underscores.

  Example:
    The "table(name, value.if(NOT short_format))" format will list a value
    column if the *--short-format* command line flag is not specified.

  Returns:
    r
  """
  _ = expr
  return r


def TransformIso(r, undefined='T'):
  """Formats the resource to numeric ISO time format.

  Args:
    r: A JSON-serializable object.
    undefined: Returns this value if the resource does not have an isoformat()
      attribute.

  Returns:
    The numeric ISO time format for r or undefined if r is not a time.
  """
  return TransformDate(r, format='%Y-%m-%dT%H:%M:%S.%3f%Oz',
                       undefined=undefined)


def TransformJoin(r, sep='/', undefined=''):
  """Joins the elements of the resource list by the value of sep.

  A string resource is treated as a list of characters.

  Args:
    r: A string or list.
    sep: The separator value to use when joining.
    undefined: Returns this value if the result after joining is empty.

  Returns:
    A new string containing the resource values joined by sep.

  Example:
    "a/b/c/d".split("/").join("!") returns "a!b!c!d"
  """
  try:
    parts = [unicode(i) for i in r]
    return sep.join(parts) or undefined
  except (AttributeError, TypeError):
    return undefined


def TransformLen(r):
  """Returns the length of the resource if it is non-empty, 0 otherwise.

  Args:
    r: A JSON-serializable object.

  Returns:
    The length of r if r is non-empty, 0 otherwise.
  """
  try:
    return len(r)
  except TypeError:
    return 0


def TransformList(r, show='', undefined='', separator=','):
  """Formats a dict or list into a compact comma separated list.

  Args:
    r: A JSON-serializable object.
    show: If show=*keys* then list dict keys; if show=*values* then list dict
      values; otherwise list dict key=value pairs.
    undefined: Return this if the resource is empty.
    separator: The list item separator string.

  Returns:
    The key=value pairs for a dict or list values for a list, separated by
    separator. Returns undefined if r is empty, or r if it is not a dict or
    list.
  """
  if isinstance(r, dict):
    if show == 'keys':
      return separator.join([unicode(k) for k in sorted(r)])
    elif show == 'values':
      return separator.join([unicode(v) for _, v in sorted(r.iteritems())])
    else:
      return separator.join([u'{k}={v}'.format(k=k, v=v)
                             for k, v in sorted(r.iteritems())])
  if isinstance(r, list):
    return separator.join(map(unicode, r))
  return r or undefined


def TransformMap(r):
  """Applies the next transform in the sequence to each resource list item.

  Example:
    list_field.map().foo().bar() applies foo() to each item in list_field and
    then bar() to the resulting value. list_field.map().foo().map().bar()
    applies foo() to each item in list_field and then bar() to each item in the
    resulting list.

  Args:
    r: A resource.

  Returns:
    r.
  """
  # This method is used as a decorator in transform expressions. It is
  # recognized at parse time and discarded.
  return r


def TransformResolution(r, undefined='', transpose=False):
  """Formats a human readable XY resolution.

  Args:
    r: object, A JSON-serializable object containing an x/y resolution.
    undefined: Returns this value if a recognizable resolution was not found.
    transpose: Returns the y/x resolution if true.

  Returns:
    The human readable x/y resolution for r if it contains members that
      specify width/height, col/row, col/line, or x/y resolution. Returns
      undefined if no resolution found.
  """
  names = (
      ('width', 'height'),
      ('screenx', 'screeny'),
      ('col', 'row'),
      ('col', 'line'),
      ('x', 'y'),
      )

  # Collect the lower case candidate member names.
  mem = {}
  for m in r if isinstance(r, dict) else dir(r):
    if not m.startswith('__') and not m.endswith('__'):
      mem[m.lower()] = m

  def _Dimension(d):
    """Gets the resolution dimension for d.

    Args:
      d: The dimension name substring to get.

    Returns:
      The resolution dimension matching d or None.
    """
    for m in mem:
      if d in m:
        return resource_property.Get(r, [mem[d]], None)
    return None

  # Check member name pairwise matches in order from least to most ambiguous.
  for name_x, name_y in names:
    x = _Dimension(name_x)
    if x is None:
      continue
    y = _Dimension(name_y)
    if y is None:
      continue
    if GetBooleanArgValue(transpose):
      return '{y} x {x}'.format(x=x, y=y)
    return '{x} x {y}'.format(x=x, y=y)
  return undefined


def TransformScope(r, *args):
  """Gets the /args/ suffix from a URI.

  Args:
    r: A URI.
    *args: Optional URI segment names. If not specified then 'regions', 'zones'
      is assumed.

  Returns:
    The URI segment after the first /*args/ in r, the last /-separated
      component in r if none found.

  Example:
    "https://abc/foo/projects/bar/xyz".scope("projects") returns "bar/xyz".
    "https://xyz/foo/regions/abc".scope() returns "abc".
  """
  if not r:
    return ''
  r = urllib2.unquote(unicode(r))
  if '/' not in r:
    return r
  # Checking for regions and/or zones is the most common use case.
  for scope in args or ('regions', 'zones'):
    segment = '/' + scope + '/'
    if segment in r:
      return r.split(segment)[-1]
  if r.startswith('https://'):
    return r.split('/')[-1]
  return r


def TransformSegment(r, index=-1, undefined=''):
  """Returns the index-th URI path segment.

  Args:
    r: A URI path.
    index: The path segment index to return counting from 0.
    undefined: Returns this value if the resource or segment index is empty.

  Returns:
    The index-th URI path segment in r
  """
  if not r:
    return undefined
  r = urllib2.unquote(unicode(r))
  segments = r.split('/')
  try:
    return segments[int(index)] or undefined
  except IndexError:
    return undefined


# pylint: disable=redefined-builtin, params match the transform spec
def TransformSize(r, zero='0', precision=1, units_in=None, units_out=None,
                  min=0):
  """Formats a human readable size in bytes.

  Args:
    r: A size in bytes.
    zero: Returns this if size==0. Ignored if None.
    precision: The number of digits displayed after the decimal point.
    units_in: A unit suffix (only the first character is checked) or unit size.
      The size is multiplied by this. The default is 1.0.
    units_out: A unit suffix (only the first character is checked) or unit size.
      The size is divided by this. The default is 1.0.
    min: Sizes < _min_ will be listed as "< _min_".

  Returns:
    A human readable scaled size in bytes.
  """

  def _UnitSuffixAndSize(unit):
    """Returns the unit size for unit, 1.0 for unknown units.

    Args:
      unit: The unit suffix (only the first character is checked), the unit
        size in bytes, or None.

    Returns:
      A (unit_suffix, unit_size) tuple.
    """
    unit_size = {
        'K': 2 ** 10,
        'M': 2 ** 20,
        'G': 2 ** 30,
        'T': 2 ** 40,
        'P': 2 ** 50,
    }

    try:
      return ('', float(unit) or 1.0)
    except (TypeError, ValueError):
      pass
    try:
      unit_suffix = unit[0].upper()
      return (unit_suffix, unit_size[unit_suffix])
    except (IndexError, KeyError, TypeError):
      pass
    return ('', 1.0)

  if not r and zero is not None:
    return zero
  try:
    size = float(r)
  except (TypeError, ValueError):
    size = 0
  min_size = float(min)  # Exception OK here.
  if size < min_size:
    size = min_size
    prefix = '< '
  else:
    prefix = ''
  (_, units_in_size) = _UnitSuffixAndSize(units_in)
  size *= units_in_size
  (units_out_suffix, units_out_size) = _UnitSuffixAndSize(units_out)
  if units_out_suffix:
    size /= units_out_size
    fmt = '{{0:.{precision}f}}'.format(precision=precision)
    return fmt.format(size)
  the_unit = 'PiB'
  for unit in ['bytes', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB']:
    if size < 1024.0:
      the_unit = unit
      break
    size /= 1024.0
  if the_unit:
    the_unit = ' ' + the_unit
  if size == int(size):
    return '{0}{1}{2}'.format(prefix, int(size), the_unit)
  else:
    fmt = '{{0}}{{1:.{precision}f}}{{2}}'.format(precision=precision)
    return fmt.format(prefix, size, the_unit)


def TransformSlice(r, op=':', undefined=''):
  """Returns a list slice specified by op.

  The op parameter consists of up to three colon-delimeted integers: start, end,
  and step. The parameter supports half-open ranges: start and end values can
  be omitted, representing the first and last positions of the resource
  respectively.

  The step value represents the increment between items in the resource included
  in the slice. A step of 2 results in a slice that contains every other item in
  the resource.

  Negative values for start and end indicate that the positons should start from
  the last position of the resource. A negative value for step indicates that
  the slice should contain items in reverse order.

  If op contains no colons, the slice consists of the single item at the
  specified position in the resource.

  Args:
    r: A JSON-serializable string or array.
    op: The slice operation.
    undefined: Returns this value if the slice cannot be created, or the
        resulting slice is empty.

  Returns:
    A new array containing the specified slice of the resource.

  Example:
    [1,2,3].slice(1:) returns [2,3].
    [1,2,3].slice(:2) returns [1,2].
    [1,2,3].slice(-1:) returns [3].
    [1,2,3].slice(::-1) returns [3,2,1].
    [1,2,3].slice(1) returns [2].
  """
  op = op.strip()
  if not op:
    return undefined

  # Construct a list of integer and None values from op to be passed to slice().
  try:
    ops = [int(sp) if sp else None for sp in (p.strip() for p in op.split(':'))]
  except (AttributeError, TypeError, ValueError):
    return undefined

  # Handle the case where the user specifies only an index by
  # constructing a slice of i:i+1. E.g., the equivalent slice of index
  # 1 is [1:2]. If ops[0] + 1 == 0, use None as the slice end instead.
  # The slice [-1:0] returns an empty set; [-1:] returns a set
  # containing the last element.
  if len(ops) == 1:
    ops.append(ops[0] + 1 or None)

  try:
    return list(r[slice(*ops)]) or undefined
  except (TypeError, ValueError):
    return undefined


def TransformSplit(r, sep='/', undefined=''):
  """Splits a string by the value of sep.

  Args:
    r: A string.
    sep: The separator value to use when splitting.
    undefined: Returns this value if the result after splitting is empty.

  Returns:
    A new array containing the split components of the resource.

  Example:
    "a/b/c/d".split() returns ["a", "b", "c", "d"]
  """
  if not r:
    return undefined

  try:
    return r.split(sep)
  except (AttributeError, TypeError, ValueError):
    return undefined


def TransformUri(r, undefined='.'):
  """Gets the resource URI.

  Args:
    r: A JSON-serializable object.
    undefined: Returns this if a the URI for r cannot be determined.

  Returns:
    The URI for r or undefined if not defined.
  """

  def _GetAttr(attr):
    """Returns the string value for attr or None if the value is not a string.

    Args:
      attr: The attribute object to get the value from.

    Returns:
      The string value for attr or None if the value is not a string.
    """
    try:
      attr = attr()
    except TypeError:
      pass
    return attr if isinstance(attr, (basestring, buffer)) else None

  if isinstance(r, (basestring, buffer)):
    if r.startswith('https://'):
      return r
  elif r:
    for name in ('selfLink', 'SelfLink'):
      uri = _GetAttr(resource_property.Get(r, [name], None))
      if uri:
        return uri
  return undefined


def TransformYesNo(r, yes=None, no='No'):
  """Returns no if the resource is empty, yes or the resource itself otherwise.

  Args:
    r: A JSON-serializable object.
    yes: If the resource is not empty then returns _yes_ or the resource itself
      if _yes_ is not defined.
    no: Returns this value if the resource is empty.

  Returns:
    yes or r if r is not empty, no otherwise.
  """
  return (r if yes is None else yes) if r else no


# The builtin transforms.
_BUILTIN_TRANSFORMS = {
    'always': TransformAlways,
    'basename': TransformBaseName,
    'collection': TransformCollection,
    'color': TransformColor,
    'date': TransformDate,
    'decode': TransformDecode,
    'duration': TransformDuration,
    'encode': TransformEncode,
    'enum': TransformEnum,
    'error': TransformError,
    'extract': TransformExtract,
    'fatal': TransformFatal,
    'firstof': TransformFirstOf,
    'float': TransformFloat,
    'format': TransformFormat,
    'group': TransformGroup,
    'if': TransformIf,
    'iso': TransformIso,
    'join': TransformJoin,
    'len': TransformLen,
    'list': TransformList,
    'map': TransformMap,
    'resolution': TransformResolution,
    'scope': TransformScope,
    'segment': TransformSegment,
    'size': TransformSize,
    'slice': TransformSlice,
    'split': TransformSplit,
    'uri': TransformUri,
    'yesno': TransformYesNo,
}

# This dict maps API names (the leftmost dotted name in a collection) to
# (module_path, method_name) tuples where:
#   module_path: A dotted module path that contains a transform dict.
#   method_name: A method name in the module that returns the transform dict.
_API_TO_TRANSFORMS = {
    'compute': ('googlecloudsdk.api_lib.compute.transforms', 'GetTransforms'),
    'debug': ('googlecloudsdk.api_lib.debug.transforms', 'GetTransforms'),
    'runtimeconfig': (
        'googlecloudsdk.api_lib.deployment_manager.runtime_configs.transforms',
        'GetTransforms'
    ),
    'service_registry': ('googlecloudsdk.api_lib.service_registry.transforms',
                         'GetTransforms'),
}


def GetTransforms(collection=None):
  """Returns the builtin or collection specific transform symbols dict.

  Args:
    collection: A collection, None or 'builtin' for the builtin transforms.

  Raises:
    ImportError: module_path __import__ error.
    AttributeError: module does not contain method_name.

  Returns:
    The transform symbols dict, None if there is none.
  """
  if collection in (None, 'builtin'):
    return _BUILTIN_TRANSFORMS
  api = collection.split('.')[0]
  module_path, method_name = _API_TO_TRANSFORMS.get(api, (None, None))
  if not module_path:
    return None
  # Exceptions after this point indicate configuration/installation errors.
  module = __import__(module_path, fromlist=[method_name])
  method = getattr(module, method_name)
  return method()


def GetTypeDataName(name, type_name='object'):
  """Returns the data name for name of type type_name.

  Args:
    name: The data name.
    type_name: The data type name.

  Returns:
    The data name for name of type type_name.
  """
  return '{name}::{type_name}'.format(name=name, type_name=type_name)
