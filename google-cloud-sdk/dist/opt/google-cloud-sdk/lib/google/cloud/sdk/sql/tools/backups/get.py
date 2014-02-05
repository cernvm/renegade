# Copyright 2013 Google Inc. All Rights Reserved.

"""Retrieves information about a backup."""
from apiclient import errors

from google.cloud.sdk.calliope import base
from google.cloud.sdk.calliope import exceptions
from google.cloud.sdk.sql import util


class Get(base.Command):
  """Retrieves information about a backup.

  Retrieves information about a backup.
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
        'due_time',
        help='The time when this run is due to start in RFC 3339 format, for '
        'example 2012-11-15T16:19:00.094Z.')

  def Run(self, args):
    """Retrieves information about a backup.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      A dict object that has the backup run resource if the command ran
      successfully.
    Raises:
      HttpException: A http error response was received while executing api
          request.
      ToolException: An error other than http error occured while executing the
          command.
    """
    sql = self.context['sql']
    instance_id = util.GetInstanceIdWithoutProject(args.instance)
    project_id = util.GetProjectId(args.instance)
    due_time = args.due_time
    instance = self.command.ParentGroup().ParentGroup().instances.get(
        instance=instance_id)
    # At this point we support only one backup-config. So, we just use that id.
    backup_config = instance['settings']['backupConfiguration'][0]['id']
    request = sql.backupRuns().get(
        project=project_id, instance=instance_id,
        backupConfiguration=backup_config, dueTime=due_time)
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
      result: A dict object that has the backupRun resource.
    """
    printer = util.PrettyPrinter(0)
    printer.PrintBackupRun(result)
