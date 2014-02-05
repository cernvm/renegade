# Copyright 2013 Google Inc. All Rights Reserved.

"""The super-group for the cloud CLI."""

import argparse
import os

from google.cloud.sdk.calliope import base
from google.cloud.sdk.core import properties


class Gcloud(base.Group):
  """Google Cloud Platform CLI/API."""

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--project',
        help='Google Cloud Platform project to use for this invocation.')
    parser.add_argument(
        '--api-host',
        help=argparse.SUPPRESS)
    # Must have a None default so properties are not always overridden when the
    # arg is not provided.
    parser.add_argument(
        '--quiet',
        '-q',
        action='store_true',
        default=None,
        help='Disable all interactive prompts when running gcloud commands.  '
        'If input is required, defaults will be used, or an error will be '
        'raised.')
