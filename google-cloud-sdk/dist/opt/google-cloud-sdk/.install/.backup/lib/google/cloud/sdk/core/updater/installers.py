# Copyright 2013 Google Inc. All Rights Reserved.

"""Implementations of installers for different component types."""

import os
import re
import shutil
import tarfile
import urllib2


from google.cloud.sdk.core.util import files as file_utils


class Error(Exception):
  """Base exception for the installers module."""
  pass


class URLFetchError(Error):
  """Exception for problems fetching via HTTP."""
  pass


class UnsupportedSourceError(Error):
  """An exception when trying to install a component with an unknown source."""
  pass


class ComponentInstaller(object):
  """A class to install Cloud SDK components of different source types."""

  DOWNLOAD_DIR_NAME = '.download'

  def __init__(self, sdk_root, state_directory, snapshot):
    """Initializes an installer for components of different source types.

    Args:
      sdk_root:  str, The path to the root directory of all Cloud SDK files.
      state_directory: str, The path to the directory where the local state is
        stored.
      snapshot: snapshots.ComponentSnapshot, The snapshot that describes the
        component to install.
    """
    self.__sdk_root = sdk_root
    self.__state_directory = state_directory
    self.__download_directory = os.path.join(
        self.__state_directory, ComponentInstaller.DOWNLOAD_DIR_NAME)
    self.__snapshot = snapshot

    for d in [self.__download_directory]:
      if not os.path.isdir(d):
        file_utils.MakeDir(d)

  def Install(self, component_id):
    """Installs the given component for whatever source type it has.

    Args:
      component_id: str, The component id from the snapshot to install.

    Returns:
      list of str, The files that were installed.

    Raises:
      UnsupportedSourceError: If the component data source is of an unknown
        type.
      URLFetchError: If the URL associated with the component data source
        cannot be fetched.
    """
    component = self.__snapshot.ComponentFromId(component_id)
    data = component.data

    if not data:
      # No source data, just a configuration component
      return []

    if data.type == 'tar':
      return self._InstallTar(component)

    raise UnsupportedSourceError(
        'tar is the only supported source format [{datatype}]'.format(
            datatype=self.data.type))

  def _InstallTar(self, component):
    """Installer implementation for a component with source in a .tar.gz.

    Downloads the .tar for the component and extracts it.

    Args:
      component: schemas.Component, The component to install.

    Returns:
      list of str, The files that were installed or [] if nothing was installed.

    Raises:
      ValueError: If the source URL for the tar file is relative, but there is
        no location information associated with the snapshot we are installing
        from.
      URLFetchError: If there is a problem fetching the component's URL.
    """
    url = component.data.source
    if not url:
      # not all components must have real source
      return []

    if not re.search(r'^\w+://', url):
      # This is a relative path, look relative to the snapshot file.
      if not self.__snapshot.url:
        raise ValueError('Cannot install component [{}] from a relative path '
                         'because the base URL of the snapshot is not defined.'
                         .format(component.id))
      url = os.path.dirname(self.__snapshot.url) + '/' + url

    return ComponentInstaller.DownloadAndExtractTar(
        url, self.__download_directory, self.__sdk_root)

  @staticmethod
  def DownloadAndExtractTar(url, download_dir, extract_dir):
    """Download and extract the given tar file.

    Args:
      url: str, The URL to download.
      download_dir: str, The path to put the temporary download file into.
      extract_dir: str, The path to extract the tar into.

    Returns:
      [str], The files that were extracted from the tar file.

    Raises:
      URLFetchError: If there is a problem fetching the given URL.
    """
    for d in [download_dir, extract_dir]:
      if not os.path.exists(d):
        file_utils.MakeDir(d)
    download_file_path = os.path.join(download_dir, os.path.basename(url))
    if os.path.exists(download_file_path):
      os.remove(download_file_path)

    try:
      req = urllib2.urlopen(url)
    except (urllib2.HTTPError, urllib2.URLError) as e:
      raise URLFetchError(e)
    with open(download_file_path, 'wb') as fp:
      shutil.copyfileobj(req, fp)

    with file_utils.Context(tarfile.open(name=download_file_path)) as tar:
      tar.extractall(extract_dir)
      files = [item.name + '/' if item.isdir() else item.name
               for item in tar.getmembers()]

    os.remove(download_file_path)
    return files
