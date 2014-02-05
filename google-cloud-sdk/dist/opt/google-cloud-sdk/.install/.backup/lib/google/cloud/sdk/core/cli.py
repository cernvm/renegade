# Copyright 2013 Google Inc. All Rights Reserved.

"""A module to make it easy to set up and run CLIs in the Cloud SDK."""

import logging
import os.path
import subprocess
import sys


import httplib2
import yaml


from google.cloud.sdk import calliope
from google.cloud.sdk.calliope import exceptions
from google.cloud.sdk.core import config
from google.cloud.sdk.core.credentials import store as c_store


__all__ = ['CLI', 'CLIFromConfig', 'ParseConfigFromFile', 'GooglePackageRoot',
           'Credentials', 'Http']


class Error(Exception):
  """Exceptions for the cli module."""


class NoAuthException(Error):
  """An exception to be raised when there is no valid credentials object."""

  def __init__(self):
    auth_command = 'gcloud auth login'
    message = 'No valid credentials. Please run %s.' % auth_command
    super(NoAuthException, self).__init__(message)


class UnexpectedKeysException(Error):
  """An exception to be raised when CLI config files have unrecognized keys."""


class NoHelpFound(Error):
  """Raised when a help file cannot be located."""


def GetHelp(help_dir):
  """Returns a function that can display long help.

  Long help is displayed using the man utility if it's available on
  the user's platform. If man is not available, a plain-text version
  of help is written to standard out.

  Args:
    help_dir: str, The path to the directory containing help documents.

  Returns:
    func([str]), A function that can display help if help_dir exists,
    otherwise None.
  """

  def Help(path):
    """Displays help for the given subcommand.

    This function first attempts to display help using the man utility.
    If man is unavailable, a plain-text version of the help is printed
    to standard out.

    Args:
      path: A path representing the subcommand for which help is being
          requested (e.g., ['my-prog', 'my-subcommand'] if help is being
          requested for "my-prog my-subcommand").

    Raises:
      HelpNotFound: If man is not available and no help exists for the
          given subcommand. Note that if man is available and no help exists,
          error reporting is deferred to man.
    """
    try:
      process = subprocess.Popen(
          ['man',
           '-M', os.path.join(help_dir, 'man'),  # Sets the man search path.
           '-'.join(path),
          ],
          stderr=subprocess.PIPE)
      _, stderr = process.communicate()
      if process.returncode == 0:
        return
      else:
        logging.debug('man process returned with exit code %s; stderr: %s',
                      process.returncode, stderr)
    except OSError as e:
      logging.debug('There was a problem launching man: %s', e)

    logging.debug('Falling back to plain-text help.')

    text_help_file_path = os.path.join(help_dir, 'text.long', '-'.join(path))
    try:
      with open(text_help_file_path) as f:
        sys.stdout.write(f.read())
    except IOError:
      raise NoHelpFound(
          'no manual entry for command: {0}'.format(' '.join(path)))

  if os.path.exists(help_dir):
    return Help
  else:
    return None


def CLI(name, command_root_directory, module_directories=None,
        top_level_command=None, allow_no_credentials=False, auth=True,
        allow_non_existing_modules=False, version_func=None):
  """Get a ready-to-go CLI for Cloud SDK tools.

  Args:
    name: str, The name of your CLI. Should probably be the same as the
        executable name.
    command_root_directory: str, The absolute path to the tools root.
    module_directories: {str: str}, A Map of subgroup name to alternate roots.
    top_level_command: str, The name of the top level command to use, instead
        of a command group.
    allow_no_credentials: bool, If false, the command cannot run unless logged
        in. If true, the command may receive no credentials and an unauthorized
        http object. If credentials are required for some operations, but not
        others, config.NoAuthException should be raised when there is a problem.
    auth: bool, If false, the CLI will never try to load credentials.
    allow_non_existing_modules: bool, If true, module directories that don't
        exist will be ignored rather than cause errors.
    version_func: func, Function to call with -v, --version.

  Returns:
    calliope.CommandLoader, An object that will run the tools from the command
        line.
  """

  def Context(cfg):
    """Context for any authenticated CLIs."""
    try:
      cred = (Credentials(allow_no_credentials=allow_no_credentials)
              if auth else None)
      http = Http(auth=auth, creds=cred)
      c_store.Refresh(cred, http)
    except NoAuthException:
      raise exceptions.ToolException.FromCurrent()

    project_name = cfg.get(config.CLOUDSDK_PROJECT_KEY)

    return {
        config.CLOUDSDK_PROJECT_KEY: project_name,
        config.CLOUDSDK_CREDENTIALS_KEY: cred,
        config.CLOUDSDK_AUTHENTICATED_HTTP_KEY: http,
    }

  paths = config.Paths()

  help_dir = os.path.join(os.path.dirname(command_root_directory), 'help')

  return calliope.CommandLoader(
      name=name,
      command_root_directory=command_root_directory,
      module_directories=module_directories,
      top_level_command=top_level_command,
      load_context=Context,
      config_file=paths.config_json_path,
      logs_dir=paths.logs_dir,
      allow_non_existing_modules=allow_non_existing_modules,
      version_func=version_func,
      help_func=GetHelp(help_dir),
  )


def ParseConfigFromFile(config_path, path_normalizer_fn=None):
  """Parses a YAML configuration file for creating a CLI.

  Args:
    config_path: str, The absolute path to the YAML file.
    path_normalizer_fn: function, A function that can normalize file
      paths with forward slashes on the current platform.

  Raises:
    UnexpectedKeysException: If the configuration contains any
      unrecognized keys.

  Returns:
    dict, A dict with the results.
  """
  def PathNormalizer(path):
    return os.path.join(GooglePackageRoot(), *path)

  path_normalizer_fn = path_normalizer_fn or PathNormalizer

  with open(config_path) as f:
    config_dict = yaml.load(f.read())

  kwargs = {
      'name': config_dict.pop('name'),
      'command_root_directory': path_normalizer_fn(
          config_dict.pop('command_root_directory')),
  }

  if 'module_directories' in config_dict:
    module_directories = {}
    for entry in config_dict.pop('module_directories'):
      module_directories[entry.pop('name')] = path_normalizer_fn(
          entry.pop('directory'))

      remaining_keys = entry.keys()
      if remaining_keys:
        raise UnexpectedKeysException(
            'found unrecognized CLI config keys in module_directories: ' +
            ', '.join(remaining_keys))

    kwargs['module_directories'] = module_directories

  if 'top_level_command' in config_dict:
    kwargs['top_level_command'] = config_dict.pop('top_level_command')

  if 'allow_no_credentials' in config_dict:
    kwargs['allow_no_credentials'] = config_dict.pop('allow_no_credentials')

  if 'allow_non_existing_modules' in config_dict:
    kwargs['allow_non_existing_modules'] = (
        config_dict.pop('allow_non_existing_modules'))

  if 'auth' in config_dict:
    kwargs['auth'] = config_dict.pop('auth')

  # Ensures that no other keys remain in the configuration dict.
  remaining_keys = config_dict.keys()
  if remaining_keys:
    raise UnexpectedKeysException(
        'found unrecognized CLI config keys: ' + ', '.join(remaining_keys))
  else:
    return kwargs


def CLIFromConfig(config_path, **kwargs):
  """Get a ready-to-go CLI for Cloud SDK tools using a YAML configuration.

  At the minimum, the YAML configuration file must contain the
  top-level keys name and command_root_directory.

  See the cli.CLI's docstring for details of allowed keys. The following is
  an example config file:

    name: gcloud
    command_root_directory: [path, to, gcloud]
    module_directories:
      - name: tool-1
        directory: [path, to, tool-1]
    top_level_command: gcloud
    allow_no_credentials: false
    auth: true

  Args:
    config_path: str, The path to the YAML configuration.
    **kwargs: {str:object}, Additional arguments that cannot come from
        configuration.

  Returns:
    calliope.CommandLoader, An object that will run the tools from the command
      line.
  """
  kwargs.update(ParseConfigFromFile(config_path))
  return CLI(**kwargs)


def GooglePackageRoot():
  return config.GooglePackageRoot()


def Credentials(allow_no_credentials=False):
  """Get the currently active credentials.

  This function inspects the config at CLOUDSDK_CONFIG_JSON to decide which of
  the credentials available in CLOUDSDK_CONFIG_CREDENTIALS to return.

  These credentials will be refreshed before being returned, so it makes sense
  to cache the value returned for short-lived programs.

  Args:
    allow_no_credentials: bool, If false, a NoAuthException will be thrown if
        there are no valid credentials. If true, None will be returned instead.

  Returns:
    An active, valid credentials object. Or None if allow_no_credentials is true
    and no credentials exist.

  Raises:
    NoAuthException: If there are no currently authorized credentials.
  """
  creds = c_store.Load()

  if not creds and not allow_no_credentials:
    raise NoAuthException()

  return creds


def Http(auth=True, creds=None):
  """Get an httplib2.Http object for working with the Google API.

  Args:
    auth: bool, True if the http object returned should be authorized.
    creds: oauth2client.client.Credentials, If auth is True and creds is not
        None, use those credentials to authorize the httplib2.Http object.

  Returns:
    An authorized httplib2.Http object, or a regular httplib2.Http object if no
    credentials are available.

  """

  # TODO(user): Have retry-once-if-denied logic, to allow client tools to not
  # worry about refreshing credentials.

  http = httplib2.Http()
  if auth:
    try:
      if not creds:
        creds = Credentials()
      http = creds.authorize(http)
    except NoAuthException:
      pass
  return http
