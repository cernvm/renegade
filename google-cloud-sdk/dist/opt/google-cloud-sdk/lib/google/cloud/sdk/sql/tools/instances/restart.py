# Copyright 2013 Google Inc. All Rights Reserved.

"""Restarts a Cloud SQL instance."""
from apiclient import errors

from google.cloud.sdk.calliope import base
from google.cloud.sdk.calliope import exceptions
from google.cloud.sdk.sql import util


class Restart(base.Command):
  """Restarts a Cloud SQL instance."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use it to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument(
        'instance',
        help='Cloud SQL instance ID.')

  def Run(self, args):
    """Restarts a Cloud SQL instance.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      A dict object representing the operations resource describing the restart
      operation if the restart was successful.
    Raises:
      HttpException: A http error response was received while executing api
          request.
      ToolException: An error other than http error occured while executing the
          command.
    """
    sql = self.context['sql']
    instance_id = util.GetInstanceIdWithoutProject(args.instance)
    project_id = util.GetProjectId(args.instance)
    request = sql.instances().restart(project=project_id,
                                      instance=instance_id)
    try:
      result = request.execute()
      operations = self.command.ParentGroup().ParentGroup().operations(
          instance=instance_id)
      operation = operations.get(operation=result['operation'])
      return operation
    except errors.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))
    except errors.Error as error:
      raise exceptions.ToolException(error)

  # pylint: disable=unused-argument
  def Display(self, args, result):
    """Display prints information about what just happened to stdout.

    Args:
      args: The same as the args in Run.
      result: A dict object representing the operations resource describing the
          restart operation if the restart was successful.
    """
    printer = util.PrettyPrinter(0)
    printer.Print('Result of the restart operation:')
    printer.PrintOperation(result)
