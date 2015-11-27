# Copyright 2013 Google Inc. All Rights Reserved.
"""Deletes all certificates and generates a new server SSL certificate."""

from googlecloudsdk.api_lib.sql import errors
from googlecloudsdk.api_lib.sql import operations
from googlecloudsdk.api_lib.sql import validate
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log


class _BaseResetSslConfig(object):
  """Deletes all client certificates and generates a new server certificate."""

  @classmethod
  def Args(cls, parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument(
        'instance',
        completion_resource='sql.instances',
        help='Cloud SQL instance ID.')
    parser.add_argument(
        '--async',
        action='store_true',
        help='Do not wait for the operation to complete.')

  def Display(self, unused_args, result):
    """Display prints information about what just happened to stdout.

    Args:
      unused_args: The same as the args in Run.
      result: A dict object representing the operations resource describing the
          resetSslConfig operation if the reset-ssl-config was successful.
    """
    self.format(result)


@base.ReleaseTracks(base.ReleaseTrack.GA)
class ResetSslConfig(_BaseResetSslConfig, base.Command):
  """Deletes all client certificates and generates a new server certificate."""

  @errors.ReraiseHttpException
  def Run(self, args):
    """Deletes all certificates and generates a new server SSL certificate.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      A dict object representing the operations resource describing the
      resetSslConfig operation if the reset was successful.
    Raises:
      HttpException: A http error response was received while executing api
          request.
      ToolException: An error other than http error occured while executing the
          command.
    """
    sql_client = self.context['sql_client']
    sql_messages = self.context['sql_messages']
    resources = self.context['registry']

    validate.ValidateInstanceName(args.instance)
    instance_ref = resources.Parse(args.instance, collection='sql.instances')

    result = sql_client.instances.ResetSslConfig(
        sql_messages.SqlInstancesResetSslConfigRequest(
            project=instance_ref.project,
            instance=instance_ref.instance))

    operation_ref = resources.Create(
        'sql.operations',
        operation=result.operation,
        project=instance_ref.project,
        instance=instance_ref.instance,
    )

    if args.async:
      return sql_client.operations.Get(operation_ref.Request())

    operations.OperationsV1Beta3.WaitForOperation(
        sql_client, operation_ref, 'Resetting SSL config')

    log.status.write('Reset SSL config for [{resource}].\n'.format(
        resource=instance_ref))


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class ResetSslConfigBeta(_BaseResetSslConfig, base.Command):
  """Deletes all client certificates and generates a new server certificate."""

  @errors.ReraiseHttpException
  def Run(self, args):
    """Deletes all certificates and generates a new server SSL certificate.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      A dict object representing the operations resource describing the
      resetSslConfig operation if the reset was successful.
    Raises:
      HttpException: A http error response was received while executing api
          request.
      ToolException: An error other than http error occured while executing the
          command.
    """
    sql_client = self.context['sql_client']
    sql_messages = self.context['sql_messages']
    resources = self.context['registry']

    validate.ValidateInstanceName(args.instance)
    instance_ref = resources.Parse(args.instance, collection='sql.instances')

    result_operation = sql_client.instances.ResetSslConfig(
        sql_messages.SqlInstancesResetSslConfigRequest(
            project=instance_ref.project,
            instance=instance_ref.instance))

    operation_ref = resources.Create(
        'sql.operations',
        operation=result_operation.name,
        project=instance_ref.project,
        instance=instance_ref.instance,
    )

    if args.async:
      return sql_client.operations.Get(operation_ref.Request())

    operations.OperationsV1Beta4.WaitForOperation(
        sql_client, operation_ref, 'Resetting SSL config')

    log.status.write('Reset SSL config for [{resource}].\n'.format(
        resource=instance_ref))
