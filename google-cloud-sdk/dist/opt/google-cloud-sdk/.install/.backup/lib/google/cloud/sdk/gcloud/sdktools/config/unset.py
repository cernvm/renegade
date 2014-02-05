# Copyright 2013 Google Inc. All Rights Reserved.

"""Command to unset properties."""

from google.cloud.sdk.calliope import base
from google.cloud.sdk.calliope import exceptions as c_exc
from google.cloud.sdk.core import properties


class Unset(base.Command):
  """Erase Google Cloud SDK properties.

  Unset a property to be as if it were never defined in the first place. This
  command modifies only the local workspace properties if --global-only is not
  set, and modifies only the global properties is --global-only is set.
  """

  @staticmethod
  def Args(parser):
    """Adds args for this command."""
    parser.add_argument(
        '--global-only',
        action='store_true',
        help='Unset option in the global properties file.')
    parser.add_argument(
        '--section', '-s',
        default=properties.VALUES.default_section.name,
        help='The section containing the option to be unset.')
    parser.add_argument(
        'property',
        help='The property to be unset.')

  @c_exc.RaiseToolExceptionInsteadOf(properties.Error)
  def Run(self, args):
    """Runs this command."""
    prop = properties.VALUES.Section(args.section).Property(args.property)
    properties.PersistProperty(
        prop, None, force_global=args.global_only)
