# Copyright 2013 Google Inc. All Rights Reserved.

"""Provide commands for working with Cloud SQL instance operations."""

from google.cloud.sdk.calliope import base


class Operations(base.Group):
  """Provide commands for working with Cloud SQL instance operations.

  Provide commands for working with Cloud SQL instance operations, including
  listing and getting information about instance operations of a Cloud SQL
  instance.
  """

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use it to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument(
        '--instance',
        '-i',
        required=True,
        help='Cloud SQL instance ID.')
