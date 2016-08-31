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

"""Implementation of gcloud dataflow jobs cancel command.
"""
from apitools.base.py import exceptions

from googlecloudsdk.api_lib.dataflow import job_utils
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from surface import dataflow as commands


class Cancel(base.Command):
  """Cancels all jobs that match the command line arguments.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    job_utils.ArgsForJobRefs(parser, nargs='+')

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: all the arguments that were provided to this command invocation.

    Returns:
      A pair of lists indicating the jobs that were successfully cancelled and
      those that failed to be cancelled.
    """
    for job_ref in job_utils.ExtractJobRefs(self.context, args):
      self._CancelJob(job_ref)
    return None

  def _CancelJob(self, job_ref):
    """Cancels a job.

    Args:
      job_ref: resources.Resource, The reference to the job to cancel.
    """
    apitools_client = self.context[commands.DATAFLOW_APITOOLS_CLIENT_KEY]
    dataflow_messages = self.context[commands.DATAFLOW_MESSAGES_MODULE_KEY]

    request = dataflow_messages.DataflowProjectsJobsUpdateRequest(
        projectId=job_ref.projectId,
        jobId=job_ref.jobId,
        # We don't need to send the full job, because only the state can be
        # updated, and the other fields are ignored.
        job=dataflow_messages.Job(
            requestedState=(dataflow_messages.Job.RequestedStateValueValuesEnum
                            .JOB_STATE_CANCELLED)))

    try:
      apitools_client.projects_jobs.Update(request)
      log.status.Print('Cancelled job [{0}]'.format(job_ref.jobId))
    except exceptions.HttpError as unused_error:
      log.err.Print('Failed to cancel job [{0}]'.format(job_ref.jobId))
