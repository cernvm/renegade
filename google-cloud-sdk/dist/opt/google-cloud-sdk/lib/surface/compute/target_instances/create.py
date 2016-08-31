# Copyright 2014 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Command for creating target instances."""

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.command_lib.compute import flags


class Create(base_classes.BaseAsyncCreator):
  """Create a target instance for handling traffic from a forwarding rule."""

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--description',
        help='An optional, textual description of the target instance.')
    parser.add_argument(
        '--instance',
        required=True,
        help=('The name of the virtual machine instance that will handle the '
              'traffic.'))

    flags.AddZoneFlag(
        parser,
        resource_type='instance',
        operation_type='to create the target instance in')

    parser.add_argument(
        'name',
        help='The name of the target instance.')

  @property
  def service(self):
    return self.compute.targetInstances

  @property
  def method(self):
    return 'Insert'

  @property
  def resource_type(self):
    return 'targetInstances'

  def CreateRequests(self, args):
    instance_ref = self.CreateZonalReference(
        args.instance, args.zone, resource_type='instances')

    target_instance_ref = self.CreateZonalReference(
        args.name, instance_ref.zone,
        resource_type='targetInstances')

    if target_instance_ref.zone != instance_ref.zone:
      raise calliope_exceptions.ToolException(
          'Target instance zone must match the virtual machine instance zone.')

    request = self.messages.ComputeTargetInstancesInsertRequest(
        targetInstance=self.messages.TargetInstance(
            description=args.description,
            name=target_instance_ref.Name(),
            instance=instance_ref.SelfLink(),
        ),
        project=self.project,
        zone=target_instance_ref.zone)

    return [request]


Create.detailed_help = {
    'brief': (
        'Create a target instance for handling traffic from a forwarding rule'),
    'DESCRIPTION': """\
        *{command}* is used to create a target instance for handling
        traffic from one or more forwarding rules. Target instances
        are ideal for traffic that should be managed by a single
        source. For more information on target instances, see
        [](https://cloud.google.com/compute/docs/protocol-forwarding/#targetinstances)
        """,
}
