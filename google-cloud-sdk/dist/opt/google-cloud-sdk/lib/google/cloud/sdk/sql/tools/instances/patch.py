# Copyright 2013 Google Inc. All Rights Reserved.

"""Updates the settings of a Cloud SQL instance."""
from apiclient import errors

from google.cloud.sdk.calliope import base
from google.cloud.sdk.calliope import exceptions
from google.cloud.sdk.core.util import console_io
from google.cloud.sdk.sql import util


class Patch(base.Command):
  """Updates the settings of a Cloud SQL instance."""

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
        help='The activation policy for this instance. This specifies when the '
        'instance should be activated and is applicable only when the '
        'instance state is RUNNABLE.')
    parser.add_argument(
        '--assign-ip',
        required=False,
        action='store_true',
        help='Specified if the instance must be assigned an IP address.')
    parser.add_argument(
        '--no-assign-ip',
        required=False,
        action='store_true',
        help='Specified if the assigned IP address must be revoked.')
    parser.add_argument(
        '--authorized-gae-apps',
        required=False,
        nargs='+',
        type=str,
        help='A list of App Engine app ids that can access this instance.')
    parser.add_argument(
        '--clear-gae-apps',
        required=False,
        action='store_true',
        help=('Specified to clear the list of App Engine apps that can access'
              ' this instance.'))
    parser.add_argument(
        '--authorized-networks',
        required=False,
        nargs='+',
        type=str,
        help='The list of external networks that are allowed to connect to the'
        ' instance. Specified in CIDR notation, also known as \'slash\' '
        'notation (e.g. 192.168.100.0/24).')
    parser.add_argument(
        '--clear-authorized-networks',
        required=False,
        action='store_true',
        help='Clear the list of external networks that are allowed to connect '
        'to the instance.')
    parser.add_argument(
        '--backup-start-time',
        required=False,
        help='Start time for the daily backup configuration in UTC timezone in '
        'the 24 hour format - HH:MM.')
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
        '--no-enable-bin-log',
        required=False,
        action='store_true',
        help='Specified if binary log must be disabled.')
    parser.add_argument(
        '--follow-gae-app',
        required=False,
        help='The App Engine app this instance should follow. It must be in '
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
        help='The pricing plan for this instance.')
    parser.add_argument(
        '--replication',
        required=False,
        choices=['SYNCHRONOUS', 'ASYNCHRONOUS'],
        help='The type of replication this instance uses.')
    parser.add_argument(
        '--tier',
        '-t',
        required=False,
        help='The tier of service for this instance, for example D0, D1.')

  def GetExistingBackupConfig(self, instance_id):
    """Returns the existing backup configuration of the given instance.

    Args:
      instance_id: The Cloud SQL instance id.
    Returns:
      A dict object that represents the backup configuration of the given
      instance.
    """
    instance = self.command.ParentGroup().ParentGroup().instances.get(
        instance=instance_id)
    # At this point we support only one backup-config. So, we just use that
    # id.
    backup_id = instance['settings']['backupConfiguration'][0]['id']
    start_time = (instance['settings']['backupConfiguration'][0]['startTime'])
    enabled = (instance['settings']['backupConfiguration'][0]['enabled'])
    bin_log = (instance['settings']['backupConfiguration'][0]
               ['binaryLogEnabled'])
    backup_config = {'startTime': start_time, 'enabled': enabled,
                     'id': backup_id, 'binaryLogEnabled': bin_log}
    return backup_config

  def SetLocationPreference(self, settings, follow_gae_app, gce_zone):
    location_preference = {}
    if follow_gae_app:
      location_preference['followGaeApplication'] = follow_gae_app
    if gce_zone:
      location_preference['zone'] = gce_zone
    if follow_gae_app or gce_zone:
      settings['locationPreference'] = location_preference

  def SetIpConfiguration(self, settings, assign_ip, no_assign_ip,
                         authorized_networks, clear_authorized_networks):
    ip_configuration = {}
    if assign_ip or no_assign_ip:
      ip_configuration['enabled'] = bool(assign_ip)
    if authorized_networks or clear_authorized_networks:
      ip_configuration['authorizedNetworks'] = list(authorized_networks or [])
    if (assign_ip or no_assign_ip or authorized_networks or
        clear_authorized_networks):
      settings['ipConfiguration'] = ip_configuration

  def SetBackupConfiguration(self, settings, instance_id, backup_start_time,
                             enable_bin_log, no_enable_bin_log, no_backup):
    """Constructs the backup configuration sub-object for the patch method.

    Args:
      settings: The settings dict where the backup configuration should be set.
      instance_id: The Cloud SQL instance id.
      backup_start_time: Backup start time to be set.
      enable_bin_log: Set if bin log must be enabled.
      no_enable_bin_log: Set if bin log must be disabled.
      no_backup: Set if backup must be disabled.
    """
    backup_config = self.GetExistingBackupConfig(instance_id)
    # We have to explicitly populate the rest of the existing backup config
    # values for patch method because it will replace the entire
    # backupConfiguration value since it is a list.
    if no_backup:
      backup_config['enabled'] = False
    if backup_start_time:
      backup_config['startTime'] = backup_start_time
      backup_config['enabled'] = True
    if enable_bin_log:
      backup_config['binaryLogEnabled'] = True
    if no_enable_bin_log:
      backup_config['binaryLogEnabled'] = False
    if no_backup or backup_start_time or enable_bin_log or no_enable_bin_log:
      settings['backupConfiguration'] = [backup_config]

  def SetAuthorizedGaeApps(self, settings, authorized_gae_apps, clear_gae_apps):
    if authorized_gae_apps:
      settings['authorizedGaeApplications'] = authorized_gae_apps
    if clear_gae_apps:
      if authorized_gae_apps:
        raise exceptions.ToolException('Argument --clear-gae-apps not allowed '
                                       'with --authorized_gae_apps')
      settings['authorizedGaeApplications'] = None

  def Run(self, args):
    """Updates settings of a Cloud SQL instance using the patch api method.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      A dict object representing the operations resource describing the patch
      operation if the patch was successful.
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
    pricing_plan = args.pricing_plan
    authorized_gae_apps = args.authorized_gae_apps
    backup_start_time = args.backup_start_time
    clear_gae_apps = args.clear_gae_apps
    no_backup = args.no_backup
    follow_gae_app = args.follow_gae_app
    gce_zone = args.gce_zone
    authorized_networks = args.authorized_networks
    clear_authorized_networks = args.clear_authorized_networks
    assign_ip = args.assign_ip
    no_assign_ip = args.no_assign_ip
    enable_bin_log = args.enable_bin_log
    no_enable_bin_log = args.no_enable_bin_log
    if assign_ip and no_assign_ip:
      raise exceptions.ToolException('Argument --assign-ip not allowed with'
                                     ' --no-assign-ip')
    if enable_bin_log and no_enable_bin_log:
      raise exceptions.ToolException('Argument --no-enable-bin-log not allowed '
                                     'with --enable-bin-log')
    if no_backup and backup_start_time:
      raise exceptions.ToolException('Argument --no-backup not allowed with'
                                     ' --backup-start-time')
    if authorized_networks and clear_authorized_networks:
      raise exceptions.ToolException(
          'Argument --authorized-networks not '
          'allowed with --clear-authorized-networks')
    if follow_gae_app and gce_zone:
      raise exceptions.ToolException('Argument --gce-zone not allowed with'
                                     ' --follow-gae-app')

    settings = {}
    if tier:
      settings['tier'] = tier
    if pricing_plan:
      settings['pricingPlan'] = pricing_plan
    if replication:
      settings['replicationType'] = replication
    if activation_policy:
      settings['activationPolicy'] = activation_policy

    self.SetLocationPreference(settings, follow_gae_app, gce_zone)
    self.SetIpConfiguration(settings, assign_ip, no_assign_ip,
                            authorized_networks, clear_authorized_networks)
    self.SetBackupConfiguration(settings, instance_id, backup_start_time,
                                enable_bin_log, no_enable_bin_log, no_backup)
    self.SetAuthorizedGaeApps(settings, authorized_gae_apps, clear_gae_apps)

    body = {'instance': instance_id, 'settings': settings}
    printer = util.PrettyPrinter(0)
    printer.Print('This command will change the instance setting.')
    printer.Print('The following body will be used for the patch api method.')
    printer.Print(str(body))
    if not console_io.PromptContinue():
      return util.QUIT
    request = sql.instances().patch(project=project_id,
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
      patch operation if the patch was successful.
    """
    printer = util.PrettyPrinter(0)
    if result is not util.QUIT:
      printer.Print('Result of the patch operation:')
      printer.PrintOperation(result)
