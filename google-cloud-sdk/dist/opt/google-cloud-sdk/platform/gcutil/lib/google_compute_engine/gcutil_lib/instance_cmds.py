# Copyright 2012 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Commands for interacting with Google Compute Engine VM instances."""




import logging
import subprocess
import sys

from apiclient import errors

from google.apputils import app
from google.apputils import appcommands
import gflags as flags

from gcutil_lib import command_base
from gcutil_lib import gcutil_errors
from gcutil_lib import gcutil_logging
from gcutil_lib import image_cmds
from gcutil_lib import kernel_cmds
from gcutil_lib import metadata
from gcutil_lib import scopes
from gcutil_lib import ssh_keys
from gcutil_lib import version


FLAGS = flags.FLAGS
LOGGER = gcutil_logging.LOGGER
EPHEMERAL_ROOT_DISK_WARNING_MESSAGE = (
    'You appear to be running on a SCRATCH root disk '
    'so your data will not persist beyond the life '
    'of the instance. Consider using a persistent disk '
    'instead.\n'
    'For more information, see:\n'
    'https://developers.google.com/compute/docs/disks#persistentdisks'
)


def _DefineSchedulingFlags(flag_values):
  flags.DEFINE_enum('on_host_maintenance',
                    None,
                    ['terminate', 'migrate'],
                    'How the instance should behave when the host machine '
                    'undergoes maintenance that may temporarily impact '
                    'instance performance. Must be unspecified or '
                    '\'terminate\' for instances with scratch disk. If '
                    'unspecified, a default of \'terminate\' will be used for '
                    'instances with scratch disk, or \'migrate\' for instances '
                    'without scratch disk.',
                    flag_values=flag_values)
  flags.DEFINE_boolean('automatic_restart',
                       None,
                       'Whether the instance should be automatically '
                       'restarted whenever it is terminated by Compute '
                       'Engine (not terminated by user).',
                       flag_values=flag_values)


def _GetSchedulingFromFlags(flag_values):
  scheduling = {}
  if flag_values['on_host_maintenance'].present:
    scheduling['onHostMaintenance'] = flag_values.on_host_maintenance
  if flag_values['automatic_restart'].present:
    scheduling['automaticRestart'] = flag_values.automatic_restart
  return scheduling


class InstanceCommand(command_base.GoogleComputeCommand):
  """Base command for working with the instances collection."""

  print_spec = command_base.ResourcePrintSpec(
      summary=['name', 'zone', 'status', 'network-ip', 'external-ip'],
      field_mappings=(
          ('name', 'name'),
          ('machine-type', 'machineType'),
          ('image', 'image'),
          ('kernel', 'kernel'),
          ('network', 'networkInterfaces.network'),
          ('network-ip', 'networkInterfaces.networkIP'),
          ('external-ip', 'networkInterfaces.accessConfigs.natIP'),
          ('disks', 'disks.source'),
          ('zone', 'zone'),
          ('status', 'status'),
          ('status-message', 'statusMessage')),
      detail=(
          ('name', 'name'),
          ('description', 'description'),
          ('creation-time', 'creationTimestamp'),
          ('machine', 'machineType'),
          ('image', 'image'),
          ('kernel', 'kernel'),
          ('zone', 'zone'),
          ('tags-fingerprint', 'tags.fingerprint'),
          ('metadata-fingerprint', 'metadata.fingerprint'),
          ('status', 'status'),
          ('status-message', 'statusMessage')),
      sort_by='name')

  print_spec_with_scheduling_fields = command_base.ResourcePrintSpec(
      summary=print_spec.summary,
      field_mappings=print_spec.field_mappings,
      detail=print_spec.detail + (
          ('on-host-maintenance', 'scheduling.onHostMaintenance'),
          ('automatic-restart', 'scheduling.automaticRestart')),
      sort_by=print_spec.sort_by)

  def GetPrintSpec(self):
    if self.api.version >= version.get('v1beta16'):
      return self.print_spec_with_scheduling_fields
    return self.print_spec

  # A map from legal values for the disk "mode" option to the
  # corresponding API value. Keys in this map should be lowercase, as
  # we convert user provided values to lowercase prior to performing a
  # look-up.
  disk_modes = {
      'read_only': 'READ_ONLY',
      'ro': 'READ_ONLY',
      'read_write': 'READ_WRITE',
      'rw': 'READ_WRITE'}

  resource_collection_name = 'instances'

  # The default network interface name assigned by the service.
  DEFAULT_NETWORK_INTERFACE_NAME = 'nic0'

  # The default access config name
  DEFAULT_ACCESS_CONFIG_NAME = 'External NAT'

  # Currently, only access config type 'ONE_TO_ONE_NAT' is supported.
  ONE_TO_ONE_NAT_ACCESS_CONFIG_TYPE = 'ONE_TO_ONE_NAT'

  # Let the server select an ephemeral IP address.
  EPHEMERAL_ACCESS_CONFIG_NAT_IP = 'ephemeral'

  def __init__(self, name, flag_values):
    super(InstanceCommand, self).__init__(name, flag_values)

    flags.DEFINE_string('zone',
                        None,
                        '[Required] The zone for this request.',
                        flag_values=flag_values)

  def GetDetailRow(self, result):
    """Returns an associative list of items for display in a detail table.

    Args:
      result: A dict returned by the server.

    Returns:
      A list.
    """
    data = []
    # Add the disks
    for disk in result.get('disks', []):
      disk_info = [('type', disk['type'])]
      if 'mode' in disk:
        disk_info.append(('mode', disk['mode']))
      if 'deviceName' in disk:
        disk_info.append(('device-name', disk['deviceName']))
      if 'source' in disk:
        disk_info.append(('source', disk['source']))
      if 'boot' in disk:
        disk_info.append(('boot', disk['boot']))
      if 'deleteOnTerminate' in disk:
        disk_info.append(('delete-on-terminate', disk['deleteOnTerminate']))

      data.append(('disk', disk_info))

    # Add the networks
    for network in result.get('networkInterfaces', []):
      network_info = [('network', network.get('network')),
                      ('ip', network.get('networkIP'))]
      for config in network.get('accessConfigs', []):
        network_info.append(('access-configuration', config.get('name')))
        network_info.append(('type', config.get('type')))
        network_info.append(('external-ip', config.get('natIP')))
      data.append(('network-interface', network_info))

    # Add the service accounts
    for service_account in result.get('serviceAccounts', []):
      account_info = [('service-account', service_account.get('email')),
                      ('scopes', service_account.get('scopes'))]
      data.append(('service-account', account_info))

    # Add metadata
    if result.get('metadata', []):
      metadata_container = result.get('metadata', {}).get('items', [])
      metadata_info = []
      for i in metadata_container:
        metadata_info.append((i.get('key'), i.get('value')))
      if metadata_info:
        data.append(('metadata', metadata_info))
        data.append(('metadata-fingerprint',
                     result.get('metadata', {}).get('fingerprint')))

    # Add tags
    if result.get('tags', []):
      tags_container = result.get('tags', {}).get('items', [])
      tags_info = []
      for tag in tags_container:
        tags_info.append(tag)
      if tags_info:
        data.append(('tags', tags_info))
        data.append(('tags-fingerprint',
                     result.get('tags', {}).get('fingerprint')))

    return data

  def _ExtractExternalIpFromInstanceRecord(self, instance_record):
    """Extract the external IP(s) from an instance record.

    Args:
      instance_record: An instance as returned by the Google Compute Engine API.

    Returns:
      A list of internet IP addresses associated with this VM.
    """
    external_ips = set()

    for network_interface in instance_record.get('networkInterfaces', []):
      for access_config in network_interface.get('accessConfigs', []):
        # At the moment, we only know how to translate 1-to-1 NAT
        if (access_config.get('type') == self.ONE_TO_ONE_NAT_ACCESS_CONFIG_TYPE
            and 'natIP' in access_config):
          external_ips.add(access_config['natIP'])

    return list(external_ips)

  def _AddAuthorizedUserKeyToProject(self, authorized_user_key):
    """Update the project to include the specified user/key pair.

    Args:
      authorized_user_key: A dictionary of a user/key pair for the user.

    Returns:
      True iff the ssh key was added to the project.

    Raises:
      gcutil_errors.CommandError: If the metadata update fails.
    """
    project = self.api.projects.get(project=self._project).execute()
    common_instance_metadata = project.get('commonInstanceMetadata', {})

    project_metadata = common_instance_metadata.get(
        'items', [])
    project_ssh_keys = ssh_keys.SshKeys.GetAuthorizedUserKeysFromMetadata(
        project_metadata)
    if authorized_user_key in project_ssh_keys:
      return False
    else:
      project_ssh_keys.append(authorized_user_key)
      ssh_keys.SshKeys.SetAuthorizedUserKeysInMetadata(
          project_metadata, project_ssh_keys)

      try:
        request = self.api.projects.setCommonInstanceMetadata(
            project=self._project,
            body={'kind': self._GetResourceApiKind('metadata'),
                  'items': project_metadata})
        request.execute()
      except errors.HttpError:
        # A failure to add the ssh key probably means that the project metadata
        # has exceeded the max size. The user needs to either manually
        # clean up their project metadata, or set the ssh keys manually for this
        # instance. Either way, trigger a usage error to let them know.
        raise gcutil_errors.CommandError(
            'Unable to add the local ssh key to the project. Either manually '
            'remove some entries from the commonInstanceMetadata field of the '
            'project, or explicitly set the authorized keys for this instance.')
      return True

  def _PrepareRequestArgs(self, instance_context,
                          **other_args):
    """Gets the dictionary of API method keyword arguments.

    Args:
      instance_context: A context dict for this instance.
      **other_args: Keyword arguments that should be included in the request.

    Returns:
      Dictionary of keyword arguments that should be passed in the API call,
      includes all keyword arguments passed in 'other_args' plus
      common keys such as the name of the resource and the project.
    """
    kwargs = {
        'project': instance_context['project'],
        'instance': instance_context['instance'],
        'zone': instance_context['zone']
    }

    for key, value in other_args.items():
      kwargs[key] = value
    return kwargs

  def _AddComputeKeyToProject(self):
    """Update the current project to include the user's public ssh key.

    Returns:
      True iff the ssh key was added to the project.
    """
    compute_key = ssh_keys.SshKeys.GetPublicKey()
    return self._AddAuthorizedUserKeyToProject(compute_key)

  def _AutoDetectZone(self):
    """Instruct this command to auto detect zone instead of prompting."""
    def _GetZoneContext(object_type, context):
      if self._flags.zone:
        return self.DenormalizeResourceName(self._flags.zone)

      if object_type == 'instances':
        return self.GetZoneForResource(self.api.instances,
                                       context['instance'],
                                       project=context['project'])
      elif object_type == 'disks':
        return self.GetZoneForResource(self.api.disks,
                                       context['disk'],
                                       project=context['project'])

    self._context_parser.context_prompt_fxns['zone'] = _GetZoneContext

  def _AutoDetectZoneForDisksOnly(self):
    """Instruct this command to auto detect zone for disks only."""
    def _GetZoneContext(object_type, context):
      if self._flags.zone:
        return self.DenormalizeResourceName(self._flags.zone)
      elif object_type == 'disks':
        return self.GetZoneForResource(self.api.disks,
                                       context['disk'],
                                       project=context['project'])
      elif object_type == 'instances':
        self._flags.zone = self._GetZone(None)
        return self._flags.zone

    self._context_parser.context_prompt_fxns['zone'] = _GetZoneContext

  def _BuildAttachedDisk(self, disk_arg):
    """Converts a disk argument into an AttachedDisk object."""
    # Start with the assumption that the argument only specifies the
    # name of the disk resource.
    disk_name = disk_arg
    device_name = disk_arg
    mode = 'READ_WRITE'
    boot = False

    disk_parts = disk_arg.split(',')
    if len(disk_parts) > 1:
      # The argument includes new-style decorators. The first part is
      # the disk resource name. The other parts are optional key/value
      # pairs.
      disk_name = disk_parts[0]
      device_name = disk_parts[0]
      for option in disk_parts[1:]:
        if option == 'boot':
          boot = True
          continue
        if not '=' in option:
          raise ValueError('Invalid disk option: %s' % option)
        key, value = option.split('=', 2)
        if key == 'deviceName':
          device_name = value
        elif key == 'mode':
          mode = self.disk_modes.get(value.lower())
          if not mode:
            raise ValueError('Invalid disk mode: %s' % value)
        else:
          raise ValueError('Invalid disk option: %s' % key)
    else:
      # The user didn't provide any options using the newer key/value
      # syntax, so check to see if they have used the old syntax where
      # the device name is delimited by a colon.
      disk_parts = disk_arg.split(':')
      if len(disk_parts) > 1:
        disk_name = disk_parts[0]
        device_name = disk_parts[1]
        LOGGER.info(
            'Please use new disk device naming syntax: --disk=%s,deviceName=%s',
            disk_name,
            device_name)
    disk_url = self._context_parser.NormalizeOrPrompt('disks', disk_name)

    disk = {
        'type': 'PERSISTENT',
        'source': disk_url,
        'mode': mode,
        'deviceName': device_name,
        'boot': boot,
    }
    return disk


class AddInstance(InstanceCommand):
  """Create new virtual machine instances.

  Specify multiple instances as multiple arguments. Each instance will be
  created in parallel.
  """

  positional_args = '<instance-name-1> ... <instance-name-n>'
  status_field = 'status'
  _TERMINAL_STATUS = ['RUNNING', 'TERMINATED']
  _MAX_BOOT_DISK_NAME_LENGTH = 64

  def __init__(self, name, flag_values):
    super(AddInstance, self).__init__(name, flag_values)

    image_cmds.RegisterCommonImageFlags(flag_values)
    kernel_cmds.RegisterCommonKernelFlags(flag_values)

    flags.DEFINE_string('description',
                        '',
                        'An optional description for this instance.',
                        flag_values=flag_values)
    flags.DEFINE_string('image',
                        None,
                        'Specifies the image to use for this '
                        'instance. For example, \'--image=debian-7\' or '
                        '\'--image=debian-7-wheezy-v20130723\'. '
                        'To get a list of images built by Google, run '
                        '\'gcutil listimages --project=projects/google\'. '
                        'To get a list of images you have built, run '
                        '\'gcutil --project=<project-id> listimages\'.',
                        flag_values=flag_values)
    flags.DEFINE_string('kernel',
                        None,
                        '[Deprecated] Specifies the kernel to use for this '
                        'instance. For example, '
                        '\'--kernel=projects/google/global/kernels/'
                        'kernel-name\'. '
                        'By default, gcutil uses a preferred kernel based on '
                        'the image you select. To get a list of kernels '
                        'built by Google, run '
                        '\'gcutil listkernels --project=google\'.',
                        flag_values=flag_values)
    flags.DEFINE_boolean('persistent_boot_disk',
                         None,
                         '[Deprecated] Creates a persistent boot disk for this '
                         'instance. If this is set, gcutil creates a new '
                         'disk named \'<instance-name>\' and copies the '
                         'contents of the image onto the new disk and uses '
                         'it for booting. The preferred kernel for the '
                         'image will be used to boot, but it may be '
                         'overridden by passing \'--kernel\'. To use '
                         'scratch disk space for your root files, pass in '
                         '\'--nopersistent_boot_disk\'.',
                         flag_values=flag_values)
    flags.DEFINE_string('machine_type',
                        None,
                        '[Required] Specifies the machine type used for the '
                        'instance. For example, '
                        '\'--machine_type=machinetype-name\'. '
                        'To get a list of available machine types, run '
                        '\'gcutil listmachinetypes\'.',
                        flag_values=flag_values)
    flags.DEFINE_string('network',
                        'default',
                        'Specifies the network to use for this instance. If '
                        'not specified, the \'default\' network is used.',
                        flag_values=flag_values)
    flags.DEFINE_string('external_ip_address',
                        self.EPHEMERAL_ACCESS_CONFIG_NAT_IP,
                        'Specifies the external NAT IP of this new instance. '
                        'The default value is \'ephemeral\' and indicates '
                        'that the service should use any available ephemeral '
                        'IP. You can also specify "none" '
                        '(or an empty string) to indicate that no external '
                        'IP should be assigned to the instance. If you want '
                        'to explicitly use a certain IP, the IP must be '
                        'reserved by the project and not in use by '
                        'another resource.',
                        flag_values=flag_values)
    flags.DEFINE_multistring('disk',
                             [],
                             'Attaches a persistent disk to this instance. '
                             'You can also provide a list of comma-separated '
                             'name=value pairs options. Legal option names '
                             'are \'deviceName\', to specify the disk\'s '
                             'device name, and \'mode\', to indicate whether '
                             'the disk should be attached READ_WRITE '
                             '(the default) or READ_ONLY. You may also use '
                             'the \'boot\' flag to designate the disk as a '
                             'boot device. For example: '
                             '\'--disk=mydisk,deviceName=primarydisk,'
                             'mode=rw,boot\'',
                             flag_values=flag_values)
    flags.DEFINE_boolean('use_compute_key',
                         False,
                         'Specifies the Google Compute Engine ssh key as one '
                         'of the authorized ssh keys for the created '
                         'instance. This has the side effect of disabling '
                         'project-wide ssh key management for the instance.',
                         flag_values=flag_values)
    flags.DEFINE_boolean('add_compute_key_to_project',
                         None,
                         'Adds the default Google Compute Engine ssh key as '
                         'one of the authorized ssh keys for the project.'
                         'If the default key has already been added to the '
                         'project, then this will have no effect. '
                         'The default behavior is to add the key to the '
                         'project if no instance-specific keys are defined.',
                         flag_values=flag_values)
    flags.DEFINE_list('authorized_ssh_keys',
                      [],
                      'Updates the list of user/key-file pairs to the '
                      'specified entries, disabling project-wide key '
                      'management for this instance. These are specified as '
                      'a comma separated list of colon separated entries: '
                      'user1:keyfile1,user2:keyfile2,...',
                      flag_values=flag_values)
    flags.DEFINE_string('service_account',
                        'default',
                        'Specifies the service accounts for this instance. '
                        'Once set, the service account\'s credentials can '
                        'be used by the instance to make requests to other '
                        'services. The default account is \'default\'. You '
                        'can also set specific service account names. For '
                        'example, '
                        '\'123845678986@project.gserviceaccount.com\'',
                        flag_values=flag_values)
    flags.DEFINE_list('service_account_scopes',
                      [],
                      'Specifies the scope of credentials for the service '
                      'account(s) available to this instance. Specify '
                      'multiple scopes as comma-separated entries. You can '
                      'also use a set of supported scope aliases: %s'
                      % ', '.join(sorted(scopes.SCOPE_ALIASES.keys())),
                      flag_values=flag_values)
    flags.DEFINE_boolean('wait_until_running',
                         False,
                         'Specifies that gcutil should wait until the new '
                         'instance is running before returning.',
                         flag_values=flag_values)
    flags.DEFINE_list('tags',
                      [],
                      'Applies a set of tags to this instance. Tags can be '
                      'used for filtering and configuring network firewall '
                      'rules.',
                      flag_values=flag_values)
    flags.DEFINE_boolean('can_ip_forward',
                         False,
                         'Specifies that the newly-created instance is '
                         'allowed to send packets with a source IP address '
                         'that does not match its own and receive packets '
                         'whose destination IP address does not match its '
                         'own.',
                         flag_values=flag_values)
    _DefineSchedulingFlags(flag_values)

    self._metadata_flags_processor = metadata.MetadataFlagsProcessor(
        flag_values)

  def _GetErrorOperations(self, result_list):
    """Returns the list of operations that experienced a problem."""
    error_operations = []
    for result in result_list:
      error_list = result.get('error', {}).get('errors', [])
      if error_list:
        error_operations.append(result)
    return error_operations

  def _GetDefaultBootDiskName(self, instance_name):
    # The default boot disk name is the same as the instance name.
    return instance_name

  def Handle(self, *instance_names):
    """Add the specified instance.

    Args:
      *instance_names: A list of instance names to add.

    Returns:
      A tuple of (result, exceptions)

    Raises:
      UsageError: Improper arguments were passed to this command.
      UnsupportedCommand: Unsupported operation.
    """
    if not instance_names:
      raise app.UsageError('You must specify at least one instance name')

    if self.api.version > version.get('v1beta16'):
      if self._flags.persistent_boot_disk is False:
        raise gcutil_errors.UnsupportedCommand(
            'Persistent boot disk is required in v1 and later. You may still '
            'use ephemeral boot disks in the older APIs by specifying '
            '--service_version=v1beta15 or --service_version=v1beta16.')
      else:
        self._flags.persistent_boot_disk = True

      if self._flags.kernel:
        raise gcutil_errors.UnsupportedCommand(
            'Injected kernels are no longer supported in v1. You may still '
            'specify a kernel in the older APIs by specifying '
            '--service_version=v1beta15 or --service_version=v1beta16.')

    if len(instance_names) > 1 and self._flags.disk:
      raise gcutil_errors.CommandError(
          'Specifying a disk when starting multiple instances is not '
          'currently supported')

    if max([len(i) for i in instance_names]) > 32:
      LOGGER.warn('Hostnames longer than 32 characters trigger known issues '
                  'with some Linux distributions. If possible, you should '
                  'select a hostname that is shorter than 32 characters.')

    self._AutoDetectZoneForDisksOnly()
    instance_contexts = [self._context_parser.ParseContextOrPrompt(
        'instances', instance_name) for instance_name in instance_names]

    if not self._flags.machine_type:
      self._flags.machine_type = self._presenter.PromptForMachineType(
          self.api.machine_types)['name']

    # Processes the disks, so we can check for the presence of a boot
    # disk before prompting for image or kernel.
    disks = [self._BuildAttachedDisk(disk) for disk in self._flags.disk]

    if (self._flags.persistent_boot_disk is None
        and not self._HasBootDisk(disks)):
      self._flags.persistent_boot_disk = self._PresentSafetyPrompt(
          'You can create a new persistent boot disk (preferred) '
          'or use a scratch disk (not recommended). Do you want '
          'to create a persistent boot disk?')

    self._flags.image = self._context_parser.NormalizeOrPrompt(
        'images', command_base.ResolveImageTrackOrImage(
            self.api.images, self._flags.project, self._flags.image,
            lambda image: self._presenter.PresentElement(image['selfLink'])))

    if not self._flags.image and not self._HasBootDisk(disks):
      self._flags.image = self._presenter.PromptForImage(
          self.api.images)['selfLink']

    if self.api.version <= version.get('v1beta16'):
      if not self._flags['kernel'].present and self._HasBootDisk(disks):
        # Have boot disk but no kernel, prompt for a kernel.
        chosen_kernel = self._presenter.PromptForKernel(self.api.kernels)
        if chosen_kernel is not None:
          self._flags.kernel = chosen_kernel['selfLink']

    instance_metadata = self._metadata_flags_processor.GatherMetadata()
    if self._flags.authorized_ssh_keys or self._flags.use_compute_key:
      instance_metadata = self._AddSshKeysToMetadata(instance_metadata)

    # Instance names that we still want to create.
    instances_to_create = instance_contexts

    if self._flags.persistent_boot_disk and not self._HasBootDisk(disks):
      # Persistent boot device request. We need to create a new disk for each
      # VM and populate it with contents of the specified image.
      if self.api.version <= version.get('v1beta16'):
        # Read the preferredKernel from the image unless overridden by the user.
        if not self._flags.kernel:
          image_context = self._context_parser.ParseContextOrPrompt(
              'images', self._flags.image)

          image_resource = self.api.images.get(
              project=image_context['project'],
              image=image_context['image']).execute()

          if 'preferredKernel' in image_resource:
            self._flags.kernel = image_resource['preferredKernel']

      disk_creation_requests = []

      for instance_context in instance_contexts:
        boot_disk_name = self._GetDefaultBootDiskName(
            instance_context['instance'])

        instance_context['boot_disk_name'] = boot_disk_name

        LOGGER.info('Preparing boot disk [%s] for instance [%s]'
                    ' from disk image [%s].',
                    boot_disk_name, instance_context['instance'],
                    self._flags.image)
        disk_creation_requests.append(
            self._CreateDiskFromImageRequest(boot_disk_name,
                                             instance_context['zone'],
                                             instance_context['project']))

      if self.api.version <= version.get('v1beta16'):
        self._flags.image = None

      (disk_results, disk_exceptions) = self.ExecuteRequests(
          disk_creation_requests, wait_for_operations=True,
          collection_name='disks')

      if disk_exceptions:
        return (self.MakeListResult(disk_results, 'operationList'),
                disk_exceptions)

      # Cancel instance creation when the disk creation fails.
      disk_errors = self._GetErrorOperations(disk_results)
      if disk_errors:
        print 'There were errors creating persistent disks:'
        self.PrintResult(self.MakeListResult(disk_errors, 'operationList'))
        print 'As a result, the following instances will not be created:'

        failed_disks = []
        failed_instances = []
        for result in disk_errors:
          failed_result_context = self._context_parser.ParseContextOrPrompt(
              'disks', result['targetLink'])
          failed_disks.append(failed_result_context['disk'])
          for instance_context in instances_to_create:
            if (instance_context['boot_disk_name'] ==
                failed_result_context['disk'] and
                instance_context['zone'] == failed_result_context['zone'] and
                instance_context['project'] ==
                failed_result_context['project']):
              instances_to_create.remove(instance_context)
              failed_instances.append(instance_context['instance'])

        t = self._CreateFormatter()
        t.SetColumns(['Instance', 'Disk'])
        for instance, disk in zip(failed_instances, failed_disks):
          t.AppendRow([instance, disk])
        t.Write()

      # If there are no instances left to create, just quit.
      if not instances_to_create:
        return (self.MakeListResult(disk_results, 'operationList'),
                disk_exceptions)

    if self._flags.add_compute_key_to_project or (
        self._flags.add_compute_key_to_project is None and
        not 'sshKeys' in [entry.get('key', '') for entry in instance_metadata]):
      try:
        self._AddComputeKeyToProject()
      except ssh_keys.UserSetupError as e:
        LOGGER.warn('Could not generate compute ssh key: %s', e)

    self._ValidateFlags()

    wait_for_operations = (
        self._flags.wait_until_running or self._flags.synchronous_mode)

    requests = []
    for instance_context in instances_to_create:
      instance_disks = disks
      if 'boot_disk_name' in instance_context:
        instance_disks = [self._BuildAttachedDisk(
            '%s,boot' % instance_context['boot_disk_name'])] + disks
      requests.append(self._BuildRequestWithMetadata(
          instance_context, instance_metadata, instance_disks))

    (results, exceptions) = self.ExecuteRequests(
        requests, wait_for_operations=wait_for_operations)

    if self._flags.wait_until_running:
      instances_to_wait = results
      results = []
      for result in instances_to_wait:
        if self.IsResultAnOperation(result):
          results.append(result)
        else:
          result_context = self._context_parser.ParseContextOrPrompt(
              'instances', result['selfLink'])
          kwargs = self._PrepareRequestArgs(result_context)
          get_request = self.api.instances.get(**kwargs)
          instance_result = get_request.execute()
          instance_result = self._WaitUntilInstanceIsRunning(
              instance_result, kwargs)
          results.append(instance_result)

      return (self.MakeListResult(results, 'instanceList'), exceptions)
    else:
      return (self.MakeListResult(results, 'operationList'), exceptions)

  def _WaitUntilInstanceIsRunning(self, result, kwargs):
    """Waits for the instance to start.

    Periodically polls the server for current instance status. Exits if the
    status of the instance is RUNNING or TERMINATED or the maximum waiting
    timeout has been reached. In both cases returns the last known instance
    details.

    Args:
      result: the current state of the instance.
      kwargs: keyword arguments to _instances_api.get()

    Returns:
      Json containing full instance information.
    """
    current_status = result[self.status_field]
    start_time = self._timer.time()
    instance_name = kwargs['instance']
    LOGGER.info('Ensuring %s is running.  Will wait to start for: %d seconds.',
                instance_name, self._flags.max_wait_time)
    while (self._timer.time() - start_time < self._flags.max_wait_time and
           current_status not in self._TERMINAL_STATUS):
      LOGGER.info(
          'Waiting for instance \'%s\' to start. '
          'Current status: %s. Sleeping for %ss.',
          instance_name,
          current_status, self._flags.sleep_between_polls)
      self._timer.sleep(self._flags.sleep_between_polls)
      result = self.api.instances.get(**kwargs).execute()
      current_status = result[self.status_field]
    if current_status not in self._TERMINAL_STATUS:
      LOGGER.warn('Timeout reached. Instance %s has not yet started.',
                  instance_name)
    return result

  def _AddSshKeysToMetadata(self, instance_metadata):
    instance_ssh_keys = ssh_keys.SshKeys.GetAuthorizedUserKeys(
        use_compute_key=self._flags.use_compute_key,
        authorized_ssh_keys=self._flags.authorized_ssh_keys)
    if instance_ssh_keys:
      new_value = ['%(user)s:%(key)s' % user_key
                   for user_key in instance_ssh_keys]
      # Have the new value extend the old value
      old_values = [entry['value'] for entry in instance_metadata
                    if entry['key'] == 'sshKeys']
      all_values = '\n'.join(old_values + new_value)
      instance_metadata = [entry for entry in instance_metadata
                           if entry['key'] != 'sshKeys']
      instance_metadata.append({'key': 'sshKeys', 'value': all_values})
    return instance_metadata

  def _HasBootDisk(self, disks):
    """Determines if any of the disks in a list is a boot disk."""
    for disk in disks:
      if disk.get('boot', False):
        return True

    return False

  def _ValidateFlags(self):
    """Validate flags coming in before we start building resources.

    Raises:
      app.UsageError: If service account explicitly given without scopes.
      gcutil_errors.CommandError: If scopes contains ' '.
    """
    if self._flags.service_account and self._flags.service_account_scopes:
      # Ensures that the user did not space-delimit his or her scopes
      # list.
      for scope in self._flags.service_account_scopes:
        if ' ' in scope:
          raise gcutil_errors.CommandError(
              'Scopes list must be comma-delimited, not space-delimited.')
    elif self._flags['service_account'].present:
      raise app.UsageError(
          '--service_account given without --service_account_scopes.')

  def _CreateDiskFromImageRequest(self, disk_name, disk_zone, disk_project):
    """Build a request that creates disk from source image.

    Args:
      disk_name: Name of the disk.
      disk_zone: Zone for the disk.
      disk_project: Project for the disk

    Returns:
      The prepared disk insert request.
    """
    disk_resource = {
        'kind': self._GetResourceApiKind('instance'),
        'name': disk_name,
        'description': 'Persistent boot disk created from %s.' % (
            self._flags.image),
    }

    source_image_url = self._context_parser.NormalizeOrPrompt(
        'images', self._flags.image)

    kwargs = {
        'project': disk_project,
        'body': disk_resource,
        'sourceImage': source_image_url,
        'zone': disk_zone,
    }
    return self.api.disks.insert(**kwargs)

  def _BuildRequestWithMetadata(
      self, instance_context, instance_metadata, disks):
    """Build a request to add the specified instance, given the ssh keys for it.

    Args:
      instance_context: Context dict for the instance that we are building the
        request for.
      instance_metadata: The metadata to be passed to the VM.  This is in the
        form of [{'key': <key>, 'value': <value>}] form, ready to be
        sent to the server.
      disks: Disks to attach to the instance.

    Returns:
      The prepared instance request.

    Raises:
      UsageError: Flags were not allowed in this service version.
    """
    instance_resource = {
        'kind': self._GetResourceApiKind('instance'),
        'name': instance_context['instance'],
        'description': self._flags.description,
        'networkInterfaces': [],
        'disks': disks,
        'metadata': [],
        }

    if self.api.version <= version.get('v1beta16'):
      if self._flags.image:
        instance_resource['image'] = self._context_parser.NormalizeOrPrompt(
            'images', self._flags.image)

    if self.api.version <= version.get('v1beta16'):
      if self._flags.kernel:
        instance_resource['kernel'] = self._context_parser.NormalizeOrPrompt(
            'kernels', self._flags.kernel)

    if self._flags.machine_type:
      instance_resource['machineType'] = self._context_parser.NormalizeOrPrompt(
          'machineTypes', self._flags.machine_type)

    if self._flags['can_ip_forward'].present:
      instance_resource['canIpForward'] = self._flags.can_ip_forward

    if self._flags.network:
      network_interface = {
          'network': self._context_parser.NormalizeOrPrompt(
              'networks', self._flags.network)
          }
      external_ip_address = self._flags.external_ip_address
      if external_ip_address and external_ip_address.lower() != 'none':
        access_config = {
            'name': self.DEFAULT_ACCESS_CONFIG_NAME,
            'type': self.ONE_TO_ONE_NAT_ACCESS_CONFIG_TYPE,
            }
        if external_ip_address.lower() != self.EPHEMERAL_ACCESS_CONFIG_NAT_IP:
          access_config['natIP'] = self._flags.external_ip_address

        network_interface['accessConfigs'] = [access_config]

      instance_resource['networkInterfaces'].append(network_interface)

    metadata_subresource = {
        'kind': self._GetResourceApiKind('metadata'),
        'items': []}

    metadata_subresource['items'].extend(instance_metadata)
    instance_resource['metadata'] = metadata_subresource

    if self._flags.service_account and (
        len(self._flags.service_account_scopes)):
      instance_resource['serviceAccounts'] = []
      expanded_scopes = scopes.ExpandScopeAliases(
          self._flags.service_account_scopes)
      instance_resource['serviceAccounts'].append({
          'email': self._flags.service_account,
          'scopes': expanded_scopes})

    instance_resource['tags'] = {'items': sorted(set(self._flags.tags))}

    if self.api.version >= version.get('v1beta16'):
      scheduling = _GetSchedulingFromFlags(self._flags)
      # Only set the instance's scheduling if it is populated.
      if scheduling:
        instance_resource['scheduling'] = scheduling
    elif self._flags['on_host_maintenance'].present:
      raise app.UsageError(
          'Flag --on_host_maintenance is only supported for API versions '
          'v1beta16 and later.')
    elif self._flags['automatic_restart'].present:
      raise app.UsageError(
          'Flag --automatic_restart is only supported for API versions '
          'v1beta16 and later.')

    return self.api.instances.insert(
        project=instance_context['project'],
        zone=instance_context['zone'],
        body=instance_resource)


class GetInstance(InstanceCommand):
  """Get a VM instance."""

  positional_args = '<instance-name>'

  def Handle(self, instance_name):
    """Get the specified instance.

    Args:
      instance_name: The name of the instance to get.

    Returns:
      The result of getting the instance.
    """
    self._AutoDetectZone()
    instance_context = self._context_parser.ParseContextOrPrompt('instances',
                                                                 instance_name)

    instance_request = self.api.instances.get(
        **self._PrepareRequestArgs(instance_context))

    return instance_request.execute()


class DeleteInstance(InstanceCommand):
  """Delete one or more VM instances.

  Specify multiple disks as multiple arguments. Instances will be deleted
  in parallel.
  """
  positional_args = '<instance-name-1> ... <instance-name-n>'
  safety_prompt = 'Delete instance'

  def __init__(self, name, flag_values):
    super(DeleteInstance, self).__init__(name, flag_values)

    flags.DEFINE_boolean('delete_boot_pd',
                         None,
                         'Delete the attached boot persistent disk.',
                         flag_values=flag_values)

  def _FindBootPersistentDisks(self, instance_context_list):
    """Find any persistent boot disks for the specified instances.

    Args:
      instance_context_list:  A list of instance contexts.

    Returns:
      The list of attached boot disks.
    """
    bootdisks = []
    for instance_context in instance_context_list:
      instance_list_info = (
          self.GetListResultForResourceWithZone(
              self.api.instances, instance_context['instance'],
              zone=instance_context['zone'],
              project=instance_context['project']))

      bootdisks.extend(disk for disk
                       in instance_list_info['disks']
                       if (disk['type'] == 'PERSISTENT' and 'boot' in disk
                           and disk['boot']))
    return bootdisks

  def Handle(self, *instance_names):
    """Delete the specified instances.

    Args:
      *instance_names: Names of the instances to delete.

    Returns:
      The result of deleting the instance.

    Raises:
      UsageError: Required flags were missing.
    """

    requests = []
    disk_requests = []
    bootdisks = []
    disk_names = []

    # Check to see if there is no instance, and just quit.
    if not instance_names:
      raise app.UsageError('You must specify an instance to delete.')

    self._AutoDetectZone()
    instance_contexts = [self._context_parser.ParseContextOrPrompt(
        'instances', name) for name in instance_names]

    # Check to see which persistent disks are attached,
    # and also which are boot.
    if self._flags.delete_boot_pd is not False:
      bootdisks = self._FindBootPersistentDisks(instance_contexts)
      disk_names = [self.DenormalizeResourceName(disk['source'])
                    for disk in bootdisks]

      if bootdisks:
        # If the -f flag is specified, then delete_boot_pd flag is required.
        if self._flags.force and self._flags.delete_boot_pd is None:
          raise app.UsageError(
              'Some of your instances have boot disks attached. To use the '
              '--force flag when deleting instances with boot disks, you '
              'must also specify the --[no]delete_boot_pd flag explicitly.')

        if self._flags.delete_boot_pd is None:
          self._flags.delete_boot_pd = self._PresentSafetyPrompt(
              'Delete persistent boot disk ' + ', '.join(disk_names), False)
        if self._flags.delete_boot_pd:
          for disk in bootdisks:
            # Prepare delete disk commands to execute after deleting
            # the instances.
            disk_context = self._context_parser.ParseContextOrPrompt(
                'disks', disk['source'])

            disk_requests.append(self.api.disks.delete(
                project=disk_context['project'],
                disk=disk_context['disk'],
                zone=disk_context['zone']))

    # All of the instance deletions must go through first.
    for instance_context in instance_contexts:
      requests.append(self.api.instances.delete(
          **self._PrepareRequestArgs(instance_context)))

    wait_for_operations = self._flags.synchronous_mode or disk_requests

    (results, exceptions) = self.ExecuteRequests(
        requests, wait_for_operations=wait_for_operations)

    # Now all of the disk deletions go through.
    if disk_requests:
      (disk_results, disk_exceptions) = self.ExecuteRequests(
          disk_requests, collection_name='disks')

      results.extend(disk_results)
      exceptions.extend(disk_exceptions)

    # If the user had boot disks that they didn't want to be deleted,
    # remind them that they have newly orphaned boot PDs.
    if disk_names and self._flags.delete_boot_pd is False:
      print 'INFO:  The following boot persistent disks were orphaned:'
      print ', '.join(disk_names)

    return (self.MakeListResult(results, 'operationList'), exceptions)


class ListInstances(InstanceCommand, command_base.GoogleComputeListCommand):
  """List the VM instances for a project."""

  def IsZoneLevelCollection(self):
    return True

  def IsGlobalLevelCollection(self):
    return False

  def ListFunc(self):
    """Returns the function for listing instances."""
    return self.api.instances.list

  def ListZoneFunc(self):
    """Returns the function for listing instances in a zone."""
    return self.api.instances.list

  def ListAggregatedFunc(self):
    """Returns the function for listing instances across all zones."""
    if self.api.version >= 'v1beta15':
      return self.api.instances.aggregatedList


class AddAccessConfig(InstanceCommand):
  """Create an access config for a VM instance's network interface."""

  positional_args = '<instance-name>'

  def __init__(self, name, flag_values):
    super(AddAccessConfig, self).__init__(name, flag_values)

    flags.DEFINE_string('network_interface_name',
                        self.DEFAULT_NETWORK_INTERFACE_NAME,
                        '[Required] Specifies the name of the instance\'s '
                        'network interface to add the new access config.',
                        flag_values=flag_values)

    flags.DEFINE_string('access_config_name',
                        self.DEFAULT_ACCESS_CONFIG_NAME,
                        '[Required] Specifies the name of the new access '
                        'config.',
                        flag_values=flag_values)

    flags.DEFINE_string('access_config_type',
                        self.ONE_TO_ONE_NAT_ACCESS_CONFIG_TYPE,
                        '[Required] Specifies the type of the new access '
                        'config. Currently only type "ONE_TO_ONE_NAT" is '
                        'supported.',
                        flag_values=flag_values)

    flags.DEFINE_string('access_config_nat_ip',
                        self.EPHEMERAL_ACCESS_CONFIG_NAT_IP,
                        'The external NAT IP of the new access config. The '
                        'default value "ephemeral" indicates the service '
                        'should choose any available ephemeral IP. If an '
                        'explicit IP is given, that IP must be reserved '
                        'by the project and not in use by another resource.',
                        flag_values=flag_values)

  def Handle(self, instance_name):
    """Adds an access config to an instance's network interface.

    Args:
      instance_name: The instance name to which to add the new access config.

    Returns:
      An operation resource.
    """
    access_config_resource = {
        'name': self._flags.access_config_name,
        'type': self._flags.access_config_type,
        }
    if (self._flags.access_config_nat_ip.lower() !=
        self.EPHEMERAL_ACCESS_CONFIG_NAT_IP):
      access_config_resource['natIP'] = self._flags.access_config_nat_ip

    if self.api.version >= 'v1beta15':
      kwargs = {'networkInterface': self._flags.network_interface_name}
    else:
      kwargs = {'network_interface': self._flags.network_interface_name}

    self._AutoDetectZone()
    instance_context = self._context_parser.ParseContextOrPrompt('instances',
                                                                 instance_name)

    add_access_config_request = self.api.instances.addAccessConfig(
        **self._PrepareRequestArgs(
            instance_context,
            body=access_config_resource,
            **kwargs))
    return add_access_config_request.execute()


class DeleteAccessConfig(InstanceCommand):
  """Delete an access config from a VM instance's network interface."""

  positional_args = '<instance-name>'

  def __init__(self, name, flag_values):
    super(DeleteAccessConfig, self).__init__(name, flag_values)

    flags.DEFINE_string('network_interface_name',
                        self.DEFAULT_NETWORK_INTERFACE_NAME,
                        '[Required] The name of the instance\'s network '
                        'interface from which to delete the access config.',
                        flag_values=flag_values)

    flags.DEFINE_string('access_config_name',
                        self.DEFAULT_ACCESS_CONFIG_NAME,
                        '[Required] The name of the access config to delete.',
                        flag_values=flag_values)

  def Handle(self, instance_name):
    """Deletes an access config from an instance's network interface.

    Args:
      instance_name: The instance name from which to delete the access config.

    Returns:
      An operation resource.
    """
    if self.api.version >= 'v1beta15':
      kwargs = {'accessConfig': self._flags.access_config_name,
                'networkInterface': self._flags.network_interface_name}
    else:
      kwargs = {'access_config': self._flags.access_config_name,
                'network_interface': self._flags.network_interface_name}

    self._AutoDetectZone()
    instance_context = self._context_parser.ParseContextOrPrompt('instances',
                                                                 instance_name)

    delete_access_config_request = self.api.instances.deleteAccessConfig(
        **self._PrepareRequestArgs(instance_context, **kwargs))
    return delete_access_config_request.execute()


class SetScheduling(InstanceCommand):
  """Set scheduling options for an instance."""

  positional_args = '<instance-name>'

  def __init__(self, name, flag_values):
    super(SetScheduling, self).__init__(name, flag_values)
    _DefineSchedulingFlags(flag_values)

  def Handle(self, instance_name):
    """Set scheduling options for an instance.

    Args:
      instance_name: The instance name for which to set scheduling options.

    Returns:
      An operation resource.
    """

    if self.api.version < version.get('v1beta16'):
      raise gcutil_errors.CommandError(
          'The setscheduling command is only supported for API versions '
          'v1beta16 and later.')

    scheduling = _GetSchedulingFromFlags(self._flags)

    self._AutoDetectZone()
    instance_context = self._context_parser.ParseContextOrPrompt(
        'instances', instance_name)

    set_scheduling_request = self.api.instances.setScheduling(
        **self._PrepareRequestArgs(instance_context, body=scheduling))
    return set_scheduling_request.execute()


class SshInstanceBase(InstanceCommand):
  """Base class for SSH-based commands."""

  # We want everything after 'ssh <instance>' to be passed on to the
  # ssh command in question.  As such, all arguments to the utility
  # must come before the 'ssh' command.
  sort_args_and_flags = False

  def __init__(self, name, flag_values):
    super(SshInstanceBase, self).__init__(name, flag_values)

    flags.DEFINE_integer(
        'ssh_port',
        22,
        'TCP port to connect to',
        flag_values=flag_values)
    flags.DEFINE_multistring(
        'ssh_arg',
        [],
        'Additional arguments to pass to ssh',
        flag_values=flag_values)
    flags.DEFINE_integer(
        'ssh_key_push_wait_time',
        120,  # 2 minutes
        'Number of seconds to wait for updates to project-wide ssh keys '
        'to cascade to the instances within the project',
        flag_values=flag_values)

  def PrintResult(self, _):
    """Override the PrintResult to be a noop."""
    pass

  def _GetInstanceResource(self, instance_name):
    """Get the instance resource. This is the dictionary returned by the API.

    Args:
      instance_name: The name of the instance to retrieve the ssh address for.

    Returns:
      The data for the instance resource as returned by the API.

    Raises:
      gcutil_errors.CommandError: If the instance does not exist.
    """
    self._AutoDetectZone()
    instance_context = self._context_parser.ParseContextOrPrompt('instances',
                                                                 instance_name)

    request = self.api.instances.get(
        **self._PrepareRequestArgs(instance_context))
    result = request.execute()
    if not result:
      raise gcutil_errors.CommandError(
          'Unable to find the instance %s.' % (instance_name))
    return result

  def _GetSshAddress(self, instance_resource):
    """Retrieve the ssh address from the passed instance resource data.

    Args:
      instance_resource: The resource data of the instance for which
        to retrieve the ssh address.

    Returns:
      The ssh address and port.

    Raises:
      gcutil_errors.CommandError: If the instance has no external address.
    """
    external_addresses = self._ExtractExternalIpFromInstanceRecord(
        instance_resource)
    if len(external_addresses) < 1:
      raise gcutil_errors.CommandError(
          'Cannot connect to an instance with no external address')

    return (external_addresses[0], self._flags.ssh_port)

  def _EnsureSshable(self, instance_resource):
    """Ensure that the user can ssh into the specified instance.

    This method checks if the instance has SSH keys defined for it, and if
    it does not this makes sure the enclosing project contains a metadata
    entry for the user's public ssh key.

    If the project is updated to add the user's ssh key, then this method
    waits for the amount of time specified by the wait_time_for_ssh_key_push
    flag for the change to cascade down to the instance.

    Args:
      instance_resource: The resource data for the instance to which to connect.

    Raises:
      gcutil_errors.CommandError: If the instance is not in the RUNNING state.
    """
    instance_status = instance_resource.get('status')
    if instance_status != 'RUNNING':
      raise gcutil_errors.CommandError(
          'Cannot connect to the instance since its current status is %s.'
          % instance_status)

    instance_metadata = instance_resource.get('metadata', {})

    instance_ssh_key_entries = (
        [entry for entry in instance_metadata.get(
            'items', [])
         if entry.get('key') == 'sshKeys'])

    if not instance_ssh_key_entries:
      if self._AddComputeKeyToProject():
        wait_time = self._flags.ssh_key_push_wait_time
        LOGGER.info('Updated project with new ssh key. It can take several '
                    'minutes for the instance to pick up the key.')
        LOGGER.info('Waiting %s seconds before attempting to connect.',
                    wait_time)
        self._timer.sleep(wait_time)

  def _BuildSshCmd(self, instance_resource, command, args):
    """Builds the given SSH-based command line with the given arguments.

    A complete SSH-based command line is built from the given command,
    any common arguments, and the arguments provided. The value of
    each argument is formatted using a dictionary that contains the
    following keys: host and port.

    Args:
      instance_resource: The resource data of the instance for which
        to build the ssh command.
      command: the ssh-based command to run (e.g. ssh or scp)
      args: arguments for the command

    Returns:
      The command line used to perform the requested ssh operation.

    Raises:
      IOError: An error occured accessing SSH details.
    """
    (host, port) = self._GetSshAddress(instance_resource)
    values = {'host': host,
              'port': port,
              'user': self._flags.ssh_user}

    command_line = [
        command,
        '-o', 'UserKnownHostsFile=/dev/null',
        '-o', 'CheckHostIP=no',
        '-o', 'StrictHostKeyChecking=no',
        '-i', self._flags.private_key_file,
    ] + self._flags.ssh_arg

    if LOGGER.level <= logging.DEBUG:
      command_line.append('-v')

    for arg in args:
      command_line.append(arg % values)

    return command_line

  def _IsInstanceRootDiskPersistent(self, instance_resource):
    """Determines if instance's root disk is persistent.

    Args:
      instance_resource: Dictionary result from a get instance json request.

    Returns:
      True if the root disk of the VM instance is persistent, otherwise False.
    """
    boot_disk_is_persistent = False
    for disk in instance_resource.get('disks', []):
      if disk.get('boot', False) and disk.get('type', '') == 'PERSISTENT':
        boot_disk_is_persistent = True
    return boot_disk_is_persistent

  def _PrintEphemeralDiskWarning(self, instance_resource):
    """Prints a warning message the instance is running on an ephemeral disk.

    Args:
      instance_resource: Dictionary result from a get instance json request.
    """
    if not self._IsInstanceRootDiskPersistent(instance_resource):
      LOGGER.warn(EPHEMERAL_ROOT_DISK_WARNING_MESSAGE)

  def _RunSshCmd(self, instance_name, command, args):
    """Run the given SSH-based command line with the given arguments.

    The specified SSH-base command is run for the arguments provided.
    The value of each argument is formatted using a dictionary that
    contains the following keys: host and port.

    Args:
      instance_name: The name of the instance for which to run the ssh command.
      command: the ssh-based command to run (e.g. ssh or scp)
      args: arguments for the command

    Raises:
      IOError: An error occured accessing SSH details.
    """
    instance_resource = self._GetInstanceResource(instance_name)
    command_line = self._BuildSshCmd(instance_resource, command, args)
    self._PrintEphemeralDiskWarning(instance_resource)

    try:
      self._EnsureSshable(instance_resource)
    except ssh_keys.UserSetupError as e:
      LOGGER.warn('Could not generate compute ssh key: %s', e)
      return

    LOGGER.info('Running command line: %s', ' '.join(command_line))
    try:
      sys.exit(subprocess.call(command_line))
    except OSError as e:
      LOGGER.error('There was a problem executing the command: %s', e)


class SshToInstance(SshInstanceBase):
  """Connect to a VM instance with ssh."""

  positional_args = '<instance-name> <ssh-args>'

  def _GenerateSshArgs(self, *argv):
    """Generates the command line arguments for the ssh command.

    Args:
      *argv: List of additional ssh command line args, if any.

    Returns:
      The complete ssh argument list.
    """
    ssh_args = ['-A', '-p', '%(port)d', '%(user)s@%(host)s', '--']

    escaped_args = [a.replace('%', '%%') for a in argv]
    ssh_args.extend(escaped_args)

    return ssh_args

  def Handle(self, instance_name, *argv):
    """SSH into the instance.

    Args:
      instance_name: The name of the instance to ssh to.
      *argv: The remaining unhandled arguments.

    Returns:
      The result of the ssh command
    """
    ssh_args = self._GenerateSshArgs(*argv)
    self._RunSshCmd(instance_name, 'ssh', ssh_args)


class PushToInstance(SshInstanceBase):
  """Push one or more files to a VM instance."""

  positional_args = '<instance-name> <file-1> ... <file-n> <destination>'

  def _GenerateScpArgs(self, *argv):
    """Generates the command line arguments for the scp command.

    Args:
      *argv: List of files to push and instance-relative destination.

    Returns:
      The scp argument list.

    Raises:
      gcutil_errors.CommandError: If an invalid number of arguments are passed
          in.
    """
    if len(argv) < 2:
      raise gcutil_errors.CommandError('Invalid number of arguments passed.')

    scp_args = ['-r', '-P', '%(port)d', '--']

    escaped_args = [a.replace('%', '%%') for a in argv]
    scp_args.extend(escaped_args[0:-1])
    scp_args.append('%(user)s@%(host)s:' + escaped_args[-1])

    return scp_args

  def Handle(self, instance_name, *argv):
    """Pushes one or more files into the instance.

    Args:
      instance_name: The name of the instance to push files to.
      *argv: The remaining unhandled arguments.

    Returns:
      The result of the scp command

    Raises:
      gcutil_errors.CommandError: If an invalid number of arguments are passed
        in.
    """
    scp_args = self._GenerateScpArgs(*argv)
    self._RunSshCmd(instance_name, 'scp', scp_args)


class PullFromInstance(SshInstanceBase):
  """Pull one or more files from a VM instance."""

  positional_args = '<instance-name> <file-1> ... <file-n> <destination>'

  def _GenerateScpArgs(self, *argv):
    """Generates the command line arguments for the scp command.

    Args:
      *argv: List of files to pull and local-relative destination.

    Returns:
      The scp argument list.

    Raises:
      gcutil_errors.CommandError: If an invalid number of arguments are passed
          in.
    """
    if len(argv) < 2:
      raise gcutil_errors.CommandError('Invalid number of arguments passed.')

    scp_args = ['-r', '-P', '%(port)d', '--']

    escaped_args = [a.replace('%', '%%') for a in argv]
    for arg in escaped_args[0:-1]:
      scp_args.append('%(user)s@%(host)s:' + arg)
    scp_args.append(escaped_args[-1])

    return scp_args

  def Handle(self, instance_name, *argv):
    """Pulls one or more files from the instance.

    Args:
      instance_name: The name of the instance to pull files from.
      *argv: The remaining unhandled arguments.

    Returns:
      The result of the scp command

    Raises:
      gcutil_errors.CommandError: If an invalid number of arguments are passed
          in.
    """
    scp_args = self._GenerateScpArgs(*argv)
    self._RunSshCmd(instance_name, 'scp', scp_args)


class GetSerialPortOutput(InstanceCommand):
  """Get the output of a VM instance's serial port."""

  positional_args = '<instance-name>'

  def Handle(self, instance_name):
    """Get the specified instance's serial port output.

    Args:
      instance_name: The name of the instance.

    Returns:
      The output of the instance's serial port.
    """
    self._AutoDetectZone()
    instance_context = self._context_parser.ParseContextOrPrompt('instances',
                                                                 instance_name)

    instance_request = self.api.instances.getSerialPortOutput(
        **self._PrepareRequestArgs(instance_context))

    return instance_request.execute()

  def PrintResult(self, result):
    """Override the PrintResult to be a noop."""

    if self._flags.print_json:
      super(GetSerialPortOutput, self).PrintResult(result)
    else:
      print result['contents'].encode('utf-8')


class ResetInstance(InstanceCommand):
  """Reset a VM instance, resulting in a reboot."""

  positional_args = '<instance-name>'

  def Handle(self, instance_name):
    """Initiate a hard reset on the instance.

    Args:
      instance_name: The instance name to reset.

    Returns:
      An operation resource.
    """
    self._AutoDetectZone()
    instance_context = self._context_parser.ParseContextOrPrompt('instances',
                                                                 instance_name)

    reset_request = self.api.instances.reset(
        **self._PrepareRequestArgs(instance_context))

    return reset_request.execute()


class OptimisticallyLockedInstanceCommand(InstanceCommand):
  """Base class for instance commands that require a fingerprint."""

  def __init__(self, name, flag_values):
    super(OptimisticallyLockedInstanceCommand, self).__init__(name, flag_values)

    flags.DEFINE_string('fingerprint',
                        None,
                        '[Required] Fingerprint of the data to be '
                        'overwritten. This fingerprint provides optimistic '
                        'locking. Data will only be set if the given '
                        'fingerprint matches the state of the data prior to '
                        'this request.',
                        flag_values=flag_values)

  def Handle(self, instance_name):
    """Invokes the HandleCommand method of the subclass."""
    if not self._flags.fingerprint:
      raise app.UsageError('You must provide a fingerprint with your request.')
    return self.HandleCommand(instance_name)


class SetMetadata(OptimisticallyLockedInstanceCommand):
  """Set the metadata for a VM instance.

  This method overwrites existing instance metadata with new metadata.
  Common metadata (project-wide) is preserved.

  For example, running:

    gcutil --project=<project-name> setinstancemetadata my-instance \
      --metadata="key1:value1" \
      --fingerprint=<original-fingerprint>
    ...
    gcutil --project=<project-name> setinstancemetadata my-instance \
      --metadata="key2:value2" \
      --fingerprint=<new-fingerprint>

  will result in 'my-instance' having 'key2:value2' as its metadata.
  """

  positional_args = '<instance-name>'

  def __init__(self, name, flag_values):
    super(SetMetadata, self).__init__(name, flag_values)

    flags.DEFINE_bool('force',
                      None,
                      'Set new metadata even if the key \'sshKeys\' will '
                      'no longer be present.',
                      flag_values=flag_values,
                      short_name='f')
    self._metadata_flags_processor = metadata.MetadataFlagsProcessor(
        flag_values)

  def HandleCommand(self, instance_name):
    """Set instance-specific metadata.

    Args:
      instance_name: The name of the instance scoping this request.

    Returns:
      An operation resource.
    """
    self._AutoDetectZone()
    instance_context = self._context_parser.ParseContextOrPrompt('instances',
                                                                 instance_name)

    new_metadata = self._metadata_flags_processor.GatherMetadata()
    if not self._flags.force:
      new_keys = set([entry['key'] for entry in new_metadata])
      get_project = self.api.projects.get(project=instance_context['project'])
      project_resource = get_project.execute()
      project_metadata = project_resource.get('commonInstanceMetadata', {})
      project_metadata = project_metadata.get('items', [])
      project_keys = set([entry['key'] for entry in project_metadata])

      get_instance = self.api.instances.get(
          **self._PrepareRequestArgs(instance_context))
      instance_resource = get_instance.execute()
      instance_metadata = instance_resource.get('metadata', {})
      instance_metadata = instance_metadata.get('items', [])
      instance_keys = set([entry['key'] for entry in instance_metadata])

      if ('sshKeys' in instance_keys and 'sshKeys' not in new_keys
          and 'sshKeys' not in project_keys):
        raise gcutil_errors.CommandError(
            'Discarding update that would have erased instance sshKeys.'
            '\n\nRe-run with the -f flag to force the update.')

    metadata_resource = {'kind': self._GetResourceApiKind('metadata'),
                         'items': new_metadata,
                         'fingerprint': self._flags.fingerprint}

    set_metadata_request = self.api.instances.setMetadata(
        **self._PrepareRequestArgs(instance_context, body=metadata_resource))
    return set_metadata_request.execute()


class SetTags(OptimisticallyLockedInstanceCommand):
  """Set the tags for a VM instance.

  This method overwrites existing instance tags.

  For example, running:

    gcutil --project=<project-name> setinstancetags my-instance \
      --tags="tag-1" \
      --fingerprint=<original-fingerprint>
    ...
    gcutil --project=<project-name> setinstancetags my-instance \
      --tags="tag-2,tag-3" \
      --fingerprint=<new-fingerprint>

  will result in 'my-instance' having tags 'tag-2' and 'tag-3'.
  """

  def __init__(self, name, flag_values):
    super(SetTags, self).__init__(name, flag_values)

    flags.DEFINE_list('tags',
                      [],
                      '[Required] A set of tags applied to this instance. '
                      'Used for filtering and to configure network firewall '
                      'rules To specify multiple tags, provide them as '
                      'comma-separated entries.',
                      flag_values=flag_values)

  def HandleCommand(self, instance_name):
    """Set instance tags.

    Args:
      instance_name: The name of the instance scoping this request.

    Returns:
      An operation resource.
    """
    self._AutoDetectZone()
    instance_context = self._context_parser.ParseContextOrPrompt('instances',
                                                                 instance_name)

    tag_resource = {'items': sorted(set(self._flags.tags)),
                    'fingerprint': self._flags.fingerprint}
    set_tags_request = self.api.instances.setTags(
        **self._PrepareRequestArgs(instance_context, body=tag_resource))
    return set_tags_request.execute()


class AttachDisk(InstanceCommand):
  """Attach a persistent disk to a VM instance."""

  positional_args = '<instance-name>'

  def __init__(self, name, flag_values):
    super(AttachDisk, self).__init__(name, flag_values)

    flags.DEFINE_multistring(
        'disk',
        '',
        '[Required] The name of a disk to be attached to the '
        'instance. The name may be followed by a '
        'comma-separated list of name=value pairs '
        'specifying options. Legal option names are '
        '\'deviceName\', to specify the disk\'s device '
        'name, and \'mode\', to indicate whether the disk '
        'should be attached READ_WRITE (the default) or '
        'READ_ONLY',
        flag_values=flag_values)

  def Handle(self, instance_name):
    """Attach a persistent disk to the instance.

    Args:
      instance_name: The instance name to attach to.

    Returns:
      An operation resource.
    """
    self._AutoDetectZone()
    instance_context = self._context_parser.ParseContextOrPrompt('instances',
                                                                 instance_name)

    disks = [self._BuildAttachedDisk(disk) for disk in self._flags.disk]

    attach_requests = []
    for disk in disks:
      attach_requests.append(
          self.api.instances.attachDisk(
              **self._PrepareRequestArgs(
                  instance_context,
                  body=disk)))

    return self.ExecuteRequests(attach_requests)


class DetachDisk(InstanceCommand):
  """Detach a persistent disk from a VM instance."""

  positional_args = '<instance-name>'

  def __init__(self, name, flag_values):
    super(DetachDisk, self).__init__(name, flag_values)

    flags.DEFINE_multistring(
        'device_name',
        '',
        '[Required] The device name of a persistent disk to '
        'detach from the instance. The device name is '
        'specified at instance creation time and may not '
        'be the same as the persistent disk name.',
        flag_values=flag_values)

  def Handle(self, instance_name):
    """Detach a persistent disk from the instance.

    Args:
      instance_name: The instance name to detach from.

    Returns:
      An operation resource.
    """
    self._AutoDetectZone()
    instance_context = self._context_parser.ParseContextOrPrompt('instances',
                                                                 instance_name)

    detach_requests = []
    for device_name in self._flags.device_name:
      detach_requests.append(
          self.api.instances.detachDisk(
              **self._PrepareRequestArgs(
                  instance_context,
                  deviceName=device_name)))

    return self.ExecuteRequests(detach_requests)


def AddCommands():
  """Add all of the instance related commands."""

  appcommands.AddCmd('addinstance', AddInstance)
  appcommands.AddCmd('getinstance', GetInstance)
  appcommands.AddCmd('deleteinstance', DeleteInstance)
  appcommands.AddCmd('listinstances', ListInstances)
  appcommands.AddCmd('addaccessconfig', AddAccessConfig)
  appcommands.AddCmd('deleteaccessconfig', DeleteAccessConfig)
  appcommands.AddCmd('setscheduling', SetScheduling)
  appcommands.AddCmd('ssh', SshToInstance)
  appcommands.AddCmd('push', PushToInstance)
  appcommands.AddCmd('pull', PullFromInstance)
  appcommands.AddCmd('getserialportoutput', GetSerialPortOutput)
  appcommands.AddCmd('setinstancemetadata', SetMetadata)
  appcommands.AddCmd('setinstancetags', SetTags)
  appcommands.AddCmd('attachdisk', AttachDisk)
  appcommands.AddCmd('detachdisk', DetachDisk)
  appcommands.AddCmd('resetinstance', ResetInstance)
