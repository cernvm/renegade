# Copyright 2013 Google Inc. All Rights Reserved.

"""config command group."""

from google.cloud.sdk.calliope import base
from google.cloud.sdk.calliope import exceptions as c_exc
from google.cloud.sdk.core import config
from google.cloud.sdk.core import properties


class Config(base.Group):
  """View and edit Google Cloud SDK properties."""
