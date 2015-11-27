# Copyright 2015 Google Inc. All Rights Reserved.
"""Helpers for writing commands interacting with jobs and their IDs.
"""

from googlecloudsdk.api_lib.dataflow import dataflow_util
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.surface import dataflow as commands
from googlecloudsdk.third_party.apitools.base import py as apitools_base


class _JobViewSummary(object):

  def JobsGetRequest(self, context):
    return (context[commands.DATAFLOW_MESSAGES_MODULE_KEY]
            .DataflowProjectsJobsGetRequest
            .ViewValueValuesEnum.JOB_VIEW_SUMMARY)

  def JobsListRequest(self, context):
    return (context[commands.DATAFLOW_MESSAGES_MODULE_KEY]
            .DataflowProjectsJobsListRequest
            .ViewValueValuesEnum.JOB_VIEW_SUMMARY)


class _JobViewAll(object):

  def JobsGetRequest(self, context):
    return (context[commands.DATAFLOW_MESSAGES_MODULE_KEY]
            .DataflowProjectsJobsGetRequest
            .ViewValueValuesEnum.JOB_VIEW_ALL)

  def JobsListRequest(self, context):
    return (context[commands.DATAFLOW_MESSAGES_MODULE_KEY]
            .DataflowProjectsJobsListRequest
            .ViewValueValuesEnum.JOB_VIEW_ALL)


JOB_VIEW_SUMMARY = _JobViewSummary()
JOB_VIEW_ALL = _JobViewAll()


def GetJob(context, job_ref, view=JOB_VIEW_SUMMARY, required=True):
  """Retrieve a specific view of a job.

  Args:
    context: Command context.
    job_ref: To retrieve.
    view: The job view to retrieve. Should be JOB_VIEW_SUMMARY or JOB_VIEW_ALL.
    required: If true and the Job doesn't exist, will raise an exception.

  Returns:
    The requested Job message.
  """
  apitools_client = context[commands.DATAFLOW_APITOOLS_CLIENT_KEY]

  request = job_ref.Request()
  request.view = view.JobsGetRequest(context)

  try:
    return apitools_client.projects_jobs.Get(request)
  except apitools_base.HttpError as error:
    if error.status_code == 404:
      msg = 'No job with ID [{0}] in project [{1}]'.format(
          job_ref.jobId, job_ref.projectId)

      if required:
        raise calliope_exceptions.ToolException(msg)
      else:
        # Turn `Not Found' exceptions into None.
        log.status.Print(msg)
        return None
    raise calliope_exceptions.HttpException(
        'Failed to get job with ID [{0}] in project [{1}]: {2}'.format(
            job_ref.jobId, job_ref.projectId,
            dataflow_util.GetErrorMessage(error)))


def GetJobForArgs(context, args, view=JOB_VIEW_ALL, required=True):
  """Retrieve a job for the JobRef specified in the arguments.

  Args:
    context: Command context.
    args: Arguments including the job to retrieve.
    view: The job view to retrieve. Should be JOB_VIEW_SUMMARY or JOB_VIEW_ALL.
        If not set will default to JOB_VIEW_ALL.
    required: If true and the Job doesn't exist, will raise an exception.

  Returns:
    The requested Job message.
  """
  job_ref = ExtractJobRef(context, args)
  return GetJob(context, job_ref, view=view, required=required)


def ArgsForJobRef(parser):
  """Register flags for specifying a single Job ID.

  Args:
    parser: The argparse.ArgParser to configure with job-filtering arguments.
  """
  parser.add_argument('job', metavar='JOB_ID', help='The job ID to operate on.')


def ArgsForJobRefs(parser, **kwargs):
  """Register flags for specifying jobs using positional job IDs.

  Args:
    parser: The argparse.ArgParser to configure with job ID arguments.
    **kwargs: Extra arguments to pass to the add_argument call.
  """
  parser.add_argument(
      'jobs', metavar='JOB', help='The jobs to operate on.', **kwargs)


def ExtractJobRef(context, args):
  """Extract the Job Ref for a command. Used with ArgsForJobRef.

  Args:
    context: The command context.
    args: The parsed arguments that were provided to this invocation.
  Returns:
    A Job resource.
  """
  resources = context[commands.DATAFLOW_REGISTRY_KEY]
  collection = 'dataflow.projects.jobs'
  return resources.Parse(args.job, collection=collection)


def ExtractJobRefs(context, args):
  """Extract the Job Refs for a command. Used with ArgsForJobRefs.

  Args:
    context: The command context.
    args: The parsed arguments that were provided to this invocation.
  Returns:
    A list of job resources.
  """
  resources = context[commands.DATAFLOW_REGISTRY_KEY]

  return [resources.Parse(job, collection='dataflow.projects.jobs')
          for job in args.jobs]
