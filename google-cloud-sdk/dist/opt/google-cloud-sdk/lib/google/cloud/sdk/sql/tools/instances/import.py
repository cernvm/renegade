# Copyright 2013 Google Inc. All Rights Reserved.

"""Imports data into a Cloud SQL instance.

Imports data into a Cloud SQL instance from a MySQL dump file in
Google Cloud Storage.
"""
import json

from apiclient import errors

from google.cloud.sdk.calliope import base
from google.cloud.sdk.calliope import exceptions
from google.cloud.sdk.sql import util


class Import(base.Command):
  """Imports data into a Cloud SQL instance from Google Cloud Storage."""

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
        '--database',
        '-d',
        required=False,
        help='The database (for example, guestbook) to which the import is'
        ' made. If not set, it is assumed that the database is specified in'
        ' the file to be imported.')
    parser.add_argument(
        '--uri',
        '-u',
        required=True,
        nargs='+',
        type=str,
        help='Path to the MySQL dump file in Google Cloud Storage from which'
        ' the import is made. The URI is in the form gs://bucketName/fileName.'
        ' Compressed gzip files (.gz) are also supported.')

  def Run(self, args):
    """Imports data into a Cloud SQL instance from Google Cloud Storage.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      A dict object representing the operations resource describing the import
      operation if the import was successful.
    Raises:
      HttpException: A http error response was received while executing api
          request.
      ToolException: An error other than http error occured while executing the
          command.
    """
    sql = self.context['sql']
    instance_id = util.GetInstanceIdWithoutProject(args.instance)
    project_id = util.GetProjectId(args.instance)
    database = args.database
    uris_list = args.uri
    uris = ''
    for uri in uris_list:
      uris += ('"%s", ' % uri)
    uris = uris.rstrip(', ')
    import_context = '"uri" : [%s]' % uris

    if database:
      import_context += ',"database" : "%s"' % database
    body = json.loads('{ "importContext" : { %s }}' % import_context)
    request = sql.instances().import_(
        project=project_id, instance=instance_id, body=body)
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
      import operation if the import was successful.
    """
    printer = util.PrettyPrinter(0)
    printer.Print('Result of the import operation:')
    printer.PrintOperation(result)
