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
"""Command for creating target pools."""

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.command_lib.compute import flags
from googlecloudsdk.core import apis as core_apis


class Create(base_classes.BaseAsyncCreator):
  """Define a load-balanced pool of virtual machine instances.

  *{command}* is used to create a target pool. A target pool resource
  defines a group of instances that can receive incoming traffic
  from forwarding rules. When a forwarding rule directs traffic to a
  target pool, Google Compute Engine picks an instance from the
  target pool based on a hash of the source and
  destination IP addresses and ports. For more
  information on load balancing, see
  [](https://cloud.google.com/compute/docs/load-balancing-and-autoscaling/)

  To add instances to a target pool, use 'gcloud compute
  target-pools add-instances'.
  """

  @staticmethod
  def Args(parser):
    backup_pool = parser.add_argument(
        '--backup-pool',
        help='Defines the fallback pool for the target pool.')
    backup_pool.detailed_help = """\
        Together with ``--failover-ratio'', this flag defines the fallback
        behavior of the target pool (primary pool) to be created by this
        command. If the ratio of the healthy instances in the primary pool
        is at or below the specified ``--failover-ratio value'', then traffic
        arriving at the load-balanced IP address will be directed to the
        backup pool. If this flag is provided, then ``--failover-ratio'' is
        required.
        """

    parser.add_argument(
        '--description',
        help='An optional description of this target pool.')

    failover_ratio = parser.add_argument(
        '--failover-ratio',
        type=float,
        help=('The ratio of healthy instances below which the backup pool '
              'will be used.'))
    failover_ratio.detailed_help = """\
        Together with ``--backup-pool'', defines the fallback behavior of the
        target pool (primary pool) to be created by this command. If the
        ratio of the healthy instances in the primary pool is at or below this
        number, traffic arriving at the load-balanced IP address will be
        directed to the backup pool. For example, if 0.4 is chosen as the
        failover ratio, then traffic will fail over to the backup pool if
        more than 40% of the instances become unhealthy.
        If not set, the traffic will be directed the
        instances in this pool in the ``force'' mode, where traffic will be
        spread to the healthy instances with the best effort, or to all
        instances when no instance is healthy.
        If this flag is provided, then ``--backup-pool'' is required.
        """

    health_check = parser.add_argument(
        '--health-check',
        help=('Specifies HttpHealthCheck to determine the health of instances '
              'in the pool.'),
        metavar='HEALTH_CHECK')
    health_check.detailed_help = """\
        Specifies an HTTP health check resource to use to determine the health
        of instances in this pool. If no health check is specified, traffic will
        be sent to all instances in this target pool as if the instances
        were healthy, but the health status of this pool will appear as
        unhealthy as a warning that this target pool does not have a health
        check.
        """

    flags.AddRegionFlag(
        parser,
        resource_type='target pool',
        operation_type='create')

    messages = core_apis.GetMessagesModule('compute', 'v1')
    session_affinities = sorted(messages.TargetPool
                                .SessionAffinityValueValuesEnum
                                .to_dict().keys())

    session_affinity = parser.add_argument(
        '--session-affinity',
        choices=session_affinities,
        type=lambda x: x.upper(),
        default='NONE',
        help='The session affinity option for the target pool.')
    session_affinity.detailed_help = """\
        Specifies the session affinity option for the connection.
        If ``NONE'' is selected, then connections from the same client
        IP address may go to any instance in the target pool.
        If ``CLIENT_IP'' is selected, then connections
        from the same client IP address will go to the same instance
        in the target pool.
        If ``CLIENT_IP_PROTO'' is selected, then connections from the same
        client IP with the same IP protocol will go to the same client pool.
        If not specified, then ``NONE'' is used as a default.
        """

    parser.add_argument(
        'name',
        help='The name of the target pool.')

  @property
  def service(self):
    return self.compute.targetPools

  @property
  def method(self):
    return 'Insert'

  @property
  def resource_type(self):
    return 'targetPools'

  def CreateRequests(self, args):
    """Returns a list of requests necessary for adding a target pool."""
    if ((args.backup_pool and not args.failover_ratio) or
        (args.failover_ratio and not args.backup_pool)):
      raise calliope_exceptions.ToolException(
          'Either both or neither of [--failover-ratio] and [--backup-pool] '
          'must be provided.')

    if args.failover_ratio is not None:
      if args.failover_ratio < 0 or args.failover_ratio > 1:
        raise calliope_exceptions.ToolException(
            '[--failover-ratio] must be a number between 0 and 1, inclusive.')

    if args.health_check:
      health_check = [self.CreateGlobalReference(
          args.health_check, resource_type='httpHealthChecks').SelfLink()]

    else:
      health_check = []

    target_pool_ref = self.CreateRegionalReference(args.name, args.region)

    if args.backup_pool:
      backup_pool_uri = self.CreateRegionalReference(
          args.backup_pool, target_pool_ref.region).SelfLink()
    else:
      backup_pool_uri = None

    request = self.messages.ComputeTargetPoolsInsertRequest(
        targetPool=self.messages.TargetPool(
            backupPool=backup_pool_uri,
            description=args.description,
            failoverRatio=args.failover_ratio,
            healthChecks=health_check,
            name=target_pool_ref.Name(),
            sessionAffinity=(
                self.messages.TargetPool.SessionAffinityValueValuesEnum(
                    args.session_affinity))),
        region=target_pool_ref.region,
        project=self.project)

    return [request]
