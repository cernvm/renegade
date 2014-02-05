# Copyright 2013 Google Inc. All Rights Reserved.

"""Provide commands for managing Cloud SQL instances."""


from google.cloud.sdk.calliope import base


class Instances(base.Group):
  """Provide commands for managing Cloud SQL instances.

  Provide commands for managing Cloud SQL instances including creating,
  configuring, restarting, and deleting instances.
  """
