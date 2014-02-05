# Copyright 2013 Google Inc. All Rights Reserved.

"""Command to list properties."""

from google.cloud.sdk.calliope import base
from google.cloud.sdk.calliope import exceptions as c_exc
from google.cloud.sdk.core import log
from google.cloud.sdk.core import properties


class List(base.Command):
  """View Google Cloud SDK properties.

  List all currently available Cloud SDK properties associated with your current
  workspace or global configuration.
  """

  @staticmethod
  def Args(parser):
    """Adds args for this command."""
    parser.add_argument(
        '--section', '-s',
        help='The section whose properties shall be listed.')
    parser.add_argument(
        '--all', action='store_true',
        help='List all set and unset properties that match the arguments.')
    parser.add_argument(
        'property',
        nargs='?',
        help='The property to be listed.')

  @c_exc.RaiseToolExceptionInsteadOf(properties.Error)
  def Run(self, args):
    """List available properties."""
    section = args.section or properties.VALUES.default_section.name

    if args.property:
      return {section: {
          args.property:
              properties.VALUES.Section(section).Property(args.property).Get()}}
    if args.section:
      return {section: properties.VALUES.Section(args.section).AllValues(
          list_unset=args.all)}
    return properties.VALUES.AllValues(list_unset=args.all)

  def Display(self, args, result):
    writer = log.ConsoleWriter()

    for section, props in sorted(result.iteritems()):
      writer.write('[{section}]\n'.format(section=section))
      for prop, value in sorted(props.iteritems()):
        if value is None:
          writer.write('{prop} (unset)\n'.format(prop=prop))
        else:
          writer.write('{prop} = {value}\n'.format(prop=prop, value=value))
