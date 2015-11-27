# Copyright 2013 Google Inc. All Rights Reserved.

"""Common functionality to support source fingerprinting."""

import os

from googlecloudsdk.core import log
from googlecloudsdk.core import properties

_PROMPTS_DISABLED_ERROR_MESSAGE = (
    '("disable_prompts" set to true, run "gcloud config set disable_prompts '
    'False" to fix this)')


class Params(object):
  """Parameters passed to the the runtime module Fingerprint() methods.

  Attributes:
    appinfo: (apphosting.api.appinfo.AppInfoExternal or None) The parsed
      app.yaml file for the module if it exists.
    custom: (bool) True if the Configurator should generate a custom runtime.
    deploy: (bool) True if this is happening from deployment.
  """

  def __init__(self, appinfo=None, custom=False, deploy=False):
    self.appinfo = appinfo
    self.custom = custom
    self.deploy = deploy


class Cleaner(object):
  """Class to manage cleanup of a set of files.

  Instances of this class are callable, when called they delete all of the
  files.
  """

  def __init__(self):
    self.__files = []

  def Add(self, filename):
    self.__files.append(filename)

  def HasFiles(self):
    """Returns true if the cleaner has files in it (would delete something)."""
    return self.__files

  def GetFiles(self):
    """Returns the list of files in the cleaner."""
    return self.__files

  def __call__(self):
    for filename in self.__files:
      try:
        os.remove(filename)
      except (OSError, IOError) as ex:
        log.error('Error deleting [%s]: %s', filename, ex)


class Configurator(object):
  """Base configurator class.

  Configurators generate config files for specific classes of runtimes.  They
  are returned by the Fingerprint functions in the runtimes sub-package after
  a successful match of the runtime's heuristics.
  """

  def GenerateConfigs(self):
    """Generate all configuration files for the module.

    Generates config files in the current working directory.

    Returns:
      (callable()) Function that will delete all of the generated files.
    """
    raise NotImplementedError()


def GetNonInteractiveErrorMessage():
  """Returns useful instructions when running non-interactive.

  Certain fingerprinting modules require interactive functionality.  It isn't
  always obvious why gcloud is running in non-interactive mode (e.g. when
  "disable_prompts" is set) so this returns an appropriate addition to the
  error message in these circumstances.

  Returns:
    (str) The appropriate error message snippet.
  """
  if properties.VALUES.core.disable_prompts.GetBool():
    # We add a leading space to the raw message so that it meshes well with
    # its display context.
    return ' ' + _PROMPTS_DISABLED_ERROR_MESSAGE
  else:
    # The other case for non-interactivity (running detached from a terminal)
    # should be obvious.
    return ''
