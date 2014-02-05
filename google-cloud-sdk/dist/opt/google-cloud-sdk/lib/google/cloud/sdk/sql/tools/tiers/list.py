# Copyright 2013 Google Inc. All Rights Reserved.

"""Lists all available service tiers for Google Cloud SQL."""
from apiclient import errors

from google.cloud.sdk.calliope import base
from google.cloud.sdk.calliope import exceptions
from google.cloud.sdk.core import properties
from google.cloud.sdk.sql import util


class List(base.Command):
  """Lists all available service tiers for Google Cloud SQL."""

  def Run(self, unused_args):
    """Lists all available service tiers for Google Cloud SQL.

    Args:
      unused_args: argparse.Namespace, The arguments that this command was
          invoked with.

    Returns:
      A dict object that has the list of tier resources if the command ran
      successfully.
    Raises:
      HttpException: A http error response was received while executing api
          request.
      ToolException: An error other than http error occured while executing the
          command.
    """
    sql = self.context['sql']
    project_id = properties.VALUES.core.project.Get()
    request = sql.tiers().list(project=project_id)
    try:
      result = request.execute()
      return result
    except errors.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))
    except errors.Error as error:
      raise exceptions.ToolException(error)

  def Display(self, unused_args, result):
    """Display prints information about what just happened to stdout.

    Args:
      unused_args: The same as the args in Run.
      result: the value returned by Run().
    """
    PrettyPrintTiersList(result)


def PrettyPrintTiersList(tiers_list):
  """Pretty prints a list of tiers.

  Args:
    tiers_list: A dict object representing the the list of tier resources.
  """
  printer = util.PrettyPrinter(0)
  for tier in tiers_list['items']:
    printer.Print('%s' % tier['tier'])
    printer.indent += util.EXTRA_INDENT
    PrettyPrintTier(tier, printer)
    printer.indent -= util.EXTRA_INDENT
    printer.Print('')


def PrettyPrintTier(tier, printer):
  """Pretty prints a tier resource.

  Args:
    tier: A dict object representing the tier resource.
    printer: A pretty printer object.
  """
  for key, value in sorted(tier.items()):
    if key == 'region':
      printer.PrintList('region', value)
    elif key != 'kind':
      printer.Print('%s: %s' % (key, value))
