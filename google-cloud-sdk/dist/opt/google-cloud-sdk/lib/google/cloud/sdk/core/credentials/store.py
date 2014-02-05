# Copyright 2013 Google Inc. All Rights Reserved.

"""One-line documentation for auth module.

A detailed description of auth.
"""

import datetime
import os

import httplib2
from oauth2client import client
from oauth2client import gce as oauth2client_gce
from oauth2client import multistore_file

from google.cloud.sdk.core import config
from google.cloud.sdk.core import properties
from google.cloud.sdk.core.credentials import flow
from google.cloud.sdk.core.credentials import gce as c_gce
from google.cloud.sdk.core.credentials import legacy
from google.cloud.sdk.core.util import files


GOOGLE_OAUTH2_PROVIDER_AUTHORIZATION_URI = (
    'https://accounts.google.com/o/oauth2/auth')
GOOGLE_OAUTH2_PROVIDER_TOKEN_URI = (
    'https://accounts.google.com/o/oauth2/token')


class Error(Exception):
  """Exceptions for the credentials module."""


class NoCredentialsForAccountException(Error):
  """Exception for when no credentials are found for an account."""

  def __init__(self, account):
    super(NoCredentialsForAccountException, self).__init__(
        'No credentials for %s.' % account)


class NoActiveAccountException(Error):
  """Exception for when there are no valid active credentials."""

  def __init__(self, message='No active credentials.'):
    super(NoActiveAccountException, self).__init__(message)


class FlowError(Error):
  """Exception for when something goes wrong with a web flow."""


class RefreshError(Error):
  """Exception for when there was a problem refreshing."""


class RevokeError(Error):
  """Exception for when there was a problem revoking."""


def _StorageForAccount(account):
  """Get the oauth2client.multistore_file storage.

  Args:
    account: str, The account tied to the storage being fetched.

  Returns:
    oauth2client.client.Storage, A credentials store.
  """
  storage_path = config.Paths().credentials_path
  parent_dir, unused_name = os.path.split(storage_path)
  files.MakeDir(parent_dir)

  storage_key = {
      'type': 'google-cloud-sdk',
      'account': account,
      'clientId': config.CLOUDSDK_CLIENT_ID,
      'scope': ' '.join(config.CLOUDSDK_SCOPES),
  }

  storage = multistore_file.get_credential_storage_custom_key(
      filename=storage_path,
      key_dict=storage_key)
  return storage


def AvailableAccounts():
  """Get all accounts that have credentials stored for the CloudSDK.

  This function will also ping the GCE metadata server to see if GCE credentials
  are available.

  Returns:
    [str], List of the accounts.

  """
  all_keys = multistore_file.get_all_credential_keys(
      filename=config.Paths().credentials_path)

  accounts = []

  for key in all_keys:
    if key.get('type') != 'google-cloud-sdk':
      continue
    if key.get('clientId') != config.CLOUDSDK_CLIENT_ID:
      continue
    if key.get('scope') != ' '.join(config.CLOUDSDK_SCOPES):
      continue
    accounts.append(key['account'])

  accounts.extend(c_gce.Metadata().Accounts())

  accounts.sort()

  return accounts


def ActiveAccount():
  """Get the currently active CloudSDK account.

  Returns:
    str, The account name.
  """
  account = properties.VALUES.core.account.Get()

  return account


def Load(account=None):
  """Get the credentials associated with the provided account.

  Args:
    account: str, The account address for the credentials being fetched. If
        None, the account stored in the core.account property is used.

  Returns:
    oauth2client.client.Credentials, The specified credentials.

  Raises:
    NoActiveAccountException: If account is not provided and there is no
        active account.
    NoCredentialsForAccountException: If there are no valid credentials
        available for the provided or active account.
    c_gce.CannotConnectToMetadataServerException: If the metadata server cannot
        be reached.
  """
  if not account:
    account = properties.VALUES.core.account.Get()

  if not account:
    raise NoActiveAccountException()

  if account in c_gce.Metadata().Accounts():
    return AcquireFromGCE(account)

  store = _StorageForAccount(account)
  if not store:
    raise NoCredentialsForAccountException(account)
  cred = store.get()
  if not cred:
    raise NoCredentialsForAccountException(account)

  return cred


def Refresh(creds, http=None):
  """Refresh credentials.

  Calls creds.refresh(), unless they're SignedJwtAssertionCredentials.

  Args:
    creds: oauth2client.client.Credentials, The credentials to refresh.
    http: httplib2.Http, The http transport to refresh with.
  """
  # TODO(user): Remove this function when oauth2client does not hang while
  # refreshing SignedJwtAssertionCredentials.
  if creds and (not client.HAS_CRYPTO or
                type(creds) != client.SignedJwtAssertionCredentials):
    try:
      creds.refresh(http or httplib2.Http())
    except client.AccessTokenRefreshError as e:
      raise RefreshError(e)


def Store(creds, account=None):
  """Store credentials according for an account address.

  Args:
    creds: oauth2client.client.Credentials, The credentials to be stored.
    account: str, The account address of the account they're being stored for.
        If None, the account stored in the core.account property is used.

  Raises:
    NoActiveAccountException: If account is not provided and there is no
        active account.
  """
  if not account:
    account = properties.VALUES.core.account.Get()
  if not account:
    raise NoActiveAccountException()

  store = _StorageForAccount(account)
  store.put(creds)
  creds.set_store(store)
  _GetLegacyGen(account, creds).WriteTemplate()


def _GetLegacyGen(account, creds):
  return legacy.LegacyGenerator(
      multistore_path=config.Paths().LegacyCredentialsMultistorePath(account),
      json_path=config.Paths().LegacyCredentialsJSONPath(account),
      gae_java_path=config.Paths().LegacyCredentialsGAEJavaPath(account),
      gsutil_path=config.Paths().LegacyCredentialsGSUtilPath(account),
      credentials=creds, scopes=config.CLOUDSDK_SCOPES)


def Revoke(account=None):
  """Revoke credentials and clean up related files.

  Args:
    account: str, The account address for the credentials to be revoked. If
        None, the currently active account is used.

  Raises:
    NoCredentialsForAccountException: If the provided account is not tied to any
        known credentials.
    RevokeError: If there was a more general problem revoking the account.
  """
  if not account:
    account = ActiveAccount()

  if account in c_gce.Metadata().Accounts():
    raise RevokeError('Cannot revoke GCE-provided credentials.')

  creds = Load(account)
  if not creds:
    raise NoCredentialsForAccountException(account)

  # TODO(user): Remove this condition when oauth2client does not crash while
  # revoking SignedJwtAssertionCredentials.
  if creds and (not client.HAS_CRYPTO or
                type(creds) != client.SignedJwtAssertionCredentials):
    creds.revoke(httplib2.Http())
  store = _StorageForAccount(account)
  if store:
    store.delete()

  _GetLegacyGen(account, creds).Clean()
  files.RmTree(config.Paths().LegacyCredentialsDir(account))


def AcquireFromWebFlow(launch_browser=True,
                       auth_uri=GOOGLE_OAUTH2_PROVIDER_AUTHORIZATION_URI,
                       token_uri=GOOGLE_OAUTH2_PROVIDER_TOKEN_URI):
  """Get credentials via a web flow.

  Args:
    launch_browser: bool, Open a new web browser window for authorization.
    auth_uri: str, URI to open for authorization.
    token_uri: str, URI to use for refreshing.

  Returns:
    client.Credentials, Newly acquired credentials from the web flow.

  Raises:
    FlowError: If there is a problem with the web flow.
  """
  webflow = client.OAuth2WebServerFlow(
      client_id=config.CLOUDSDK_CLIENT_ID,
      client_secret=config.CLOUDSDK_CLIENT_NOTSOSECRET,
      scope=config.CLOUDSDK_SCOPES,
      user_agent=config.CLOUDSDK_USER_AGENT,
      auth_uri=auth_uri,
      token_uri=token_uri)

  try:
    cred = flow.Run(webflow, launch_browser=launch_browser)
  except flow.Error as e:
    raise FlowError(e)
  return cred


def AcquireFromToken(refresh_token,
                     token_uri=GOOGLE_OAUTH2_PROVIDER_TOKEN_URI):
  """Get credentials from an already-valid refresh token.

  Args:
    refresh_token: An oauth2 refresh token.
    token_uri: str, URI to use for refreshing.

  Returns:
    client.Credentials, Credentials made from the refresh token.
  """
  cred = client.OAuth2Credentials(
      access_token=None,
      client_id=config.CLOUDSDK_CLIENT_ID,
      client_secret=config.CLOUDSDK_CLIENT_NOTSOSECRET,
      refresh_token=refresh_token,
      # always start expired
      token_expiry=datetime.datetime.utcnow(),
      token_uri=token_uri,
      user_agent=config.CLOUDSDK_USER_AGENT)
  return cred


def AcquireFromGCE(account=None):
  """Get credentials from a GCE metadata server.

  Args:
    account: str, The account name to use. If none, the default is used.

  Returns:
    client.Credentials, Credentials taken from the metadata server.

  Raises:
    c_gce.CannotConnectToMetadataServerException: If the metadata server cannot
        be reached.
    Error: If a non-default service account is used.
  """
  default_account = c_gce.Metadata().DefaultAccount()
  if account is None:
    account = default_account
  if account != default_account:
    raise Error('Unable to use non-default GCE service accounts.')
  # TODO(user): Update oauth2client to fetch alternate credentials. This
  # inability is not currently a problem, because the metadata server does not
  # yet provide multiple service accounts.

  cred = oauth2client_gce.AppAssertionCredentials(config.CLOUDSDK_SCOPES)
  try:
    cred.refresh(httplib2.Http())
  except httplib2.ServerNotFoundError:
    raise c_gce.CannotConnectToMetadataServerException()

  return cred
