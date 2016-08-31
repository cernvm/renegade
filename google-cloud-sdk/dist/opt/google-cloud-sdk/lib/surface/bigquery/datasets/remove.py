# Copyright 2015 Google Inc. All Rights Reserved.
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

"""Implementation of gcloud bigquery datasets remove.
"""

from apitools.base.py import exceptions as apitools_exceptions

from googlecloudsdk.api_lib.bigquery import bigquery
from googlecloudsdk.api_lib.bigquery import bigquery_client_helper
from googlecloudsdk.api_lib.bigquery import message_conversions
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io
from surface import bigquery as commands


class DatasetsRemove(base.Command):
  """Removes a dataset.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument(
        '--ignore-not-found',
        action='store_true',
        help='Terminate without an error if the specified dataset does not '
        'exist.')
    parser.add_argument(
        '--remove-tables',
        action='store_true',
        help='Remove the dataset even if it contains one or more tables.')
    parser.add_argument('dataset_name', help='The name of the dataset.')

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace, All the arguments that were provided to this
        command invocation.

    Raises:
      ToolException: when user cancels dataset removal.

    Returns:
      Some value that we want to have printed later.
    """
    apitools_client = self.context[commands.APITOOLS_CLIENT_KEY]
    bigquery_messages = self.context[commands.BIGQUERY_MESSAGES_MODULE_KEY]
    resource_parser = self.context[commands.BIGQUERY_REGISTRY_KEY]
    resource = resource_parser.Parse(
        args.dataset_name, collection='bigquery.datasets')
    reference = message_conversions.DatasetResourceToReference(
        bigquery_messages, resource)

    if not args.quiet:
      dataset_exists = bigquery_client_helper.DatasetExists(
          apitools_client, bigquery_messages, reference)
      if dataset_exists:
        removal_confirmed = console_io.PromptContinue(
            message='About to remove dataset {0}.'.format(resource))
        if not removal_confirmed:
          raise exceptions.ToolException('canceled by user')

    request = bigquery_messages.BigqueryDatasetsDeleteRequest(
        projectId=reference.projectId,
        datasetId=reference.datasetId,
        deleteContents=args.remove_tables)
    try:
      apitools_client.datasets.Delete(request)
      log.DeletedResource(resource)
    except apitools_exceptions.HttpError as server_error:
      try:
        raise bigquery.Error.ForHttpError(server_error)
      except bigquery.NotFoundError:
        if args.ignore_not_found:
          log.status.Print('Dataset {0} did not exist.'.format(resource))
        else:
          raise
