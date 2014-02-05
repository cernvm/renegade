# Copyright 2013 Google Inc. All Rights Reserved.

"""Read and write properties for the CloudSDK."""

import ConfigParser
import os

from google.cloud.sdk.core import config
from google.cloud.sdk.core.credentials import gce as c_gce
from google.cloud.sdk.core.util import files


class Error(Exception):
  """Exceptions for the config module."""


class PropertiesParseError(Error):
  """An exception to be raised when a properties file is invalid."""


class NotInAWorkspaceError(Error):
  """An exception to be raised when you must be in a workspace."""


class NoSuchPropertyError(Error):
  """An exception to be raised when the desired property does not exist."""


class InvalidValueError(Error):
  """An exception to be raised when the set value of a property is invalid."""


class _Sections(object):
  """Represents the available sections in the properties file.

  Attributes:
    default_section: Section, The main section of the properties file (core).
    core: Section, The section containing core properties for the Cloud SDK.
    component_manager: Section, The section containing properties for the
      component_manager.
  """

  def __init__(self):
    self.core = _SectionCore()
    self.component_manager = _SectionComponentManager()

    self.__sections = dict((section.name, section) for section in
                           [self.core, self.component_manager])
    self.__args = None

  @property
  def default_section(self):
    return self.core

  def __iter__(self):
    return iter(self.__sections.values())

  def GetArgs(self):
    return self.__args

  def SetArgs(self, args):
    old_args = self.__args
    self.__args = args
    return old_args

  def Section(self, section):
    """Gets a section given its name.

    Args:
      section: str, The section for the desired property.

    Returns:
      Section, The section corresponding to the given name.

    Raises:
      NoSuchPropertyError: If the section is not known.
    """
    try:
      return self.__sections[section]
    except KeyError:
      raise NoSuchPropertyError('Section "{section}" does not exist.'.format(
          section=section))

  def AllValues(self, list_unset=False):
    """Gets the entire collection of property values for all sections.

    Args:
      list_unset: bool, If True, include unset properties in the result.

    Returns:
      {str:{str:str}}, A dict of sections to dicts of properties to values.
    """
    result = {}
    for section in self:
      section_result = section.AllValues(list_unset=list_unset)
      if section_result:
        result[section.name] = section_result
    return result


class _Section(object):
  """Represents a section of the properties file that has related properties.

  Attributes:
    name: str, The name of the section.
  """

  def __init__(self, name):
    self.__name = name
    self.__properties = {}

  @property
  def name(self):
    return self.__name

  def __iter__(self):
    return iter(self.__properties.values())

  def _Add(self, name, **kwargs):
    prop = _Property(section=self.__name, name=name, **kwargs)
    self.__properties[name] = prop
    return prop

  def Property(self, property_name):
    """Gets a property from this section, given its name.

    Args:
      property_name: str, The name of the desired property.

    Returns:
      Property, The property corresponding to the given name.

    Raises:
      NoSuchPropertyError: If the property is not known for this section.
    """
    try:
      return self.__properties[property_name]
    except KeyError:
      raise NoSuchPropertyError(
          'Section "{s}" has no property "{p}".'.format(
              s=self.__name,
              p=property_name))

  def AllValues(self, list_unset=False):
    """Gets all the properties and their values for this section.

    Args:
      list_unset: bool, If True, include unset properties in the result.

    Returns:
      {str:str}, The dict of {property:value} for this section.
    """
    properties_file = _PropertiesFile.Load()
    result = {}
    for prop in self:
      value = _GetProperty(prop, properties_file)
      if list_unset or value is not None:
        result[prop.name] = value
    return result


class _SectionCore(_Section):
  """Contains the properties for the 'core' section."""

  def __init__(self):
    super(_SectionCore, self).__init__('core')
    # pylint: disable=unnecessary-lambda, We don't want to call Metadata()
    # unless we really have to.
    self.account = self._Add(
        'account', callbacks=[lambda: c_gce.Metadata().DefaultAccount()])
    self.disable_prompts = self._Add('disable_prompts', argument='quiet')
    self.disable_usage_reporting = self._Add('disable_usage_reporting')
    self.cli_verbosity = self._Add('cli_verbosity')
    self.interactive_verbosity = self._Add('interactive_verbosity')
    # pylint: disable=unnecessary-lambda, Just a value return.
    self.api_host = self._Add(
        'api_host', argument='api_host',
        callbacks=[lambda: 'https://www.googleapis.com'])
    self.verbosity = self._Add('verbosity', argument='verbosity')
    # pylint: disable=unnecessary-lambda, We don't want to call Metadata()
    # unless we really have to.
    self.project = self._Add(
        'project', argument='project',
        callbacks=[lambda: c_gce.Metadata().Project()])


class _SectionComponentManager(_Section):
  """Contains the properties for the 'component_manager' section."""

  def __init__(self):
    super(_SectionComponentManager, self).__init__('component_manager')
    self.disable_update_check = self._Add('disable_update_check')
    self.snapshot_url = self._Add('snapshot_url')


class _Property(object):
  """An individual property that can be gotten from the properties file.

  Attributes:
    name: str, The name of the property.
    section: str, The name of the section the property appears in in the file.
    argument: str, The name of the command line argument that can be used to
        set this property.
    callbacks: [func], A list of functions to be called, in order, if no value
        is found elsewhere.
  """

  def __init__(self, section, name, argument=None, callbacks=None):
    self.__section = section
    self.__name = name
    self.__argument = argument
    self.__callbacks = callbacks or []

  @property
  def section(self):
    return self.__section

  @property
  def name(self):
    return self.__name

  @property
  def argument(self):
    return self.__argument

  @property
  def callbacks(self):
    return self.__callbacks

  def Get(self):
    """Gets the value for this property.

    Looks first in the environment, then in the workspace config, then in the
    global config, and finally at callbacks.

    Returns:
      str, The value for this property.
    """
    return _GetProperty(self, _PropertiesFile.Load())

  def GetBool(self):
    """Gets the boolean value for this property.

    Looks first in the environment, then in the workspace config, then in the
    global config, and finally at callbacks.

    Returns:
      bool, The boolean value for this property.
    """
    return _GetBoolProperty(self, _PropertiesFile.Load())

  def GetInt(self):
    """Gets the integer value for this property.

    Looks first in the environment, then in the workspace config, then in the
    global config, and finally at callbacks.

    Returns:
      int, The integer value for this property.
    """
    return _GetIntProperty(self, _PropertiesFile.Load())

  def Set(self, value):
    """Sets the value for this property as an environment variable.

    Args:
      value: str/bool, The proposed value for this property.  If None, it is
        removed from the environment.
    """
    if value is not None:
      os.environ[self.EnvironmentName()] = str(value)
    elif self.EnvironmentName() in os.environ:
      del os.environ[self.EnvironmentName()]

  def EnvironmentName(self):
    """Get the name of the environment variable for this property.

    Returns:
      str, The name of the correct environment variable.
    """
    return 'CLOUDSDK_{section}_{name}'.format(
        section=self.__section.upper(),
        name=self.__name.upper(),
    )


VALUES = _Sections()


def PersistProperty(prop, value, force_global=False):
  """Sets the given property in the properties file.

  This function should not generally be used as part of normal program
  execution.  The property files are user editable config files that they should
  control.  This is mostly for initial setup of properties that get set during
  SDK installation.

  Args:
    prop: properties.Property, The property to set.
    value: str, The value to set for the property. If None, the property is
      removed.
    force_global: bool, True to set in the global config file. False to set in
      the local workspace if one is available, defaulting to the global config.

  Raises:
    NotInAWorkspaceError: If you are trying to set a local property but you are
      not in a workspace.
  """
  config_paths = config.Paths()
  properties_file = config_paths.workspace_properties_path
  if force_global or not properties_file:
    properties_file = config_paths.global_properties_path

  parsed_config = ConfigParser.ConfigParser()
  parsed_config.read(properties_file)

  if not parsed_config.has_section(prop.section):
    if value is None:
      return
    parsed_config.add_section(prop.section)

  if value is None:
    parsed_config.remove_option(prop.section, prop.name)
  else:
    parsed_config.set(prop.section, prop.name, str(value))

  properties_dir, unused_name = os.path.split(properties_file)
  files.MakeDir(properties_dir)
  with open(properties_file, 'w') as fp:
    parsed_config.write(fp)


def _GetProperty(prop, properties_file):
  """Gets the given property from the properties file.

  If the property has a designated command line argument and args is provided,
  check args for the value first. If the corresponding environment variable is
  set, use that second. If still nothing, use the callbacks.

  Args:
    prop: properties.Property, The property to get.
    properties_file: _PropertiesFile, An already loaded properties files to use.

  Returns:
    str, The value of the property, or None if it is not set.
  """
  # Providing the argument overrides all.
  args = VALUES.GetArgs()
  if args and prop.argument:
    value = getattr(args, prop.argument, None)
    if value is not None:
      return str(value)

  value = os.environ.get(prop.EnvironmentName(), None)
  if value is not None:
    return str(value)

  value = properties_file.Get(prop)
  if value is not None:
    return str(value)

  # Still nothing, fall back to the callbacks.
  for callback in prop.callbacks:
    value = callback()
    if value is not None:
      return str(value)

  return None


def _GetBoolProperty(prop, properties_file):
  """Gets the given property in bool form.

  Args:
    prop: properties.Property, The property to get.
    properties_file: _PropertiesFile, An already loaded properties files to use.

  Returns:
    bool, The value of the property, or False if it is not set.
  """
  value = _GetProperty(prop, properties_file)
  if value is None:
    return False
  return value.lower() in ['1', 'true', 'on', 'yes']


def _GetIntProperty(prop, properties_file):
  """Gets the given property in integer form.

  Args:
    prop: properties.Property, The property to get.
    properties_file: _PropertiesFile, An already loaded properties files to use.

  Returns:
    int, The integer value of the property, or None if it is not set.
  """
  value = _GetProperty(prop, properties_file)
  if value is None:
    return None
  try:
    return int(value)
  except ValueError:
    raise InvalidValueError(
        'The property [{section}.{name}] must have an integer value: [{value}]'
        .format(section=prop.section, name=prop.name, value=value))


class _PropertiesFile(object):
  """Properties holder for CloudSDK CLIs."""

  @staticmethod
  def Load(global_only=False):
    """Loads the set of properties for the CloudSDK CLIs from files.

    This function will load the properties file, first from the global config
    directory CLOUDSDK_GLOBAL_CONFIG_DIR, and then from the workspace config
    directory CLOUDSDK_WORKSPACE_CONFIG_DIR.

    Args:
      global_only: bool, If True, ignore local workspace properties.

    Returns:
      properties.Properties, The CloudSDK properties.
    """
    config_paths = config.Paths()
    paths = [config_paths.global_properties_path]
    if not global_only:
      workspace_file = config_paths.workspace_properties_path
      if workspace_file:
        paths.append(workspace_file)

    return _PropertiesFile(paths)

  def __init__(self, paths):
    """Creates a new _PropertiesFile and load from the given paths.

    Args:
      paths: [str], List of files to load properties from, in order.
    """
    self._properties = {}

    for properties_path in paths:
      self.__Load(properties_path)

  def __Load(self, properties_path):
    """Loads properties from the given file.

    Overwrites anything already known.

    Args:
      properties_path: str, Path to the file containing properties info.
    """
    parsed_config = ConfigParser.ConfigParser()

    try:
      parsed_config.read(properties_path)
    except ConfigParser.ParsingError as e:
      raise PropertiesParseError(e.message)

    for section in parsed_config.sections():
      if section not in self._properties:
        self._properties[section] = {}
      self._properties[section].update(dict(parsed_config.items(section)))

  def Get(self, prop):
    """Gets the value of the given property.

    Args:
      prop: Property, The property to get.

    Returns:
      str, The value for the given section and property, or None if it is not
        set.
    """
    try:
      return self._properties[prop.section][prop.name]
    except KeyError:
      return None
