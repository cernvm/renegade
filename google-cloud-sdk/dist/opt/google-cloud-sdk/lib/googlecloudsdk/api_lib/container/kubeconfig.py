# Copyright 2015 Google Inc. All Rights Reserved.

"""Utilities for loading and parsing kubeconfig."""
import os

from googlecloudsdk.core import log
from googlecloudsdk.core.util import files as file_utils

import yaml


class Error(Exception):
  """Class for errors raised by kubeconfig utilities."""


# TODO(jeffml): marshal yaml directly into a type with a
# matching structure.
class Kubeconfig(object):
  """Interface for interacting with a kubeconfig file."""

  def __init__(self, raw_data, filename):
    self._filename = filename
    self._data = raw_data
    self.clusters = {}
    self.users = {}
    self.contexts = {}
    for cluster in self._data['clusters']:
      self.clusters[cluster['name']] = cluster
    for user in self._data['users']:
      self.users[user['name']] = user
    for context in self._data['contexts']:
      self.contexts[context['name']] = context

  @property
  def current_context(self):
    return self._data['current-context']

  def Clear(self, key):
    self.contexts.pop(key, None)
    self.clusters.pop(key, None)
    self.users.pop(key, None)
    if self._data.get('current-context') == key:
      self._data['current-context'] = ''

  def SaveToFile(self):
    self._data['clusters'] = self.clusters.values()
    self._data['users'] = self.users.values()
    self._data['contexts'] = self.contexts.values()
    # We use os.open here to explicitly set file mode 0600.
    # the flags passed should mimic behavior of open(self._filename, 'w'),
    # which does write with truncate and creates file if not existing.
    fd = os.open(self._filename, os.O_WRONLY | os.O_TRUNC | os.O_CREAT, 0o600)
    with os.fdopen(fd, 'w') as fp:
      yaml.safe_dump(self._data, fp, default_flow_style=False)

  def SetCurrentContext(self, context):
    self._data['current-context'] = context

  @classmethod
  def _Validate(cls, data):
    try:
      if not data:
        raise Error('empty file')
      for key in ('clusters', 'users', 'contexts'):
        if not isinstance(data[key], list):
          raise Error(
              'invalid type for %s: %s', data[key], type(data[key]))
    except KeyError as error:
      raise Error('expected key %s not found', error)

  @classmethod
  def LoadFromFile(cls, filename):
    try:
      with open(filename, 'r') as fp:
        data = yaml.load(fp)
        cls._Validate(data)
        return cls(data, filename)
    except yaml.YAMLError as error:
      raise Error('unable to load kubeconfig for %s: %s', filename, error)

  @classmethod
  def LoadOrCreate(cls, filename):
    try:
      return cls.LoadFromFile(filename)
    except (Error, IOError) as error:
      log.debug('unable to load default kubeconfig: %s; recreating %s',
                error, filename)
      file_utils.MakeDir(os.path.dirname(filename))
      kubeconfig = cls(EmptyKubeconfig(), filename)
      kubeconfig.SaveToFile()
      return kubeconfig

  @classmethod
  def Default(cls):
    return cls.LoadOrCreate(Kubeconfig.DefaultPath())

  @staticmethod
  def DefaultPath():
    if os.environ.get('KUBECONFIG'):
      return os.environ['KUBECONFIG']
    return os.path.join(os.path.expanduser('~/'), '.kube/config')


def Cluster(name, server, ca_path=None, ca_data=None):
  """Generate and return a cluster kubeconfig object."""
  cluster = {
      'server': server,
  }
  if ca_path and ca_data:
    raise Error('cannot specify both ca_path and ca_data')
  if ca_path:
    cluster['certificate-authority'] = ca_path
  elif ca_data:
    cluster['certificate-authority-data'] = ca_data
  else:
    cluster['insecure-skip-tls-verify'] = True
  return {
      'name': name,
      'cluster': cluster
  }


def User(name, token=None, username=None, password=None,
         cert_path=None, cert_data=None, key_path=None, key_data=None):
  """Generate and return a user kubeconfig object.

  Args:
    name: str, nickname for this user entry.
    token: str, bearer token.
    username: str, basic auth user.
    password: str, basic auth password.
    cert_path: str, path to client certificate file.
    cert_data: str, base64 encoded client certificate data.
    key_path: str, path to client key file.
    key_data: str, base64 encoded client key data.
  Returns:
    dict, valid kubeconfig user entry.

  Raises:
    Error: if no auth info is provided (token or username AND password)
  """
  if not token and (not username or not password):
    raise Error('either token or username,password must be provided')
  user = {}
  if token:
    user['token'] = token
  else:
    user['username'] = username
    user['password'] = password

  if cert_path and cert_data:
    raise Error('cannot specify both cert_path and cert_data')
  if cert_path:
    user['client-certificate'] = cert_path
  elif cert_data:
    user['client-certificate-data'] = cert_data

  if key_path and key_data:
    raise Error('cannot specify both key_path and key_data')
  if key_path:
    user['client-key'] = key_path
  elif key_data:
    user['client-key-data'] = key_data

  return {
      'name': name,
      'user': user
  }


def Context(name, cluster, user):
  """Generate and return a context kubeconfig object."""
  return {
      'name': name,
      'context': {
          'cluster': cluster,
          'user': user,
      },
  }


def EmptyKubeconfig():
  return {
      'apiVersion': 'v1',
      'contexts': [],
      'clusters': [],
      'current-context': '',
      'kind': 'Config',
      'preferences': {},
      'users': [],
  }

