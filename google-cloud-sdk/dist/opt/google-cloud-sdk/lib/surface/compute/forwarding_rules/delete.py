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
"""Command for deleting forwarding rules."""

from googlecloudsdk.api_lib.compute import forwarding_rules_utils
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.command_lib.compute.forwarding_rules import flags


class Delete(forwarding_rules_utils.ForwardingRulesMutator):
  """Delete forwarding rules."""

  @staticmethod
  def Args(parser):
    flags.AddCommonFlags(parser)

    parser.add_argument(
        'names',
        metavar='NAME',
        nargs='+',
        completion_resource='compute.forwarding-rules',
        help='The names of the forwarding rules to delete.')

  @property
  def method(self):
    return 'Delete'

  def CreateGlobalRequests(self, args):
    """Create a globally scoped request."""

    # TODO(user): In the future we should support concurrently deleting both
    # region and global forwarding rules
    forwarding_rule_refs = self.CreateGlobalReferences(
        args.names, resource_type='globalForwardingRules')
    utils.PromptForDeletion(forwarding_rule_refs)
    requests = []
    for forwarding_rule_ref in forwarding_rule_refs:
      request = self.messages.ComputeGlobalForwardingRulesDeleteRequest(
          forwardingRule=forwarding_rule_ref.Name(),
          project=self.project,
      )
      requests.append(request)

    return requests

  def CreateRegionalRequests(self, args):
    """Create a regionally scoped request."""

    forwarding_rule_refs = (
        self.CreateRegionalReferences(
            args.names, args.region, flag_names=['--region', '--global']))
    utils.PromptForDeletion(forwarding_rule_refs, scope_name='region')
    requests = []
    for forwarding_rule_ref in forwarding_rule_refs:
      request = self.messages.ComputeForwardingRulesDeleteRequest(
          forwardingRule=forwarding_rule_ref.Name(),
          project=self.project,
          region=forwarding_rule_ref.region,
      )
      requests.append(request)

    return requests


Delete.detailed_help = {
    'brief': 'Delete forwarding rules',
    'DESCRIPTION': """\
        *{command}* deletes one or more Google Compute Engine forwarding rules.
        """,
}
