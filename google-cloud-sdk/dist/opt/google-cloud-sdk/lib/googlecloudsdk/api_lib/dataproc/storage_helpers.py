# Copyright 2015 Google Inc. All Rights Reserved.

"""Helpers for accessing GCS.

Bulk object uploads and downloads use methods that shell out to gsutil.
Lightweight metadata / streaming operations use the StorageClient class.
"""

import os
import sys
import urlparse

from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import cli
from googlecloudsdk.core import config
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core import log
from googlecloudsdk.core.util import platforms
from googlecloudsdk.third_party.apis.storage.v1 import storage_v1_client
from googlecloudsdk.third_party.apis.storage.v1 import storage_v1_messages as messages
from googlecloudsdk.third_party.apitools.base import py as apitools_base


# URI scheme for GCS.
STORAGE_SCHEME = 'gs'

# Timeout for individual socket connections. Matches gsutil.
HTTP_TIMEOUT = 60

# Fix urlparse for storage paths.
urlparse.uses_relative.append(STORAGE_SCHEME)
urlparse.uses_netloc.append(STORAGE_SCHEME)


def _GetGsutilPath():
  """Determines the path to the gsutil binary."""
  sdk_bin_path = config.Paths().sdk_bin_path
  if not sdk_bin_path:
    # TODO(pclay): check if gsutil component is installed and offer user
    # to install it if it is not.
    raise exceptions.ToolException(('A SDK root could not be found. Please '
                                    'check your installation.'))

  gsutil_path = os.path.join(sdk_bin_path, 'gsutil')
  if platforms.OperatingSystem.Current() == platforms.OperatingSystem.WINDOWS:
    gsutil_path += '.cmd'
  return gsutil_path


def _RunGsutilCommand(command_name, command_args, run_concurrent=False):
  """Runs the specified gsutil command and returns the command's exit code.

  Args:
    command_name: The gsutil command to run.
    command_args: List of arguments to pass to the command.
    run_concurrent: Whether concurrent uploads should be enabled while running
      the command.

  Returns:
    The exit code of the call to the gsutil command.
  """
  gsutil_path = _GetGsutilPath()

  gsutil_args = []
  if run_concurrent:
    gsutil_args += ['-m']
  gsutil_args += [command_name]
  gsutil_args += command_args
  env = None

  gsutil_cmd = execution_utils.ArgsForBinaryTool(gsutil_path, *gsutil_args)
  log.debug('Running command: [{args}], Env: [{env}]'.format(
      args=' '.join(gsutil_cmd),
      env=env))
  return execution_utils.Exec(gsutil_cmd, no_exit=True, env=env)


def Upload(files, destination):
  """Upload a list of local files to GCS.

  Args:
    files: The list of local files to upload.
    destination: A GCS "directory" to copy the files into.
  """
  args = files
  args += [destination]
  exit_code = _RunGsutilCommand('cp', args)
  if exit_code != 0:
    raise exceptions.ToolException(
        "Failed to upload files {0} to '{1}' using gsutil.".format(
            files, destination))


def GetObjectRef(path):
  """Build an Object proto message from a GCS path.

  Args:
    path: The GCS path of the form "gs://<bucket>/<object>"

  Returns:
    A proto message of the parsed objects

  Raises:
    ToolException: If there is a parsing issue or the bucket is unspecified.
  """
  # TODO(pclay): Let resources.Parse take GCS paths.
  url = urlparse.urlparse(path)
  if url.scheme != STORAGE_SCHEME:
    log.warn(path)
    log.warn(url)
    raise exceptions.ToolException(
        'Invalid scheme [{0}] for a GCS path [{1}].'.format(url.scheme, path))
  gcs_bucket = url.netloc
  gcs_object = url.path.lstrip('/')
  if not gcs_bucket:
    raise exceptions.ToolException(
        'Missing bucket in GCS path [{0}].'.format(path))
  if not gcs_object:
    raise exceptions.ToolException(
        'Missing object in GCS path [{0}].'.format(path))
  return messages.Object(bucket=gcs_bucket, name=gcs_object)


class StorageClient(object):
  """Micro-client for accessing GCS."""

  # TODO(pclay): Add application-id.

  def __init__(self, http=None):
    if not http:
      http = cli.Http(timeout=HTTP_TIMEOUT)
    self.client = storage_v1_client.StorageV1(
        http=http,
        get_credentials=False)

  def _GetObject(self, object_ref, download=None):
    request = messages.StorageObjectsGetRequest(
        bucket=object_ref.bucket, object=object_ref.name)
    try:
      return self.client.objects.Get(request=request, download=download)
    except apitools_base.HttpError as error:
      # TODO(pclay): Clean up error handling. Handle 403s.
      if error.status_code == 404:
        return None
      raise error

  def GetObject(self, object_ref):
    """Get the object metadata of a GCS object.

    Args:
      object_ref: A proto message of the object to fetch. Only the bucket and
        name need be set.

    Raises:
      HttpError:
        If the responses status is not 2xx or 404.

    Returns:
      The object if it exists otherwise None.
    """
    return self._GetObject(object_ref)

  def BuildObjectStream(self, stream, object_ref):
    """Build an apitools Download from a stream and a GCS object reference.

    Note: This will always succeed, but HttpErrors with downloading will be
      raised when the download's methods are called.

    Args:
      stream: An Stream-like object that implements write(<string>) to write
        into.
      object_ref: A proto message of the object to fetch. Only the bucket and
        name need be set.

    Returns:
      The download.
    """
    download = apitools_base.Download.FromStream(stream, auto_transfer=False)
    self._GetObject(object_ref, download=download)
    return download


class StorageObjectSeriesStream(object):
  """I/O Stream-like class for communicating via a sequence of GCS objects."""

  def __init__(self, path, storage_client=None):
    """Construct a StorageObjectSeriesStream for a specific gcs path.

    Args:
      path: A GCS object prefix which will be the base of the objects used to
          communicate across the channel.
      storage_client: a StorageClient for accessing GCS.

    Returns:
      The constructed stream.
    """
    self._base_path = path
    self._gcs = storage_client or StorageClient()
    self._open = True

    # Index of current object in series.
    self._current_object_index = 0

    # Current position in bytes in the current file.
    self._current_object_pos = 0

  @property
  def open(self):
    """Whether the stream is open."""
    return self._open

  def Close(self):
    """Close the stream."""
    self._open = False

  def _AssertOpen(self):
    if not self.open:
      raise ValueError('I/O operation on closed stream.')

  def _GetObject(self, i):
    """Get the ith object in the series."""
    path = '{0}.{1:09d}'.format(self._base_path, i)
    return self._gcs.GetObject(GetObjectRef(path))

  def ReadIntoWritable(self, writable, n=sys.maxsize):
    """Read from this stream into a writable.

    Reads at most n bytes, or until it sees there is not a next object in the
    series. This will block for the duration of each object's download,
    and possibly indefinitely if new objects are being added to the channel
    frequently enough.

    Args:
      writable: The stream-like object that implements write(<string>) to
          write into.
      n: A maximum number of bytes to read. Defaults to sys.maxsize
        (usually ~4 GB).

    Raises:
      ValueError: If the stream is closed or objects in the series are
        detected to shrink.

    Returns:
      The number of bytes read.
    """
    self._AssertOpen()
    bytes_read = 0
    object_info = None
    max_bytes_to_read = n
    while bytes_read < max_bytes_to_read:
      # Cache away next object first.
      next_object_info = self._GetObject(self._current_object_index + 1)

      # If next object exists always fetch current object to get final size.
      if not object_info or next_object_info:
        object_info = self._GetObject(self._current_object_index)
        if not object_info:
          # Nothing to read yet.
          break

      new_bytes_available = object_info.size - self._current_object_pos

      if new_bytes_available < 0:
        raise ValueError('Object [{0}] shrunk.'.format(object_info.name))

      if object_info.size == 0:
        # There are no more objects to read
        self.Close()
        break

      bytes_left_to_read = max_bytes_to_read - bytes_read
      new_bytes_to_read = min(bytes_left_to_read, new_bytes_available)

      if new_bytes_to_read > 0:
        # Download range.
        download = self._gcs.BuildObjectStream(writable, object_info)
        download.GetRange(
            self._current_object_pos,
            self._current_object_pos + new_bytes_to_read - 1)
        self._current_object_pos += new_bytes_to_read
        bytes_read += new_bytes_to_read

      # Correct since we checked for next object before getting current
      # object's size.
      object_finished = (
          next_object_info and self._current_object_pos == object_info.size)

      if object_finished:
        object_info = next_object_info
        self._current_object_index += 1
        self._current_object_pos = 0
        continue
      else:
        # That is all there is to read at this time.
        break

    return bytes_read
