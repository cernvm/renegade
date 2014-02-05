# Copyright 2013 Google Inc. All Rights Reserved.

"""Provide commands for managing SSL certificates of Cloud SQL instances."""


from google.cloud.sdk.calliope import base


class SslCerts(base.Group):
  """Provide commands for managing SSL certificates of Cloud SQL instances.

  Provide commands for managing SSL certificates of Cloud SQL instances,
  including creating, deleting, listing, and getting information about
  certificates.
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
