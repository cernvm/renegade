# Copyright 2013 Google Inc. All Rights Reserved.

"""Exports data from a Cloud SQL instance.

Exports data from a Cloud SQL instance to a Google Cloud Storage bucket as
a MySQL dump file.
"""
import json

from apiclient import errors

from google.cloud.sdk.calliope import base
from google.cloud.sdk.calliope import exceptions
from google.cloud.sdk.sql import util


class Export(base.Command):
  """Exports data from a Cloud SQL instance.

  Exports data from a Cloud SQL instance to a Google Cloud Storage
  bucket as a MySQL dump file.
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
        'instance',
        help='Cloud SQL instance ID.')
    parser.add_argument(
        '--uri',
        '-u',
        required=True,
        help='The path to the file in Google Cloud Storage where the export '
        'will be stored. The URI is in the form gs://bucketName/fileName. '
        'If the file already exists, the operation fails. If the filename '
        'ends with .gz, the contents are compressed.')
    parser.add_argument(
        '--database',
        '-d',
        required=False,
        nargs='+',
        type=str,
        help='Database (for example, guestbook) from which the export is made.'
        ' If unspecified, all databases are exported.')
    parser.add_argument(
        '--table',
        '-t',
        required=False,
        nargs='+',
        type=str,
        help='Tables to export from the specified database. If you specify '
        'tables, specify one and only one database.')

  def Run(self, args):
    """Exports data from a Cloud SQL instance.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      A dict object representing the operations resource describing the export
      operation if the export was successful.
    Raises:
      HttpException: A http error response was received while executing api
          request.
      ToolException: An error other than http error occured while executing the
          command.
    """
    sql = self.context['sql']
    instance_id = util.GetInstanceIdWithoutProject(args.instance)
    project_id = util.GetProjectId(args.instance)
    database_list = args.database
    table_list = args.table
    uri = args.uri
    export_context = '"uri" : "%s"' % uri
    if database_list:
      databases = ', '.join('"{0}"'.format(db) for db in database_list)
      export_context += ',"database" : [%s]' % databases

    if table_list:
      tables = ', '.join('"{0}"'.format(tbl) for tbl in table_list)
      export_context += ',"table" : [%s]' % tables

    body = json.loads('{ "exportContext" : { %s }}' % export_context)
    request = sql.instances().export(project=project_id,
                                     instance=instance_id,
                                     body=body)
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
          export operation if the export was successful.
    """
    printer = util.PrettyPrinter(0)
    printer.Print('Result of the export operation:')
    printer.PrintOperation(result)
