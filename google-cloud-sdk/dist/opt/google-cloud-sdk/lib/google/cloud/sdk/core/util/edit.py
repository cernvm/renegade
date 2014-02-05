# Copyright 2013 Google Inc. All Rights Reserved.

"""The edit module allows you to edit a text blob without leaving the shell.

When a user needs to edit a blob of text and you don't want to save to
some location, tell them about it, and have the user re-upload the file, this
module can be used to do a quick inline edit.

It will inspect the environment variable EDITOR to see what tool to use
for editing, defaulting to vi. Then, the EDITOR will be opened in the current
terminal; when it exits, the file will be reread and returned with any edits
that the user may have saved while in the EDITOR.
"""


import os
import subprocess
import tempfile


def OnlineEdit(text):
  """Edit will edit the provided text.

  Args:
    text: The initial text to provide for editing.

  Returns:
    The edited text blob, or None if there was a problem with the editor (like
    the user killed it).
  """
  fname = tempfile.NamedTemporaryFile(suffix='.txt').name

  with open(fname, 'w') as f_out:
    f_out.write(text)

  if os.name == 'nt':
    return_code = subprocess.call([fname], shell=True)
  else:
    editor = os.getenv('EDITOR', 'vi')
    return_code = subprocess.call([editor, fname])

  if return_code != 0:
    return None

  with open(fname) as f_done:
    return f_done.read()
