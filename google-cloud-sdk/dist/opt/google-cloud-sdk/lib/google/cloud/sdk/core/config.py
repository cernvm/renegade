# Copyright 2013 Google Inc. All Rights Reserved.

"""Config for Google Cloud Platform CLIs."""

import json
import os

import google

from google.cloud.sdk.core.util import files as file_utils
from google.cloud.sdk.core.util import platforms


class Error(Exception):
  """Exceptions for the cli module."""


class GooglePackageRootNotFoundException(Error):
  """An exception to be raised when the google root is unable to be found.

  This exception should never be raised, and indicates a problem with the
  environment.
  """


def GooglePackageRoot():

  # pylint:disable=unreachable, would be nicer to have MOE insert this block.
  # pylint:disable=g-import-not-at-top, want it in this unreachable place, when

  path = __file__
  while True:
    parent, here = os.path.split(path)
    if not here:
      break
    if here == 'google':
      return path
    path = parent

  raise GooglePackageRootNotFoundException()


# Environment variable for the directory containing Cloud SDK configuration.
CLOUDSDK_CONFIG = 'CLOUDSDK_CONFIG'

CLOUDSDK_PROJECT_KEY = 'cloudsdk-project'
# Context key for the user agent to use for auth.
CLOUDSDK_USER_AGENT_KEY = 'cloudsdk-user-agent'
# Context key for the authorized credentials.
CLOUDSDK_CREDENTIALS_KEY = 'cloudsdk-credentials'
# Context key for the authenticated Httplib2.Http object.
CLOUDSDK_AUTHENTICATED_HTTP_KEY = 'cloudsdk-http'
# Context key for the path to a clientsecrets JSON file.
CLOUDSDK_CLIENTSECRETS_KEY = 'cloudsdk-clientsecrets'
# Context key for the path to a credential storage.
CLOUDSDK_CREDENTIAL_STORAGE_KEY = 'cloudsdk-credential-storage'
# Context key for the current scopes.
CLOUDSDK_SCOPES_KEY = 'cloudsdk-scopes'
# Context key for the update manager.
CLOUDSDK_UPDATE_MANAGER_KEY = 'cloudsdk-update-manager'

# Config key for the key into the credentials store for the active credentials.
CLOUDSDK_ACTIVE_CREDENTIALS_KEY_KEY = 'cloudsdk-active-credentials-key'


class InstallationConfig(object):
  """Loads configuration constants from the core config file.

  Attributes:
    version: str, The version of the core component.
    user_agent: str, The base string of the user agent to use when making API
      calls.
    documentation_url: str, The URL where we can redirect people when they need
      more information.
    snapshot_url: str, The url for the component manager to look at for
      updates.
    disable_updater: bool, True to disable the component manager for this
      installation.  We do this for distributions through another type of
      package manager like apt-get.
    snapshot_schema_version: int, The version of the snapshot schema this code
      understands.
    release_channel: str, The release channel for this Cloud SDK distribution.
      The default is 'stable'.
    config_suffix: str, A string to add to the end of the configuration
      directory name so that different release channels can have separate
      config.
  """

  @staticmethod
  def Load():
    """Initializes the object with values from the config file.

    Returns:
      InstallationSpecificData: The loaded data.
    """
    config_file = os.path.join(GooglePackageRoot(),
                               'cloud', 'sdk', 'core', 'config.json')
    with open(config_file) as f:
      data = json.load(f)
    return InstallationConfig(**data)

  def __init__(self, version, user_agent, documentation_url, snapshot_url,
               disable_updater, snapshot_schema_version, release_channel,
               config_suffix):
    # JSON returns all unicode.  We know these are regular strings and using
    # unicode in environment variables on Windows doesn't work.
    self.version = str(version)
    self.user_agent = str(user_agent)
    self.documentation_url = str(documentation_url)
    self.snapshot_url = str(snapshot_url)
    self.disable_updater = disable_updater
    # This one is an int, no need to convert
    self.snapshot_schema_version = snapshot_schema_version
    self.release_channel = str(release_channel)
    self.config_suffix = str(config_suffix)

  def IsAlternateReleaseChannel(self):
    """Determines if this distribution is using an alternate release channel.

    Returns:
      True if this distribution is not the 'stable' release channel, False
      otherwise.
    """
    return self.release_channel != 'stable'


INSTALLATION_CONFIG = InstallationConfig.Load()

# TODO(user): Have this version get set automatically somehow. Replacer?
CLOUD_SDK_VERSION = INSTALLATION_CONFIG.version
# TODO(user): Distribute a clientsecrets.json to avoid putting this in code.
CLOUDSDK_CLIENT_ID = '32555940559.apps.googleusercontent.com'
CLOUDSDK_CLIENT_NOTSOSECRET = 'ZmssLNjJy2998hD4CTg2ejr2'

CLOUDSDK_USER_AGENT = INSTALLATION_CONFIG.user_agent

# TODO(user): Consider a way to allow users to choose a smaller scope set,
# knowing that things might fail if they try to use a tool with scopes that have
# not been granted.
CLOUDSDK_SCOPES = [
    'https://www.googleapis.com/auth/appengine.admin',
    'https://www.googleapis.com/auth/bigquery',
    'https://www.googleapis.com/auth/compute',
    'https://www.googleapis.com/auth/devstorage.full_control',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/ndev.cloudman',
    'https://www.googleapis.com/auth/cloud-platform',
    'https://www.googleapis.com/auth/sqlservice.admin',
    'https://www.googleapis.com/auth/prediction',
    'https://www.googleapis.com/auth/projecthosting',
]




def _CheckForExtraScopes():
  extra_scopes = os.environ.get('CLOUDSDK_EXTRA_SCOPES')
  if not extra_scopes:
    return
  CLOUDSDK_SCOPES.extend(extra_scopes.split())

_CheckForExtraScopes()


class Paths(object):
  """Class to encapsulate the various directory paths of the Cloud SDK.

  Attributes:
    global_config_dir: str, The path to the user's global config area.
    workspace_dir: str, The path of the current workspace or None if not in a
      workspace.
    workspace_config_dir: str, The path to the config directory under the
      current workspace, or None if not in a workspace.
  """
  # Name of the directory that roots a cloud SDK workspace.
  _CLOUDSDK_WORKSPACE_CONFIG_WORD = ('gcloud' +
                                     INSTALLATION_CONFIG.config_suffix)
  CLOUDSDK_WORKSPACE_CONFIG_DIR_NAME = '.%s' % _CLOUDSDK_WORKSPACE_CONFIG_WORD

  def __init__(self):
    if platforms.OperatingSystem.Current() == platforms.OperatingSystem.WINDOWS:
      try:
        default_config_path = os.path.join(
            os.environ['APPDATA'], Paths._CLOUDSDK_WORKSPACE_CONFIG_WORD)
      except KeyError:
        # This should never happen unless someone is really messing with things.
        drive = os.environ.get('SystemDrive', 'C:')
        default_config_path = os.path.join(
            drive, '\\', Paths._CLOUDSDK_WORKSPACE_CONFIG_WORD)
    else:
      default_config_path = os.path.join(
          os.path.expanduser('~'), '.config',
          Paths._CLOUDSDK_WORKSPACE_CONFIG_WORD)
    self.global_config_dir = os.getenv(CLOUDSDK_CONFIG, default_config_path)
    self.workspace_dir = file_utils.FindDirectoryContaining(
        os.getcwd(), Paths.CLOUDSDK_WORKSPACE_CONFIG_DIR_NAME)
    self.workspace_config_dir = None
    if self.workspace_dir:
      self.workspace_config_dir = os.path.join(
          self.workspace_dir, Paths.CLOUDSDK_WORKSPACE_CONFIG_DIR_NAME)

  @property
  def config_dir(self):
    """The directory to use for configuration.

    If in a workspace, that config directory will be used, otherwise the global
    one will be used.

    Returns:
      str, The path to the config directory.
    """
    if self.workspace_config_dir:
      return self.workspace_config_dir
    return self.global_config_dir

  @property
  def credentials_path(self):
    """Gets the path to the file to store credentials in.

    Credentials are always stored in global config, never the local workspace.
    This is due to the fact that local workspaces are likely to be stored whole
    in source control, and we don't want to accidentally publish credential
    information.  We also want user credentials to be shared across workspaces
    if they are for the same user.

    Returns:
      str, The path to the credential file.
    """
    return os.path.join(self.global_config_dir, 'credentials')

  @property
  def config_json_path(self):
    """Gets the path to the file to use for persistent json storage in calliope.

    Returns:
      str, The path to the file to use for storage.
    """
    return os.path.join(self.config_dir, 'config.json')

  @property
  def logs_dir(self):
    """Gets the path to the directory to put logs in for calliope commands.

    Returns:
      str, The path to the directory to put logs in.
    """
    return os.path.join(self.config_dir, 'logs')

  @property
  def analytics_cid_path(self):
    """Gets the path to the file to store the client id for analytics.

    This is always stored in the global location because it is per install.

    Returns:
      str, The path the file.
    """
    return os.path.join(self.global_config_dir, '.metricsUUID')

  @property
  def global_properties_path(self):
    """Gets the path to the properties file in the global config dir.

    Returns:
      str, The path to the file.
    """
    return os.path.join(self.global_config_dir, 'properties')

  @property
  def workspace_properties_path(self):
    """Gets the path to the properties file in your local workspace.

    Returns:
      str, The path to the file, or None if there is no local workspace.
    """
    if not self.workspace_config_dir:
      return None
    return os.path.join(self.workspace_config_dir, 'properties')

  def LegacyCredentialsDir(self, account):
    """Gets the path to store legacy multistore credentials in.

    Args:
      account: str, Email account tied to the authorizing credentials.

    Returns:
      str, The path to the multistore credentials file.
    """
    if not account:
      account = 'default'
    return os.path.join(self.global_config_dir, 'legacy_credentials', account)

  def LegacyCredentialsMultistorePath(self, account):
    """Gets the path to store legacy multistore credentials in.

    Args:
      account: str, Email account tied to the authorizing credentials.

    Returns:
      str, The path to the multistore credentials file.
    """
    return os.path.join(self.LegacyCredentialsDir(account), 'multistore.json')

  def LegacyCredentialsJSONPath(self, account):
    """Gets the path to store legacy JSON credentials in.

    Args:
      account: str, Email account tied to the authorizing credentials.

    Returns:
      str, The path to the JSON credentials file.
    """
    return os.path.join(self.LegacyCredentialsDir(account), 'singlestore.json')

  def LegacyCredentialsGAEJavaPath(self, account):
    """Gets the path to store legacy GAE for Java credentials in.

    Args:
      account: str, Email account tied to the authorizing credentials.

    Returns:
      str, The path to the  GAE for Java credentials file.
    """
    return os.path.join(self.LegacyCredentialsDir(account), 'gaejava.txt')

  def LegacyCredentialsGSUtilPath(self, account):
    """Gets the path to store legacy GAE for Java credentials in.

    Args:
      account: str, Email account tied to the authorizing credentials.

    Returns:
      str, The path to the  GAE for Java credentials file.
    """
    return os.path.join(self.LegacyCredentialsDir(account), '.boto')

  def GCECachePath(self):
    """Get the path to cache whether or not we're on a GCE machine.

    Returns:
      str, The path to the GCE cache.
    """
    return os.path.join(self.global_config_dir, 'gce')
