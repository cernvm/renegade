# Copyright 2013 Google Inc. All Rights Reserved.

"""Lists all backups associated with a given instance.

Lists all backups associated with a given instance and configuration
in the reverse chronological order of the enqueued time.
"""
from apiclient import errors

from google.cloud.sdk.calliope import base
from google.cloud.sdk.calliope import exceptions
from google.cloud.sdk.sql import util


class List(base.Command):
  """Lists all backups associated with a given instance.

  Lists all backups associated with a given Cloud SQL instance and
  configuration in the reverse chronological order of the enqueued time.
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
        '--max-results',
        '-m',
        required=False,
        default=20,
        help='Maximum number of backups per response.')
    parser.add_argument(
        '--page-token',
        '-p',
        required=False,
        help='A previously-returned page token representing part of the larger'
        ' set of results to view.')

  def Run(self, args):
    """Lists all backups associated with a given instance.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      A dict object that has the list of backup run resources if the command ran
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
    max_results = args.max_results
    page_token = args.page_token
    instance = self.command.ParentGroup().ParentGroup().instances.get(
        instance=instance_id)
    # At this point we support only one backup-config. So, we just use that id.
    backup_config = instance['settings']['backupConfiguration'][0]['id']
    request = sql.backupRuns().list(
        project=project_id, instance=instance_id,
        backupConfiguration=backup_config, maxResults=max_results,
        pageToken=page_token)
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
      result: A dict object representing the the list of backup runs
          resources.
    """
    PrettyPrintBackupRunsList(result)


def PrettyPrintBackupRunsList(backups_list):
  """Pretty prints a list of backups.

  Args:
    backups_list: A dict object representing the the list of backups
        resources.
  """
  printer = util.PrettyPrinter(0)
  if 'nextPageToken' in backups_list:
    page_token = backups_list['nextPageToken']
    printer.Print('Next page-token : %s (use --page-token=%s to fetch the '
                  'next page)' % (page_token, page_token))
  if backups_list.has_key('items'):
    for backup in backups_list['items']:
      printer.Print('')
      printer.PrintBackupRun(backup)
  else:
    printer.Print('No backup found for instance.')
