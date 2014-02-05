# Copyright 2013 Google Inc. All Rights Reserved.

"""List all instance operations.

Lists all instance operations that have been performed on the given
Cloud SQL instance.
"""
from apiclient import errors

from google.cloud.sdk.calliope import base
from google.cloud.sdk.calliope import exceptions
from google.cloud.sdk.sql import util


class List(base.Command):
  """Lists all instance operations for the given Cloud SQL instance."""

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
        default=100,
        help='Maximum number of operations per response.')
    parser.add_argument(
        '--page-token',
        '-p',
        required=False,
        help='A previously-returned page token representing part of the larger'
        ' set of results to view.')

  def Run(self, args):
    """Lists all instance operations that have been performed on an instance.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      A dict object that has the list of operation resources if the command ran
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
    request = sql.operations().list(
        project=project_id,
        instance=instance_id,
        maxResults=max_results,
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
      result: A dict object that has the list of operation resources if the
      command ran successfully.
    """
    PrettyPrintOperationsList(result)


def PrettyPrintOperationsList(operations_list):
  """Pretty prints a list of operations.

  Args:
    operations_list: A dict object representing the the list of operations
        resources.
  """
  printer = util.PrettyPrinter(0)
  if 'nextPageToken' in operations_list:
    page_token = operations_list['nextPageToken']
    printer.Print('Next page-token : %s (use --page-token=%s to fetch the '
                  'next page)' % (page_token, page_token))
  if operations_list.has_key('items'):
    for operation in operations_list['items']:
      printer.Print('%s %s' % (operation['operationType'],
                               operation['operation']))
      printer.indent += util.EXTRA_INDENT
      printer.PrintOperation(operation)
      printer.indent -= util.EXTRA_INDENT
      printer.Print('')
  else:
    printer.Print('No operations found for instance.')
