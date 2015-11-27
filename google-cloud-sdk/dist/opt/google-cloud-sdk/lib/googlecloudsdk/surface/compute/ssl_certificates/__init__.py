# Copyright 2014 Google Inc. All Rights Reserved.
"""Commands for reading and manipulating SSL certificates."""

from googlecloudsdk.calliope import base


class SslCertificates(base.Group):
  """List, create, and delete Google Compute Engine SSL certificates."""


SslCertificates.detailed_help = {
    'brief': 'List, create, and delete Google Compute Engine SSL certificates',
}
