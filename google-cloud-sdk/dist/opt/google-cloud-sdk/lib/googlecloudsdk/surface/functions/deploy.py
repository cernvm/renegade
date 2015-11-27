# Copyright 2015 Google Inc. All Rights Reserved.

"""'functions deploy' command."""
import httplib
import os
import random
import string
from googlecloudsdk.api_lib.functions import cloud_storage as storage
from googlecloudsdk.api_lib.functions import exceptions
from googlecloudsdk.api_lib.functions import operations
from googlecloudsdk.api_lib.functions import util
from googlecloudsdk.calliope import base
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import archive
from googlecloudsdk.core.util import files as file_utils
from googlecloudsdk.third_party.apitools.base import py as apitools_base


class Deploy(base.Command):
  """Creates a new function or updates an existing one."""

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument(
        'name', help='Intended name of the new function.',
        type=util.ValidateFunctionNameOrRaise)
    parser.add_argument(
        '--source',
        help=('Path to directory with source code, either local or in Cloud '
              'Source Repositories. If the code is being deployed from Cloud '
              'Source Repositories, this parameter is required and also you '
              'have to specify the parameter --source-url. If the code is in '
              'a local directory, this parameter is optional and defaults to '
              'the current directory. In this case you have to specify the '
              '--bucket parameter.'))
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument(
        '--bucket',
        help=('Name of Google Cloud Storage bucket in which source code will '
              'be stored. Required if a function is deployed from a local '
              'directory.'),
        type=util.ValidateAndStandarizeBucketUriOrRaise)
    source_group.add_argument(
        '--source-url',
        help=('The Url of a remote repository that holds the function being '
              'deployed. Must be of the form: '
              'https://source.developers.google.com/p/{project_id}/'
              'r/{repo_name}/, where you should substitute your data for '
              'values inside the curly brackets. '
              'One of the parameters --source-revision, --source-branch, '
              'or --source-tag can be given to specify the version in the '
              'repository. If none of them are provided, the last revision '
              'from the master branch is used. If this parameter is given, '
              'the parameter --source is required and describes the path '
              'inside the repository.'))
    source_version_group = parser.add_mutually_exclusive_group()
    source_version_group.add_argument(
        '--source-revision',
        help=('The revision ID (for instance, git tag) that will be used to '
              'get the source code of the function. Can be specified only '
              'together with --source-url parameter.'))
    source_version_group.add_argument(
        '--source-branch',
        help=('The branch that will be used to get the source code of the '
              'function.  The most recent revision on this branch will be '
              'used. Can be specified only together with --source-url '
              'parameter.'))
    source_version_group.add_argument(
        '--source-tag',
        help=('The revision tag for the source that will be used as the source '
              'code of the function. Can be specified only together with '
              '--source-url parameter.'))
    parser.add_argument(
        '--entry-point',
        help=('The name of the function (as defined in source code) that will '
              'be executed.'),
        type=util.ValidateEntryPointNameOrRaise)
    trigger_group = parser.add_mutually_exclusive_group(required=True)
    trigger_group.add_argument(
        '--trigger-topic',
        help=('Name of Pub/Sub topic. Every message published in this topic '
              'will trigger function execution with message contents passed as '
              'input data.'),
        type=util.ValidateAndStandarizePubsubTopicNameOrRaise)
    trigger_group.add_argument(
        '--trigger-gs-uri',
        help=('Google Cloud Storage bucket name. Every change in files in this '
              'bucket will trigger function execution.'),
        type=util.ValidateAndStandarizeBucketUriOrRaise)

  @util.CatchHTTPErrorRaiseHTTPException
  def _GetExistingFunction(self, name):
    client = self.context['functions_client']
    messages = self.context['functions_messages']
    try:
      # TODO(belchatek): Use resources.py here after b/21908671 is fixed.
      # We got response for a get request so a function exists.
      return client.projects_regions_functions.Get(
          messages.CloudfunctionsProjectsRegionsFunctionsGetRequest(name=name))
    except apitools_base.HttpError as error:
      if error.status_code == httplib.NOT_FOUND:
        # The function has not been found.
        return None
      raise

  def _GenerateFileName(self, args):
    sufix = ''.join(random.choice(string.ascii_lowercase) for _ in range(12))
    return '{0}-{1}-{2}'.format(args.region, args.name, sufix)

  def _UploadFile(self, source, target):
    return storage.Upload(source, target)

  def _CreateZipFile(self, tmp_dir, args):
    zip_file_name = os.path.join(tmp_dir, 'fun.zip')
    archive.MakeZipFromDir(zip_file_name, args.source)
    return zip_file_name

  def _PrepareFunctionWithoutSources(self, name, args):
    """Creates a function object without filling in the sources properties.

    Args:
      name: funciton name
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Returns:
      The specified function with its description and configured filter.
    """
    messages = self.context['functions_messages']
    trigger = messages.FunctionTrigger()
    if args.trigger_topic:
      trigger.pubsubTopic = args.trigger_topic
    if args.trigger_gs_uri:
      trigger.gsUri = args.trigger_gs_uri
    function = messages.HostedFunction()
    function.name = name
    if args.entry_point:
      function.entryPoint = args.entry_point
    function.triggers = [trigger]
    return function

  def _DeployFunction(self, name, location, args, deploy_method):
    function = self._PrepareFunctionWithoutSources(name, args)
    if args.source_url:
      messages = self.context['functions_messages']
      # At most one of [args.source_tag, args.source_branch,
      # args.source_revision] is set: enforced by the arg parser.
      function.sourceRepository = messages.SourceRepository(
          tag=args.source_tag, branch=args.source_branch,
          revision=args.source_revision, repositoryUrl=args.source_url,
          sourcePath=args.source)
    else:
      function.gcsUrl = self._PrepareSourcesOnGcs(args)
    return deploy_method(location, function)

  def _PrepareSourcesOnGcs(self, args):
    remote_zip_file = self._GenerateFileName(args)
    # args.bucket is not None: Enforced in _CheckArgs().
    gcs_url = storage.BuildRemoteDestination(args.bucket, remote_zip_file)
    with file_utils.TemporaryDirectory() as tmp_dir:
      zip_file = self._CreateZipFile(tmp_dir, args)
      if self._UploadFile(zip_file, gcs_url) != 0:
        raise exceptions.FunctionsError('Function upload failed.')
    return gcs_url

  @util.CatchHTTPErrorRaiseHTTPException
  def _CreateFunction(self, location, function):
    client = self.context['functions_client']
    messages = self.context['functions_messages']
    # TODO(belchatek): Use resources.py here after b/21908671 is fixed.
    op = client.projects_regions_functions.Create(
        messages.CloudfunctionsProjectsRegionsFunctionsCreateRequest(
            location=location, hostedFunction=function))
    operations.Wait(op, messages, client)
    return self._GetExistingFunction(function.name)

  @util.CatchHTTPErrorRaiseHTTPException
  def _UpdateFunction(self, unused_location, function):
    client = self.context['functions_client']
    messages = self.context['functions_messages']
    # TODO(belchatek): Use resources.py here after b/21908671 is fixed.
    op = client.projects_regions_functions.Update(function)
    operations.Wait(op, messages, client)
    return self._GetExistingFunction(function.name)

  def _CheckArgs(self, args):
    # This function should raise ArgumentParsingError, but:
    # 1. ArgumentParsingError requires the  argument returned from add_argument)
    #    and Args() method is static. So there is no elegant way to save it
    #    to be reused here.
    # 2. _CheckArgs() is invoked from Run() and ArgumentParsingError thrown
    #    from Run are not caught.
    if args.source_url is None:
      if args.source_revision is not None:
        raise exceptions.FunctionsError(
            'argument --source-revision: can be given only if argument '
            '--source-url is provided')
      if args.source_branch is not None:
        raise exceptions.FunctionsError(
            'argument --source-branch: can be given only if argument '
            '--source-url is provided')
      if args.source_tag is not None:
        raise exceptions.FunctionsError(
            'argument --source-tag: can be given only if argument '
            '--source-url is provided')
      if args.source is None:
        args.source = '.'
      util.ValidateDirectoryExistsOrRaiseFunctionError(args.source)
    else:
      if args.source is None:
        raise exceptions.FunctionsError(
            'argument --source: required when argument --source-url is '
            'provided')
  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Returns:
      The specified function with its description and configured filter.

    Raises:
      FunctionsError if command line parameters are not valid.
    """
    # TODO(b/24723761): This should be invoked as a hook method after arguments
    # are parsed, but unfortunately gcloud framework doesn't support such a
    # hook.
    self._CheckArgs(args)

    project = properties.VALUES.core.project.Get(required=True)
    location = 'projects/{0}/regions/{1}'.format(project, args.region)
    name = 'projects/{0}/regions/{1}/functions/{2}'.format(
        project, args.region, args.name)

    function = self._GetExistingFunction(name)
    if function is None:
      return self._DeployFunction(name, location, args, self._CreateFunction)
    else:
      return self._DeployFunction(name, location, args, self._UpdateFunction)

  def Display(self, unused_args, result):
    """This method is called to print the result of the Run() method.

    Args:
      unused_args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    self.format(result)
