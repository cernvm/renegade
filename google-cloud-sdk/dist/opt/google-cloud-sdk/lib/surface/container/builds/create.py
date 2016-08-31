# Copyright 2016 Google Inc. All Rights Reserved.
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
"""Describe build command."""

import os.path

from apitools.base.py import encoding

from googlecloudsdk.api_lib.cloudbuild import config
from googlecloudsdk.api_lib.cloudbuild import logs as cb_logs
from googlecloudsdk.api_lib.cloudbuild import snapshot
from googlecloudsdk.api_lib.cloudbuild import storage as cb_storage
from googlecloudsdk.api_lib.util import http_error_handler
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions as c_exceptions
from googlecloudsdk.core import apis as core_apis
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.resource import resource_transform
from googlecloudsdk.core.util import times


_ALLOWED_SOURCE_EXT = ['.zip', '.tgz', '.gz']


class Create(base.Command):
  """Create a build using the Google Container Builder service."""

  @staticmethod
  def Args(parser):
    """Register flags for this command.

    Args:
      parser: An argparse.ArgumentParser-like object. It is mocked out in order
          to capture some information, but behaves like an ArgumentParser.
    """
    parser.add_argument(
        'source',
        help='The source directory on local disk or tarball in Google Cloud '
             'Storage or disk to use for this build.',
    )
    parser.add_argument(
        '--gcs-source-staging-dir',
        help='Directory in Google Cloud Storage to stage a copy of the source '
             'used for the build. If the bucket does not exist, it will be '
             'created. If not set, gs://<project id>_cloudbuild/source is '
             'used.',
    )
    parser.add_argument(
        '--gcs-log-dir',
        help='Directory in Google Cloud Storage to hold build logs. If the '
             'bucket does not exist, it will be created. If not set, '
             'gs://<project id>_cloudbuild/logs is used.',
    )
    build_config = parser.add_mutually_exclusive_group(required=True)
    build_config.add_argument(
        '--tag', '-t',
        help='The tag to use with a "docker build" image creation.',
    )
    build_config.add_argument(
        '--config',
        help='The .yaml or .json file to use for build configuration.',
    )
    base.ASYNC_FLAG.AddToParser(parser)

  # TODO(user,b/29048700): Until resolution of this bug, the error message
  # printed by gcloud (for 404s, eg) will not be as useful as it could be.
  @http_error_handler.HandleHttpErrors
  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Returns:
      Some value that we want to have printed later.
    """

    if args.gcs_source_staging_dir is None:
      args.gcs_source_staging_dir = 'gs://{project}_cloudbuild/source'.format(
          project=properties.VALUES.core.project.Get(),
      )
    if args.gcs_log_dir is None:
      args.gcs_log_dir = 'gs://{project}_cloudbuild/logs'.format(
          project=properties.VALUES.core.project.Get(),
      )

    client = core_apis.GetClientInstance('cloudbuild', 'v1')
    messages = core_apis.GetMessagesModule('cloudbuild', 'v1')
    registry = self.context['registry']

    gcs_client = cb_storage.Client(properties.VALUES.core.project.Get())

    # First, create the build request.
    build_timeout = properties.VALUES.container.build_timeout.Get()
    if build_timeout is not None:
      timeout_str = build_timeout + 's'
    else:
      timeout_str = None

    if args.tag:
      build_config = messages.Build(
          images=[args.tag],
          steps=[
              messages.BuildStep(
                  name='gcr.io/cloud-builders/docker',
                  args=['build', '-t', args.tag, '.'],
              ),
          ],
          timeout=timeout_str,
      )
    elif args.config:
      build_config = config.LoadCloudbuildConfig(args.config, messages)

    if build_config.timeout is None:
      build_config.timeout = timeout_str

    suffix = '.tgz'
    if args.source.startswith('gs://') or os.path.isfile(args.source):
      _, suffix = os.path.splitext(args.source)

    # Next, stage the source to Cloud Storage.
    staged_object = '{stamp}_{tag_ish}{suffix}'.format(
        stamp=times.GetTimeStampFromDateTime(times.Now()),
        tag_ish='_'.join(build_config.images or 'null').replace('/', '_'),
        suffix=suffix,
    )
    gcs_source_staging_dir = registry.Parse(
        args.gcs_source_staging_dir, collection='storage.objects')
    gcs_client.CreateBucketIfNotExists(gcs_source_staging_dir.bucket)
    if gcs_source_staging_dir.object:
      staged_object = gcs_source_staging_dir.object + '/' + staged_object

    gcs_source_staging = registry.Create(
        collection='storage.objects',
        bucket=gcs_source_staging_dir.bucket,
        object=staged_object)

    if args.source.startswith('gs://'):
      gcs_source = registry.Parse(
          args.source, collection='storage.objects')
      staged_source_obj = gcs_client.Copy(gcs_source, gcs_source_staging)
      build_config.source = messages.Source(
          storageSource=messages.StorageSource(
              bucket=staged_source_obj.bucket,
              object=staged_source_obj.name,
              generation=staged_source_obj.generation,
          ))
    else:
      if not os.path.exists(args.source):
        raise c_exceptions.BadFileException(
            'could not find source [{src}]'.format(src=args.source))
      if os.path.isdir(args.source):
        source_snapshot = snapshot.Snapshot(args.source)
        size_str = resource_transform.TransformSize(
            source_snapshot.uncompressed_size)
        log.status.write(
            'Creating temporary tarball archive of {num_files} file(s)'
            ' totalling {size} before compression.\n'.format(
                num_files=len(source_snapshot.files),
                size=size_str))
        staged_source_obj = source_snapshot.CopyTarballToGCS(
            gcs_client, gcs_source_staging)
        build_config.source = messages.Source(
            storageSource=messages.StorageSource(
                bucket=staged_source_obj.bucket,
                object=staged_source_obj.name,
                generation=staged_source_obj.generation,
            ))
      elif os.path.isfile(args.source):
        unused_root, ext = os.path.splitext(args.source)
        if ext not in _ALLOWED_SOURCE_EXT:
          raise c_exceptions.BadFileException(
              'Local file [{src}] is none of '+_ALLOWED_SOURCE_EXT.join(', '))
        log.status.write(
            'Uploading local file [{src}] to '
            '[gs://{bucket}/{object}]\n'.format(
                src=args.source,
                bucket=gcs_source_staging.bucket,
                object=gcs_source_staging.object,
            ))
        staged_source_obj = gcs_client.Upload(args.source, gcs_source_staging)
        build_config.source = messages.Source(
            storageSource=messages.StorageSource(
                bucket=staged_source_obj.bucket,
                object=staged_source_obj.name,
                generation=staged_source_obj.generation,
            ))

    gcs_log_dir = registry.Parse(
        args.gcs_log_dir, collection='storage.objects')

    if gcs_log_dir.bucket != gcs_source_staging.bucket:
      # Create the logs bucket if it does not yet exist.
      gcs_client.CreateBucketIfNotExists(gcs_log_dir.bucket)
    build_config.logsBucket = 'gs://'+gcs_log_dir.bucket+'/'+gcs_log_dir.object

    log.debug('creating build: '+repr(build_config))

    # Start the build.
    op = client.projects_builds.Create(
        messages.CloudbuildProjectsBuildsCreateRequest(
            build=build_config,
            projectId=properties.VALUES.core.project.Get()))
    json = encoding.MessageToJson(op.metadata)
    build = encoding.JsonToMessage(messages.BuildOperationMetadata, json).build

    build_ref = registry.Create(
        collection='cloudbuild.projects.builds',
        projectId=build.projectId,
        id=build.id)

    log.CreatedResource(build_ref)
    if build.logUrl:
      log.status.write('Logs are permanently available at [{log_url}]\n'.format(
          log_url=build.logUrl))
    else:
      log.status.write('Logs are available in the Cloud Console.\n')

    # If the command is run --async, we just print out a reference to the build.
    if args.async:
      return build

    # Otherwise, logs are streamed from GCS.
    return cb_logs.Stream(build_ref, client, messages)

  def Collection(self):
    return 'cloudbuild.projects.builds'

  def Format(self, args):
    return self.ListFormat(args)
