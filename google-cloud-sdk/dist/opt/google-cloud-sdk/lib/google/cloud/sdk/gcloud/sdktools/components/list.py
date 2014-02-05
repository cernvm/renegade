# Copyright 2013 Google Inc. All Rights Reserved.

"""The command to list installed/available gcloud components."""

from google.cloud.sdk.calliope import base
from google.cloud.sdk.calliope import exceptions
from google.cloud.sdk.core import config
from google.cloud.sdk.core.updater import update_manager


class List(base.Command):
  """Command to list the current state of installed components.

  List all available components and indicate whether or not they're installed or
  have updates available.
  """

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--show-versions', required=False, action='store_true',
        help='Show version information for all components.')

  def Run(self, args):
    """Runs the list command."""

    manager = self.context[config.CLOUDSDK_UPDATE_MANAGER_KEY]
    try:
      manager.List(show_versions=args.show_versions)
    except update_manager.Error:
      raise exceptions.ToolException.FromCurrent()
