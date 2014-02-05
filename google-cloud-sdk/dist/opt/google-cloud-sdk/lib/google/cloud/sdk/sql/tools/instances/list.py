# Copyright 2013 Google Inc. All Rights Reserved.

"""Lists instances in a given project.

Lists instances in a given project in the alphabetical order of the
 instance name.
"""
from apiclient import errors

from google.cloud.sdk.calliope import base
from google.cloud.sdk.calliope import exceptions
from google.cloud.sdk.core import properties
from google.cloud.sdk.sql import util


class List(base.Command):
  """Lists Cloud SQL instances in a given project.

  Lists Cloud SQL instances in a given project in the alphabetical
  order of the instance name.
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
        default=30,
        help='Maximum number of instances per response.')
    parser.add_argument(
        '--page-token',
        '-p',
        required=False,
        help='A previously-returned page token representing part of the larger'
        ' set of results to view.')

  def Run(self, args):
    """Lists Cloud SQL instances in a given project.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      A dict object of the list of instance resources if the command ran
      successfully.
    Raises:
      HttpException: An http error response was received while executing api
          request.
      ToolException: An error other than an http error occured while executing
          the command.
    """
    sql = self.context['sql']
    project_id = properties.VALUES.core.project.Get()
    max_results = args.max_results
    page_token = args.page_token
    request = sql.instances().list(project=project_id,
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
      result: A dict object that has the list of instance resources if the
      command ran successfully.
    """
    PrettyPrintInstancesList(result)


def PrettyPrintInstancesList(instances_list):
  """Pretty prints a list of instances.

  Args:
    instances_list: A dict object representing the the list of instance
        resources.
  """
  printer = util.PrettyPrinter(0)
  if 'nextPageToken' in instances_list:
    page_token = instances_list['nextPageToken']
    printer.Print('Next page-token : %s (use --page-token=%s to fetch the '
                  'next page)' % (page_token, page_token))
  if instances_list.has_key('items'):
    for instance in instances_list['items']:
      printer.Print('%s' % instance['project'] + ':' + instance['instance'])
  else:
    printer.Print('No instances found for project.')

