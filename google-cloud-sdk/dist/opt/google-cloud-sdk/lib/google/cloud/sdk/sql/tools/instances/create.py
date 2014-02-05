# Copyright 2013 Google Inc. All Rights Reserved.

"""Creates a new Cloud SQL instance."""
from apiclient import errors

from google.cloud.sdk.calliope import base
from google.cloud.sdk.calliope import exceptions
from google.cloud.sdk.sql import util


class Create(base.Command):
  """Creates a new Cloud SQL instance."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Please add arguments in alphabetical order except for no- or a clear-
    pair for that argument which can follow the argument itself.
    Args:
      parser: An argparse parser that you can use it to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument(
        '--activation-policy',
        required=False,
        choices=['ALWAYS', 'NEVER', 'ON_DEMAND'],
        default='ON_DEMAND',
        help='The activation policy for this instance. This specifies when the '
        'instance should be activated and is applicable only when the '
        'instance state is RUNNABLE.')
    parser.add_argument(
        '--assign-ip',
        required=False,
        action='store_true',
        help='Specified if the instance must be assigned an IP address.')
    parser.add_argument(
        '--authorized-gae-apps',
        required=False,
        nargs='+',
        type=str,
        default=[],
        help='List of AppEngine app ids that can access this instance.')
    parser.add_argument(
        '--authorized-networks',
        required=False,
        nargs='+',
        type=str,
        default=[],
        help='The list of external networks that are allowed to connect to the'
        ' instance. Specified in CIDR notation, also known as \'slash\' '
        'notation (e.g. 192.168.100.0/24).')
    parser.add_argument(
        '--backup-start-time',
        required=False,
        help='Start time for the daily backup configuration in UTC timezone,'
        'in the 24 hour format - HH:MM.')
    parser.add_argument(
        '--no-backup',
        required=False,
        action='store_true',
        help='Specified if daily backup must be disabled.')
    parser.add_argument(
        '--enable-bin-log',
        required=False,
        action='store_true',
        help='Specified if binary log must be enabled. If backup configuration'
        ' is disabled, binary log must be disabled as well.')
    parser.add_argument(
        '--follow-gae-app',
        required=False,
        help='The AppEngine app this instance should follow. It must be in '
        'the same region as the instance.')
    parser.add_argument(
        '--gce-zone',
        required=False,
        help='The preferred Compute Engine zone (e.g. us-central1-a, '
        'us-central1-b, etc.).')
    parser.add_argument(
        'instance',
        help='Cloud SQL instance ID.')
    parser.add_argument(
        '--pricing-plan',
        '-p',
        required=False,
        choices=['PER_USE', 'PACKAGE'],
        default='PER_USE',
        help='The pricing plan for this instance.')
    parser.add_argument(
        '--region',
        required=False,
        choices=['us-east1', 'europe-west1'],
        default='us-east1',
        help='The geographical region. Can be us-east1 or europe-west1.')
    parser.add_argument(
        '--replication',
        required=False,
        choices=['SYNCHRONOUS', 'ASYNCHRONOUS'],
        default='SYNCHRONOUS',
        help='The type of replication this instance uses.')
    parser.add_argument(
        '--tier',
        '-t',
        required=False,
        default='D1',
        help='The tier of service for this instance, for example D0, D1.')

  def Run(self, args):
    """Creates a new Cloud SQL instance.

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
    replication = args.replication
    tier = args.tier
    activation_policy = args.activation_policy
    region = args.region
    pricing_plan = args.pricing_plan
    authorized_gae_apps = args.authorized_gae_apps
    follow_gae_app = args.follow_gae_app
    gce_zone = args.gce_zone
    assign_ip = args.assign_ip
    authorized_networks = args.authorized_networks
    enable_bin_log = args.enable_bin_log

    backup_start_time = args.backup_start_time
    no_backup = args.no_backup
    settings = {}
    settings['tier'] = tier
    settings['pricingPlan'] = pricing_plan
    settings['replicationType'] = replication
    settings['activationPolicy'] = activation_policy
    settings['authorizedGaeApplications'] = authorized_gae_apps
    location_preference = {}
    if follow_gae_app:
      location_preference['followGaeApplication'] = follow_gae_app
    if gce_zone:
      location_preference['zone'] = gce_zone
    settings['locationPreference'] = location_preference
    ip_configuration = [{'enabled': assign_ip,
                         'authorizedNetworks': authorized_networks}]
    settings['ipConfiguration'] = ip_configuration

    if no_backup:
      if backup_start_time or enable_bin_log:
        raise exceptions.ToolException('Argument --no-backup not allowed with'
                                       ' --backup-start-time or '
                                       '--enable_bin_log')
      settings['backupConfiguration'] = [{'startTime': '00:00',
                                          'enabled': 'False'}]
    if backup_start_time:
      backup_config = [{'startTime': backup_start_time,
                        'enabled': 'True',
                        'binaryLogEnabled': enable_bin_log}]
      settings['backupConfiguration'] = backup_config
    body = {'instance': instance_id, 'project': project_id, 'region': region,
            'settings': settings}
    request = sql.instances().insert(project=project_id,
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
      create operation if the create was successful.
    """
    printer = util.PrettyPrinter(0)
    printer.Print('Result of the create operation:')
    printer.PrintOperation(result)
