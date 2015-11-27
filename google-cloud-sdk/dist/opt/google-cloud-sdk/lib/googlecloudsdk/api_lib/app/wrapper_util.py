# Copyright 2015 Google Inc. All Rights Reserved.

"""Utilities for the dev_appserver.py wrapper script.

Functions for parsing app.yaml files and installing the required components.
"""
import os

from googlecloudsdk.core import log
import yaml

_RUNTIME_COMPONENTS = {
    'java': 'app-engine-java',
    'php55': 'app-engine-php',
}


_WARNING_RUNTIMES = {
    'go': ('The Cloud SDK no longer ships runtimes for Go apps.  Please use '
           'the Go SDK that can be found at: '
           'https://cloud.google.com/appengine/downloads'),
    'php': ('The Cloud SDK no longer ships runtimes for PHP 5.4.  Please set '
            'your runtime to be "php55".')
}

_YAML_FILE_EXTENSIONS = ('.yaml', '.yml')


def GetRuntimes(args):
  """Gets a list of unique runtimes that the user is about to run.

  Args:
    args: A list of arguments (typically sys.argv).

  Returns:
    A set of runtime strings.
  """
  runtimes = set()
  for arg in args:
    # Check all the arguments to see if they're application yaml files.
    if (os.path.isfile(arg) and
        os.path.splitext(arg)[1] in _YAML_FILE_EXTENSIONS):
      with open(arg) as f:
        try:
          info = yaml.safe_load(f)
          # safe_load can return arbitrary objects, we need a dict.
          if not isinstance(info, dict):
            continue
          # Grab the runtime from the yaml, if it exists.
          if 'runtime' in info:
            runtime = info.get('runtime')
            if type(runtime) == str:
              runtimes.add(runtime)
              if runtime in _WARNING_RUNTIMES:
                log.warn(_WARNING_RUNTIMES[runtime])
        except yaml.YAMLError:
          continue
  return runtimes


def GetComponents(runtimes):
  """Gets a list of required components.

  Args:
    runtimes: A list containing the required runtime ids.
  Returns:
    A list of components that must be present.
  """
  # Always install python.
  components = ['app-engine-python']
  for requested_runtime in runtimes:
    for component_runtime, component in _RUNTIME_COMPONENTS.iteritems():
      if component_runtime in requested_runtime:
        components.append(component)
  return components
