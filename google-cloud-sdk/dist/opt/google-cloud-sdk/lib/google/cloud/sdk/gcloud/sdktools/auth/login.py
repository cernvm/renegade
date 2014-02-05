# Copyright 2013 Google Inc. All Rights Reserved.

"""The auth command gets tokens via oauth2."""

import sys
import webbrowser

from google.cloud.sdk.calliope import base
from google.cloud.sdk.calliope import exceptions as c_exc
from google.cloud.sdk.core import log
from google.cloud.sdk.core import properties
from google.cloud.sdk.core.credentials import gce as c_gce
from google.cloud.sdk.core.credentials import store as c_store
from google.cloud.sdk.core.util import console_io


# A list of results for webbrowser.get().name that indicate we should not
# attempt to open a web browser for the user.
_WEBBROWSER_NAMES_BLACKLIST = [
    'www-browser',
]


class Login(base.Command):
  """Get credentials via Google's oauth2 web flow.

  Obtains access credentials for Google Cloud Platform resources, via a web
  flow, and makes them available for all the platform tools in the Cloud SDK. If
  a project is not provided, prompts for a default project.
  """

  @staticmethod
  def Args(parser):
    """Set args for gcloud auth."""

    parser.add_argument(
        '--no-launch-browser',
        action='store_false', default=True, dest='launch_browser',
        help=('Print a URL to be copied instead of launching a web browser.'))
    parser.add_argument(
        '--account', help='Override the account acquired from the web flow.')
    parser.add_argument(
        '--do-not-activate', action='store_true',
        help='Do not set the new credentials as active.')

  @c_exc.RaiseToolExceptionInsteadOf(c_store.Error)
  def Run(self, args):
    """Run the authentication command."""

    # Run the auth flow. Even if the user already is authenticated, the flow
    # will allow him or her to choose a different account.
    try:
      launch_browser = args.launch_browser and not c_gce.Metadata().connected

      # Sometimes it's not possible to launch the web browser. This often
      # happens when people ssh into other machines.
      if launch_browser:
        try:
          browser = webbrowser.get()
          if (hasattr(browser, 'name')
              and browser.name in _WEBBROWSER_NAMES_BLACKLIST):
            launch_browser = False
        except webbrowser.Error:
          launch_browser = False

      creds = c_store.AcquireFromWebFlow(
          launch_browser=launch_browser)
    except c_store.FlowError:
      log.info(
          ('There was a problem with the web flow. Try running with '
           '--no-launch-browser'))
      raise

    account = args.account
    if not account:
      account = creds.token_response['id_token']['email']

    c_store.Store(creds, account)

    if not args.do_not_activate:
      properties.PersistProperty(properties.VALUES.core.account, account)

    project = args.project
    if not project and sys.stdout.isatty():
      project = console_io.PromptResponse(
          ('\nYou can view your existing projects and create new ones in the '
           'Google Developers Console at: https://cloud.google.com/console. '
           'If you have a project ready, you can enter it now.\n\n'
           'Enter your Google Cloud project ID (or leave blank to not set): '))
    if project:
      properties.PersistProperty(properties.VALUES.core.project, project)
    else:
      log.ConsoleWriter().write(
          '\nYou can set your active project at any time by running:\n'
          ' $ gcloud config set project <project id>\n')

    return creds

  def Display(self, unused_args, creds):
    account = creds.token_response['id_token']['email']
    log.ConsoleWriter().write(
        '\nYou are logged in as {account}.\n'.format(account=account))
