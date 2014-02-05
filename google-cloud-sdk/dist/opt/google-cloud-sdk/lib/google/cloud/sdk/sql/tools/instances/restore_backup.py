# Copyright 2013 Google Inc. All Rights Reserved.

"""Restores a backup of a Cloud SQL instance."""
from apiclient import errors

from google.cloud.sdk.calliope import base
from google.cloud.sdk.calliope import exceptions
from google.cloud.sdk.sql import util


class RestoreBackup(base.Command):
  """Restores a backup of a Cloud SQL instance."""

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
    parser.add_argument(
        '--due-time',
        '-d',
        required=True,
        help='The time when this run was due to start in RFC 3339 format, for '
        'example 2012-11-15T16:19:00.094Z.')

  def Run(self, args):
    """Restores a backup of a Cloud SQL instance.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      A dict object representing the operations resource describing the
      restoreBackup operation if the restoreBackup was successful.
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
    request = sql.instances().restoreBackup(
        project=project_id, instance=instance_id,
        backupConfiguration=backup_config, dueTime=due_time)
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

  def Display(self, unused_args, result):
    """Display prints information about what just happened to stdout.

    Args:
      unused_args: The same as the args in Run.
      result: A dict object representing the operations resource describing the
      restoreBackup operation if the restoreBackup was successful.
    """
    printer = util.PrettyPrinter(0)
    printer.Print('Result of the restore-backup operation:')
    printer.PrintOperation(result)
