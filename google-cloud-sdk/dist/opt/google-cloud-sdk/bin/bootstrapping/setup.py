# Copyright 2013 Google Inc. All Rights Reserved.

"""Does some initial setup and checks for all the bootstrapping scripts."""


import os
import sys

# If we're in a virtualenv, always import site packages. Also, upon request.
import_site_packages = (os.environ.get('CLOUDSDK_PYTHON_SITEPACKAGES') or
                        os.environ.get('VIRTUAL_ENV'))

if import_site_packages:
  # pylint:disable=unused-import
  # pylint:disable=g-import-not-at-top
  import site

# Put Cloud SDK libs on the path
lib_dir = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), '..', '..', 'lib')
sys.path = [lib_dir] + sys.path
# Add this so that all subprocess will have this on the path as well
python_path = os.environ.get('PYTHONPATH')
if python_path:
  os.environ['PYTHONPATH'] = os.pathsep.join([lib_dir, python_path])
else:
  os.environ['PYTHONPATH'] = lib_dir


# This strange import below ensures that the correct 'google' is imported. We
# reload after sys.path and PYTHONPATH are updated, so we know if will find our
# google before any other.
# pylint:disable=g-import-not-at-top, must follow sys.path and PYTHONPATH logic.
import google
reload(google)


# pylint: disable=g-import-not-at-top
from google.cloud.sdk.core.util import platforms


MIN_REQUIRED_VERSION = (2, 6)


def CheckPythonVersion():
  if not hasattr(sys, 'version_info'):
    sys.stderr.write('ERROR: Your current version of Python is not supported '
                     'by the Google Cloud SDK.  Please upgrade to Python '
                     '%s.%s or greater.\n'
                     % (str(MIN_REQUIRED_VERSION[0]),
                        str(MIN_REQUIRED_VERSION[1])))
    sys.exit(1)

  version_tuple = sys.version_info[:2]
  if version_tuple < MIN_REQUIRED_VERSION:
    sys.stderr.write('ERROR: Python %s.%s is not supported by the Google Cloud '
                     'SDK. Please upgrade to version %s.%s or greater.\n'
                     % (str(version_tuple[0]), str(version_tuple[1]),
                        str(MIN_REQUIRED_VERSION[0]),
                        str(MIN_REQUIRED_VERSION[1])))
    sys.exit(1)


def CheckCygwin():
  if (platforms.OperatingSystem.Current() == platforms.OperatingSystem.CYGWIN
      and platforms.Architecture.Current() == platforms.Architecture.x86_64):
    sys.stderr.write('ERROR: Cygwin 64 bit is not supported by the Google '
                     'Cloud SDK.  Please use a 32 bit version of Cygwin.')
    sys.exit(1)


# Add more methods to this list for universal checks that need to be performed
def DoAllRequiredChecks():
  CheckPythonVersion()
  CheckCygwin()

DoAllRequiredChecks()
