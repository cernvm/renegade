# Copyright 2012 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Helper class for metadata parsing from flags and reading from files."""

from __future__ import with_statement




from google.apputils import app
import gflags as flags


class MetadataFlagsProcessor(object):
  """Helper class for processing flags and building the metadata list."""

  def __init__(self, flag_values):
    flags.DEFINE_multistring('metadata',
                             [],
                             'Metadata to be made available within the VM '
                             'environment via the local metadata server. This '
                             'should be in the form key:value. Metadata keys '
                             'must be unique',
                             flag_values=flag_values)
    flags.DEFINE_multistring('metadata_from_file',
                             [],
                             'Metadata to be made available within the VM '
                             'environment via the local metadata server. The '
                             'value is loaded from a file. This should be in '
                             'the form key:filename. Metadata keys must be '
                             'unique',
                             flag_values=flag_values)
    self._flags = flag_values

  def GatherMetadata(self):
    """Gather the list of metadata dictionaries based on the parsed flag values.

    Returns:
      A list of 'key'/'value' dictionaries defining the metadata.
    Raises:
      app.UsageError: If the parsed flag values are malformed.
    """
    metadata_dict = {}

    def CheckKey(key, metadata_dict):
      """Raises KeyError if key is already in metadata_dict."""
      if key in metadata_dict:
        raise app.UsageError('The key \'%s\' has been specified more than once.'
                             ' Metadata keys must be unique' % key)

    def GatherFromList(metadata_entries, metadata_dict):
      for metadata in metadata_entries:
        if ':' not in metadata:
          raise app.UsageError('Wrong syntax for metadata %s. Use key:value.',
                               metadata)
        key_value = metadata.split(':', 1)
        key = key_value[0]
        CheckKey(key, metadata_dict)
        value = ''
        if len(key_value) > 1:
          value = key_value[1]
          metadata_dict[key] = value

    def GatherFromFiles(metadata_files, metadata_dict):
      for metadata_entry in metadata_files:
        if ':' not in metadata_entry:
          raise app.UsageError('Wrong syntax for metadata_from_file %s. '
                               'Use key:filename.', metadata_entry)
        key_value = metadata_entry.split(':', 1)
        key = key_value[0]
        CheckKey(key, metadata_dict)
        if len(key_value) != 2:
          raise app.UsageError('No metadata file specified for %s.', key)
        with open(key_value[1], 'r') as f:
          metadata_dict[key] = f.read()

    GatherFromList(self._flags.metadata, metadata_dict)
    GatherFromFiles(self._flags.metadata_from_file, metadata_dict)

    result = []
    # We sort here to make testing easier.
    result.extend([{'key': k, 'value': v}
                   for (k, v) in sorted(metadata_dict.items())])
    return result
