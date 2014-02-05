# Copyright 2013 Google Inc. All Rights Reserved.

"""Sets the password of the MySQL root user."""
from apiclient import errors

from google.cloud.sdk.calliope import base
from google.cloud.sdk.calliope import exceptions
from google.cloud.sdk.sql import util


class SetRootPassword(base.Command):
  """Sets the password of the MySQL root user."""

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
        '--password',
        '-p',
        help='The password for the root user. WARNING: Setting password using '
        'this option can potentially expose the password to other users '
        'of this machine. Instead, you can use --password-file to get the'
        ' password from a file.')
    parser.add_argument(
        '--password-file',
        help='The path to the filename which has the password to be set. The '
        'first line of the file will be interpreted as the password to be set.')

  def Run(self, args):
    """Sets the password of the MySQL root user.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      A dict object representing the operations resource describing the
      setRootPassword operation if the setRootPassword was successful.
    Raises:
      HttpException: A http error response was received while executing api
          request.
      ToolException: An error other than http error occured while executing the
          command.
    """
    sql = self.context['sql']
    instance_id = util.GetInstanceIdWithoutProject(args.instance)
    project_id = util.GetProjectId(args.instance)
    if args.password and args.password_file:
      raise exceptions.ToolException('Argument --password/-p not allowed with'
                                     ' --password-file')
    if not args.password and not args.password_file:
      raise exceptions.ToolException('Must specify either --password/-p or'
                                     ' --password-file')
    password = args.password
    password_file = args.password_file
    try:
      if password_file:
        with open(password_file, 'r') as f:
          password = f.readline()
      body = {'setRootPasswordContext': {'password': password}}
      request = sql.instances().setRootPassword(project=project_id,
                                                instance=instance_id,
                                                body=body)
      result = request.execute()
      operations = self.command.ParentGroup().ParentGroup().operations(
          instance=instance_id)
      operation = operations.get(operation=result['operation'])
      return operation
    except errors.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))
    except errors.Error as error:
      raise exceptions.ToolException(error)
    except IOError as error:
      raise exceptions.ToolException(error)

  # pylint: disable=unused-argument
  def Display(self, args, result):
    """Display prints information about what just happened to stdout.

    Args:
      args: The same as the args in Run.
      result: A dict object representing the operations resource describing the
          set-root-password operation if the set-root-password was successful.
    """
    printer = util.PrettyPrinter(0)
    printer.Print('Result of the set-root-password operation:')
    printer.PrintOperation(result)
