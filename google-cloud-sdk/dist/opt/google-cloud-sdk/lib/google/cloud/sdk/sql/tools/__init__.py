# Copyright 2013 Google Inc. All Rights Reserved.

"""The super-group for the sql CLI.

The fact that this is a directory with
an __init__.py in it makes it a command group. The methods written below will
all be called by calliope (though they are all optional).
"""

import apiclient.discovery as discovery

from google.cloud.sdk.calliope import base
from google.cloud.sdk.calliope import exceptions
from google.cloud.sdk.core import cli
from google.cloud.sdk.core import config
from google.cloud.sdk.core import properties
from google.cloud.sdk.core.credentials import store as c_store
from google.cloud.sdk.sql import util as util


class SQL(base.Group):
  """Manage Cloud SQL databases."""

  @exceptions.RaiseToolExceptionInsteadOf(c_store.Error)
  def Filter(self, context, unused_args):
    """Context() is a filter function that can update the context.

    Args:
      context: The current context.
      unused_args: The argparse namespace that was specified on the CLI or API.

    Returns:
      The updated context.
    Raises:
      ToolException: When no project is specified.
    """
    http = cli.Http()
    discovery_url = (properties.VALUES.core.api_host.Get()+
                     '/discovery/v1/apis/sqladmin/v1beta3/rest')
    sql = discovery.build(
        'sqladmin',
        'v1beta3',
        http=http,
        discoveryServiceUrl=discovery_url)
    context['sql'] = sql

    if not properties.VALUES.core.project.Get():
      raise exceptions.ToolException(
          ('No project specified. You can add one using "gcloud config set'
           ' project PROJECT".'))

    return context
