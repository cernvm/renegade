# Copyright 2013 Google Inc. All Rights Reserved.

"""Creates an SSL certificate for a Cloud SQL instance."""
from apiclient import errors

from google.cloud.sdk.calliope import base
from google.cloud.sdk.calliope import exceptions
from google.cloud.sdk.core import log
from google.cloud.sdk.core.util import console_io
from google.cloud.sdk.core.util import files
from google.cloud.sdk.sql import util


class AddCert(base.Command):
  """Creates an SSL certificate for a Cloud SQL instance."""

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
    parser.add_argument(
        '--cert-file',
        default=None,
        help=('Location of file which the private key of the created ssl-cert'
              ' will be written to.'))

  def Run(self, args):
    """Creates an SSL certificate for a Cloud SQL instance.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      A dict object representing the operations resource describing the create
      operation if the create was successful.
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
    body = {'commonName': common_name}
    request = sql.sslCerts().insert(project=project_id,
                                    instance=instance_id,
                                    body=body)
    try:
      result = request.execute()
      return result
    except errors.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))
    except errors.Error as error:
      raise exceptions.ToolException(error)

  def Display(self, args, result):
    """Display prints information about what just happened to stdout.

    Args:
      args: The same as the args in Run.
      result: A dict object representing the response if the api
          request was successful.
    """
    printer = util.PrettyPrinter(0)
    if args.cert_file is not None:
      cert_file = args.cert_file
      private_key = result.get('clientCert').get('certPrivateKey')
      while True:
        try:
          with files.OpenForWritingPrivate(cert_file) as cf:
            cf.write(private_key)
            cf.write('\n')
          printer.Print('Wrote the private key for ssl-cert "{name}" to {file}.'
                        .format(name=args.common_name, file=cert_file))
          return
        except OSError as e:
          log.error(e)
          cert_file = console_io.PromptResponse(
              'Enter a destination for the cert:')
    else:
      printer.PrintSslCertInsertResponse(result)
      printer.Print('Note: Save the private key. This is the only time you '
                    'will be able to see the private key. If you lose this '
                    'private key, you will have to create a new certificate.')
