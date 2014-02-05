# Copyright 2013 Google Inc. All Rights Reserved.

"""Prepare the user to push to git repos for deployment."""

import textwrap

from google.cloud.sdk.calliope import base
from google.cloud.sdk.calliope import exceptions as c_exc
from google.cloud.sdk.core import log
from google.cloud.sdk.core import properties
from google.cloud.sdk.core.credentials import gitp2d
from google.cloud.sdk.core.credentials import store as c_store


class ActivateGitP2D(base.Command):
  """Enable access to Google-hosted code repositories.

  Edit $HOME/.netrc (or $HOME/_netrc on Windows), adding an entry that
  authenticates against code.google.com using the provided user and a valid
  refresh token. Since git looks at a single file, access can only be enabled
  for one account at a time. To change the account with access, run this command
  again.
  """

  @staticmethod
  def Args(parser):
    """Set args for gcloud auth activate-refresh-token."""
    parser.add_argument(
        'account', help='The account to be used for accessing repositories.',
        nargs='?')
    parser.add_argument(
        '--netrc', help='Alternative netrc file to use.')

  @c_exc.RaiseToolExceptionInsteadOf(c_store.Error)
  def Run(self, args):
    """Run the authentication command."""

    if args.account:
      account = args.account
    else:
      account = properties.VALUES.core.account.Get()
    creds = c_store.Load(account=account)
    if not creds.refresh_token:
      raise c_exc.InvalidArgumentException(
          'account', 'Unable to get refresh token from account.')

    gitp2d.ActivateGitP2D(account, creds, args.netrc)

    return account

  def Display(self, unused_args, result):
    log.Print('\n'.join(textwrap.wrap(
        """{account} now has access to Google-hosted code repositories. Only
        one account can have access at a time. To give another account access,
        run this command again.
        """.format(account=result), 80)))
