# Copyright 2013 Google Inc. All Rights Reserved.

"""Deletes an SSL certificate for a Cloud SQL instance."""
from apiclient import errors

from google.cloud.sdk.calliope import base
from google.cloud.sdk.calliope import exceptions
from google.cloud.sdk.sql import util


class Delete(base.Command):
  """Deletes an SSL certificate for a Cloud SQL instance."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use it to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument(
        'common_name',
        help='User supplied name. Constrained to [a-zA-Z.-_ ]+.')

  def Run(self, args):
    """Deletes an SSL certificate for a Cloud SQL instance.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      A dict object representing the operations resource describing the delete
      operation if the api request was successful.
    Raises:
      HttpException: A http error response was received while executing api
          request.
      ToolException: An error other than http error occured while executing the
          command.
    """
    sql = self.context['sql']
    instance_id = util.GetInstanceIdWithoutProject(args.instance)
    project_id = util.GetProjectId(args.instance)
    common_name = args.common_name
    try:
      ssl_certs = self.command.ParentGroup().list()
      for cert in ssl_certs['items']:
        if cert.get('commonName') == common_name:
          sha1_fingerprint = cert.get('sha1Fingerprint')
          request = sql.sslCerts().delete(project=project_id,
                                          instance=instance_id,
                                          sha1Fingerprint=sha1_fingerprint)
          result = request.execute()
          operations = self.command.ParentGroup().ParentGroup().operations(
              instance=instance_id)
          operation = operations.get(operation=result['operation'])
          return operation
      raise exceptions.ToolException('Cert with the provided common name '
                                     'doesn\'t exist.')
    except errors.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))

  # pylint: disable=unused-argument
  def Display(self, args, result):
    """Display prints information about what just happened to stdout.

    Args:
      args: The same as the args in Run.
      result: A dict object representing the operations resource describing the
          delete operation if the delete was successful.
    """
    printer = util.PrettyPrinter(0)
    printer.Print('Result of the delete operation:')
    printer.PrintOperation(result)

