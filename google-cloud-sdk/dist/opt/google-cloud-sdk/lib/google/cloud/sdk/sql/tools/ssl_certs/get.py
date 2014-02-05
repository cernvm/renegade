# Copyright 2013 Google Inc. All Rights Reserved.

"""Retrieves information about an SSL cert for a Cloud SQL instance."""
from apiclient import errors

from google.cloud.sdk.calliope import base
from google.cloud.sdk.calliope import exceptions
from google.cloud.sdk.sql import util


class Get(base.Command):
  """Retrieves information about an SSL cert for a Cloud SQL instance."""

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
    """Retrieves information about an SSL cert for a Cloud SQL instance.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      A dict object representing the sslCerts resource if the api request was
      successful.
    Raises:
      HttpException: A http error response was received while executing api
          request.
      ToolException: An error other than http error occured while executing the
          command.
    """
    common_name = args.common_name
    try:
      ssl_certs = (self.command.ParentGroup().list())
      for cert in ssl_certs['items']:
        if cert.get('commonName') == common_name:
          return cert
      raise exceptions.ToolException('Cert with the provided common name '
                                     'doesn\'t exist.')
    except errors.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))
    except errors.Error as error:
      raise exceptions.ToolException(error)

  def Display(self, unused_args, result):
    """Display prints information about what just happened to stdout.

    Args:
      unused_args: The same as the args in Run.
      result: A dict object representing the sslCert resource if the api
      request was successful.
    """
    printer = util.PrettyPrinter(0)
    printer.PrintSslCert(result)
