# Copyright 2013 Google Inc. All Rights Reserved.

"""The command to remove gcloud components."""

import argparse

from google.cloud.sdk.calliope import base
from google.cloud.sdk.calliope import exceptions
from google.cloud.sdk.core import config
from google.cloud.sdk.core.updater import update_manager


class Remove(base.Command):
  """Command to remove installed components.

  Completely uninstall components and components that depend on them.
  """

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'component_ids',
        metavar='COMPONENT-IDS',
        nargs='+',
        help='The component ids to remove.')
    parser.add_argument(
        '--allow-no-backup',
        required=False,
        action='store_true',
        help=argparse.SUPPRESS)

  def Run(self, args):
    """Runs the list command."""

    manager = self.context[config.CLOUDSDK_UPDATE_MANAGER_KEY]
    try:
      manager.Remove(args.component_ids, allow_no_backup=args.allow_no_backup)
    except update_manager.Error:
      raise exceptions.ToolException.FromCurrent()
