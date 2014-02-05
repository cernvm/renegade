#!/bin/sh
#
# Copyright 2013 Google Inc. All Rights Reserved.
#

SCRIPT_LINK=$( readlink "$0" )
CLOUDSDK_ROOT_DIR="$( cd -P "$( dirname "${SCRIPT_LINK:-$0}" )" && pwd -P )"

echo Welcome to the Google Cloud SDK!

if [ -z "$CLOUDSDK_PYTHON" ]; then
  if [ -z $(which python) ]; then
    echo
    echo "To use the Google Cloud SDK, you must have Python installed and on your PATH."
    echo "As an alternative, you may also set the CLOUDSDK_PYTHON environment variable"
    echo "to the location of your Python executable."
    exit 1
  fi
  CLOUDSDK_PYTHON="python"
fi

__cloudsdk_sitepackages=-S
if [ ${CLOUDSDK_PYTHON_SITEPACKAGES} ]; then
  __cloudsdk_sitepackages=
fi

${CLOUDSDK_PYTHON} ${CLOUDSDK_PYTHON_ARGS-$__cloudsdk_sitepackages} ${CLOUDSDK_ROOT_DIR}/bin/bootstrapping/install.py "$@"
exit_code=$?
if [ $exit_code -ne 0 ]; then exit $exit_code; fi
