# Copyright 2013 Google Inc. All Rights Reserved.

"""Common utility functions for sql tool."""
import os.path
import re

from oauth2client.anyjson import simplejson

from google.cloud.sdk.core import log
from google.cloud.sdk.core import properties


CLIENT_USER_AGENT = 'gcloud/sql'

SCOPES = (
    'https://www.googleapis.com/auth/cloud-platform',
    'https://www.googleapis.com/auth/sqlservice.admin',)


USER_HOME = os.path.expanduser('~/')

SQL_CONFIG = os.getenv(
    'SQL_CONFIG',
    os.path.join(USER_HOME, '.config', 'sql')
)

CREDENTIAL_STORE_PATH = os.path.join(
    SQL_CONFIG,
    'credentials')

EXTRA_INDENT = 2

QUIT = 'QUIT'


class PrettyPrinter(object):
  """A class for pretty printing stuff."""
  indent = 0

  def __init__(self, indent):
    self.printer = log.ConsoleWriter()
    self.indent = indent

  def PrintInstance(self, instance):
    """Pretty prints an instances resource.

    Args:
      instance: A dict object representing the instances resource to be pretty
      printed.
    """
    for key, value in sorted(instance.items()):
      if key == 'settings':
        self.Print('settings (Modifiable attributes):')
        self.Print('[')
        self.indent += 2
        self.PrintSettings(value)
        self.indent -= 2
        self.Print(']')
      elif key == 'serverCaCert':
        self.Print('serverCaCert:')
        self.Print('[')
        self.indent += 2
        self.PrintSslCert(value)
        self.indent -= 2
        self.Print(']')
      elif key == 'ipAddresses':
        self.Print('ipAddresses:')
        self.Print('[')
        for ip_address in value:
          self.indent += 2
          self.PrintIpAddresses(ip_address)
          self.indent -= 2
        self.Print(']')
      elif key == 'currentDiskSize' or key == 'maxDiskSize':
        self.Print('%s: %s' % (key, GetHumanReadableDiskSize(value)))
      elif not (key == 'kind' or key == 'etag'):
        self.Print('%s: %s' % (key, value))

  def PrintSettings(self, settings):
    """Pretty prints a settings object in instances resource.

    Args:
      settings: A dict object representing settings.
    """
    for key, value in sorted(settings.items()):
      if key == 'authorizedGaeApplications':
        self.PrintList('authorizedGaeApplications', value)
      elif key == 'backupConfiguration':
        self.Print('backupConfiguration:')
        self.Print('[')
        self.indent += 2
        self.PrintBackupConfiguration(value)
        self.indent -= 2
        self.Print(']')
      elif key == 'ipConfiguration':
        self.Print('ipConfiguration:')
        self.Print('[')
        self.indent += 2
        self.PrintIpConfiguration(value)
        self.indent -= 2
        self.Print(']')
      elif key == 'locationPreference':
        if value.has_key('zone') or value.has_key('followGaeApplication'):
          self.Print('locationPreference:')
          self.Print('[')
          self.indent += 2
          self.PrintLocationPreference(value)
          self.indent -= 2
          self.Print(']')
      elif key != 'kind':
        self.Print('%s: %s' % (key, value))

  def PrintBackupConfiguration(self, backup_configurations):
    """Pretty prints a backup configurations object in instances resource.

    Args:
      backup_configurations: A list of backupConfiguration dict objects.
    """
    for backup_configuration in backup_configurations:
      for key, value in sorted(backup_configuration.items()):
        if key != 'kind':
          self.Print('%s: %s' % (key, value))

  def PrintIpConfiguration(self, ip_configuration):
    """Pretty prints a ip configurations object in instances resource.

    Args:
      ip_configuration: An ipConfiguration dict object.
    """
    for key, value in sorted(ip_configuration.items()):
      if key == 'authorizedNetworks':
        self.PrintList('authorizedNetworks', value)
      elif key != 'kind':
        self.Print('%s: %s' % (key, value))

  def PrintLocationPreference(self, location_preference):
    """Pretty prints a location preference object in instances resource.

    Args:
      location_preference: A locationPreference dict object.
    """
    for key, value in sorted(location_preference.items()):
      if key != 'kind':
        self.Print('%s: %s' % (key, value))

  def PrintBackupRun(self, backup_run):
    """Pretty prints a backup run resource.

    Args:
      backup_run: A dict object representing the backuprun resource to be pretty
      printed.
    """
    for key, value in sorted(backup_run.items()):
      if key != 'kind' and key != 'instance' and key != 'backupConfiguration':
        self.Print('%s: %s' % (key, value))

  def PrintIpAddresses(self, ip_address):
    """Pretty prints a list of ipAddress objects in the instance resource.

    Args:
      ip_address: A list object containing the ipAddress dict objects to be
      pretty printed.
    """
    for key, value in sorted(ip_address.items()):
      if key != 'kind':
        self.Print('%s: %s' % (key, value))

  def PrintOperation(self, operation):
    """Pretty prints an operations resource.

    Args:
      operation: A dict object representing the operations resource to be pretty
      printed.
    """
    for key, value in sorted(operation.items()):
      if key == 'error':
        self.PrintOperationErrors(value)
      elif key == 'importContext':
        self.PrintImportContext(value)
      elif key == 'exportContext':
        self.PrintExportContext(value)
      elif key != 'kind':
        self.Print('%s: %s' % (key, value))

  def PrintSslCertInsertResponse(self, insert_response):
    """Pretty prints an Ssl cert insert response.

    Args:
      insert_response: A dict object representing the sslcert insert response to
      be pretty printed.
    """
    private_key = insert_response.get('clientCert').get('certPrivateKey')
    self.Print('Private Key:\n' + private_key)

  def PrintSslCert(self, ssl_cert):
    """Pretty prints an Ssl Cert resource.

    Args:
      ssl_cert: A dict object representing the ssl_certs resource to be pretty
      printed.
    """
    for key, value in sorted(ssl_cert.items()):
      if key == 'cert':
        self.Print('%s: \n%s' % (key, value))
      elif key != 'kind':
        self.Print('%s: %s' % (key, value))

  def PrintImportContext(self, import_context):
    """Pretty prints import context for an operation resource.

    Args:
      import_context: A dict object representing the import context to be pretty
      printed.
    """
    self.Print('import context:')
    self.Print('[')
    if 'uri' in import_context:
      self.indent += 2
      self.PrintList('uri(s)', import_context['uri'])
      self.indent -= 2
    if 'database' in import_context:
      self.Print('database: %s' % import_context['database'])
    self.Print(']')

  def PrintExportContext(self, export_context):
    """Pretty prints export context for an operation resource.

    Args:
      export_context: A dict object representing the export context to be pretty
      printed.
    """
    self.Print('export context:')
    self.Print('[')
    if 'uri' in export_context:
      self.indent += 2
      self.Print('uri: %s' % export_context['uri'])
      self.indent -= 2
    if 'database' in export_context:
      self.indent += 2
      self.PrintList('database(s)', export_context['database'])
      self.indent -= 2
    if 'table' in export_context:
      self.indent += 2
      self.PrintList('table(s)', export_context['table'])
      self.indent -= 2
    self.Print(']')

  def PrintOperationErrors(self, operation_errors):
    """Pretty prints an operation errors for an operation resource.

    Args:
      operation_errors: A list object representing the operation errors to be
      pretty printed.
    """
    error_list = [error['code'] for error in operation_errors]
    self.PrintList('Operation error(s)', error_list)

  def Print(self, string):
    """Prints a given string with indentation.

    Args:
      string: The string to be printed.
    """
    spacing = ' '  * self.indent
    self.printer.Print(spacing + string)

  def PrintList(self, list_name, list_of_strings):
    """Prints a list of strings.

    Args:
      list_name: A string representing the name for the list.
      list_of_strings: list of strings to be printed.
    """
    self.Print('%s: %s' % (list_name, ', '.join(list_of_strings)))


def GetHumanReadableDiskSize(size):
  """Returns a human readable string representation of the disk size.

  Args:
    size: Disk size represented as number of bytes.

  Returns:
    A human readable string representation of the disk size.
  """
  for unit in ['bytes', 'KB', 'MB', 'GB', 'TB']:
    if size < 1024.0:
      return '%3.1f %s' % (size, unit)
    size = float(size) / 1024.0


def GetError(error):
  """Returns a ready-to-print string representation from the http response.

  Args:
    error: A string representing the raw json of the Http error response.

  Returns:
    A ready-to-print string representation of the error.
  """
  data = simplejson.loads(error.content)
  reason = data['error']['errors'][0]['reason']
  status = data['error']['code']
  message = data['error']['message']
  code = error.resp.reason
  return ('ResponseError: status=%s, code=%s, reason=%s\nmessage=%s'
          % (str(status), code, reason, message))


def GetInstanceIdWithoutProject(instance_name):
  """Gets the instance id alone from the given instance name.

  Parses the given instance name and returns the instance id alone leaving
  the project id portion of the instance name.

  Args:
    instance_name: A string representing the instance name of the form
    domain:project:instance or project:instance or instance.
  Returns:
    A string that represents the instance id without project id part.
  """
  match = re.findall(r'(?::?)([a-z0-9\-]+)', instance_name)
  # The part after the last colon corresponds to instance name.
  return match[-1]


def GetProjectId(instance_name):
  """Gets the project id from the given instance name.

  Parses the given instance name and returns the project id (along with domain
  if applicable) leaving out the instance id portion of the instance name.

  Args:
    instance_name: A string representing the instance name of the form
    domain:project:instance or project:instance or instance.

  Returns:
    A string that represents the project id of the given instance.
  """
  match = re.findall(r'(?::?)([a-z0-9\-\.]+)', instance_name)
  # The part before the last colon corresponds to instance name.
  if len(match) == 2:
    return match[0]
  elif len(match) == 3:
    return match[0] + ':' + match[1]
  else:
    return properties.VALUES.core.project.Get()
