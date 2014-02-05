# Copyright 2013 Google Inc. All Rights Reserved.

"""Command to use a calliope tool in an interactive python shell.
"""

import code
import os
import textwrap

from google.cloud.sdk import gcloud
from google.cloud.sdk.calliope import base
from google.cloud.sdk.core import config


class Interactive(base.Command):
  """Use this tool in an interactive python shell.

  Run a Python shell where the gcloud CLI is represented by a collection of
  callable Python objects. For instance, to run the command "gcloud auth login",
  call the function "gcloud.auth.login()".
  """

  def Run(self, args):
    groot = config.GooglePackageRoot()
    libroot, _ = os.path.split(groot)
    libroot = os.path.abspath(libroot)
    # Make the advertized import path more robust to refactoring.
    importpath = gcloud.__name__
    code.interact(
        banner=textwrap.dedent("""\
Google Cloud SDK interactive Python mode.

To use this mode in a Python script, add the following directory to your
PYTHONPATH.
  {pythonpath}

Visit https://developers.google.com/cloud/sdk/interactive for more information.

>>> from {importpath}.gcloud import gcloud
        """.format(
            importpath=importpath,
            pythonpath=libroot)),
        local={'gcloud': self.entry_point})
