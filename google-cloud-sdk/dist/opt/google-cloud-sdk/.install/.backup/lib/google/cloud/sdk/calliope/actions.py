# Copyright 2013 Google Inc. All Rights Reserved.

"""argparse Actions for use with calliope.
"""

# pylint:disable=g-bad-import-order
import argparse
import StringIO
import sys
import textwrap


def FunctionExitAction(func):
  """Get an argparse.Action that runs the provided function, and exits.

  Args:
    func: func, the function to execute.

  Returns:
    argparse.Action, the action to use.
  """

  class Action(argparse.Action):
    def __init__(self, **kwargs):
      kwargs['nargs'] = 0
      super(Action, self).__init__(**kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
      func()
      sys.exit(0)

  return Action


def _WrapWithPrefix(prefix, message, indent, length, spacing,
                    writer=sys.stdout):
  """Helper function that does two-column writing.

  If the first column is too long, the second column begins on the next line.

  Args:
    prefix: str, Text for the first column.
    message: str, Text for the second column.
    indent: int, Width of the first column.
    length: int, Width of both columns, added together.
    spacing: str, Space to put on the front of prefix.
    writer: file-like, Receiver of the written output.
  """
  def W(s):
    writer.write(s)
  def Wln(s):
    W(s+'\n')

  # Reformat the message to be of rows of the correct width, which is what's
  # left-over from length when you subtract indent. The first line also needs
  # to begin with the indent, but that will be taken care of conditionally.
  message = ('\n%%%ds' % indent % ' ').join(
      textwrap.wrap(message, length - indent))
  if len(prefix) > indent - len(spacing) - 2:
    # If the prefix is too long to fit in the indent width, start the message
    # on a new line after writing the prefix by itself.
    Wln('%s%s' % (spacing, prefix))
    # The message needs to have the first line indented properly.
    W('%%%ds' % indent % ' ')
    Wln(message)
  else:
    # If the prefix fits comfortably within the indent (2 spaces left-over),
    # print it out and start the message after adding enough whitespace to make
    # up the rest of the indent.
    W('%s%s' % (spacing, prefix))
    Wln('%%%ds %%s'
        % (indent - len(prefix) - len(spacing) - 1)
        % (' ', message))


def _PositionalDisplayString(arg):
  message = arg.metavar or arg.dest.upper()
  if arg.nargs == '+':
    message += '+'
  elif arg.nargs == '*' or arg.nargs == argparse.REMAINDER:
    message += '*'
  elif arg.nargs == '?':
    message = '[{msg}]'.format(msg=message)
  return message


def _FlagDisplayString(arg, brief):
  if brief:
    if arg.nargs == 0:
      return arg.option_strings[0]
    return '{flag}={metavar}'.format(
        flag=arg.option_strings[0],
        metavar=arg.metavar or arg.dest.upper())
  else:
    if arg.nargs == 0:
      return ', '.join(arg.option_strings)
    else:
      display_string = ', '.join(
          ['{flag} {metavar}'.format(
              flag=option_string,
              metavar=arg.metavar or arg.dest.upper())
           for option_string in arg.option_strings])
      if not arg.required and arg.default:
        display_string += '; default="{val}"'.format(val=arg.default)
      return display_string

# pylint:disable=pointless-string-statement
""" Some example short help outputs follow.

$ gcloud -h
usage: gcloud            [optional flags] <group | command>
  group is one of        auth | components | config | dns | sql
  command is one of      init | interactive | su | version

Google Cloud Platform CLI/API.

optional flags:
  -h, --help             Print this help message and exit.
  --project PROJECT      Google Cloud Platform project to use for this
                         invocation.
  --quiet, -q            Disable all interactive prompts when running gcloud
                         commands.  If input is required, defaults will be used,
                         or an error will be raised.

groups:
  auth                   Manage oauth2 credentials for the Google Cloud SDK.
  components             Install, update, or remove the tools in the Google
                         Cloud SDK.
  config                 View and edit Google Cloud SDK properties.
  dns                    Manage Cloud DNS.
  sql                    Manage Cloud SQL databases.

commands:
  init                   Initialize a gcloud workspace in the current directory.
  interactive            Use this tool in an interactive python shell.
  su                     Switch the user account.
  version                Print version information for Cloud SDK components.



$ gcloud auth -h
usage: gcloud auth       [optional flags] <command>
  command is one of      activate_git_p2d | activate_refresh_token |
                         activate_service_account | list | login | revoke

Manage oauth2 credentials for the Google Cloud SDK.

optional flags:
  -h, --help             Print this help message and exit.

commands:
  activate_git_p2d       Activate an account for git push-to-deploy.
  activate_refresh_token
                         Get credentials via an existing refresh token.
  activate_service_account
                         Get credentials via the private key for a service
                         account.
  list                   List the accounts for known credentials.
  login                  Get credentials via Google's oauth2 web flow.
  revoke                 Revoke authorization for credentials.



$ gcloud sql instances create -h
usage: gcloud sql instances create
                         [optional flags] INSTANCE

Creates a new Cloud SQL instance.

optional flags:
  -h, --help             Print this help message and exit.
  --authorized-networks AUTHORIZED_NETWORKS
                         The list of external networks that are allowed to
                         connect to the instance. Specified in CIDR notation,
                         also known as 'slash' notation (e.g. 192.168.100.0/24).
  --authorized-gae-apps AUTHORIZED_GAE_APPS
                         List of AppEngine app ids that can access this
                         instance.
  --activation-policy ACTIVATION_POLICY; default="ON_DEMAND"
                         The activation policy for this instance. This specifies
                         when the instance should be activated and is applicable
                         only when the instance state is RUNNABLE. Defaults to
                         ON_DEMAND.
  --follow-gae-app FOLLOW_GAE_APP
                         The AppEngine app this instance should follow. It must
                         be in the same region as the instance.
  --backup-start-time BACKUP_START_TIME
                         Start time for the daily backup configuration in UTC
                         timezone,in the 24 hour format - HH:MM.
  --gce-zone GCE_ZONE    The preferred Compute Engine zone (e.g. us-central1-a,
                         us-central1-b, etc.).
  --pricing-plan PRICING_PLAN, -p PRICING_PLAN; default="PER_USE"
                         The pricing plan for this instance. Defaults to
                         PER_USE.
  --region REGION; default="us-east1"
                         The geographical region. Can be us-east1 or europe-
                         west1. Defaults to us-east1.
  --replication REPLICATION; default="SYNCHRONOUS"
                         The type of replication this instance uses. Defaults to
                         SYNCHRONOUS.
  --tier TIER, -t TIER; default="D0"
                         The tier of service for this instance, for example D0,
                         D1. Defaults to D0.
  --assign-ip            Specified if the instance must be assigned an IP
                         address.
  --enable-bin-log       Specified if binary log must be enabled. If backup
                         configuration is disabled, binary log must be disabled
                         as well.
  --no-backup            Specified if daily backup must be disabled.

positional arguments:
  INSTANCE               Cloud SQL instance ID.


"""



def ShortHelpAction(command, argument_interceptor):
  """Get an argparse.Action that prints a short help.

  Args:
    command: calliope._CommandCommon, The command object that we're helping.
    argument_interceptor: calliope._ArgumentInterceptor, the object that tracks
        all of the flags for this command or group.

  Returns:
    argparse.Action, the action to use.
  """

  line_width = 80
  help_indent = 25

  class Action(argparse.Action):
    def __init__(self, **kwargs):
      kwargs['nargs'] = 0
      super(Action, self).__init__(**kwargs)

    def __call__(self, parser, namespace, values, option_string=None):

      # First, construct the usage.

      command_path = ' '.join(command.GetPath())
      usage_parts = []

      required_messages = []
      optional_messages = []

      # Sorting for consistency and readability.
      for arg in sorted(argument_interceptor.flag_args):
        if arg.help == argparse.SUPPRESS:
          continue
        message = (_FlagDisplayString(arg, False), arg.help or '')
        if not arg.required:
          optional_messages.append(message)
          continue
        required_messages.append(message)
        # and add it to the usage
        msg = _FlagDisplayString(arg, True)
        usage_parts.append(msg)

      if optional_messages:
        # If there are any optional flags, add a simple message to the usage.
        usage_parts.append('[optional flags]')

      positional_messages = []

      # Explicitly not sorting here - order matters.
      for arg in argument_interceptor.positional_args:
        usage_parts.append(_PositionalDisplayString(arg))
        positional_messages.append(
            (_PositionalDisplayString(arg), arg.help or ''))

      group_helps = command.GetSubGroupHelps()
      command_helps = command.GetSubCommandHelps()

      group_messages = [(name, helpmsg)
                        for (name, helpmsg)
                        in sorted(group_helps.iteritems())
                        if helpmsg != argparse.SUPPRESS]
      groups = sorted([key for key, unused_helpmsg in group_messages])
      command_messages = [(name, helpmsg)
                          for (name, helpmsg)
                          in sorted(command_helps.iteritems())
                          if helpmsg != argparse.SUPPRESS]
      commands = sorted([key for key, unused_helpmsg in command_messages])

      all_subtypes = []
      if group_messages:
        all_subtypes.append('group')
      if command_messages:
        all_subtypes.append('command')
      if group_messages or command_messages:
        usage_parts.append('<%s>' % ' | '.join(all_subtypes))

      usage_msg = ' '.join(usage_parts)

      non_option = 'usage: {command} '.format(command=command_path)

      _WrapWithPrefix(non_option, usage_msg, help_indent, line_width,
                      spacing='')

      if group_messages:
        _WrapWithPrefix('group is one of', ' | '.join(
            groups), help_indent, line_width, spacing='  ')
      if command_messages:
        _WrapWithPrefix('command is one of', ' | '.join(
            commands), help_indent, line_width, spacing='  ')
      print

      # Second, print out the long help.

      print '\n'.join(textwrap.wrap(command.long_help, line_width))
      print

      # Third, print out the short help for everything that can come on
      # the command line, grouped into required flags, optional flags,
      # sub groups, sub commands, and positional arguments.

      # This printing is done by collecting a list of rows. If the row is just
      # a string, that means print it without decoration. If the row is a tuple,
      # use _WrapWithPrefix to print that tuple in aligned columns.

      required_flag_msgs = []
      unrequired_flag_msgs = []
      for arg in sorted(argument_interceptor.flag_args):
        if arg.help == argparse.SUPPRESS:
          continue
        usage = _FlagDisplayString(arg, False)
        msg = (usage, arg.help or '')
        if not arg.required:
          unrequired_flag_msgs.append(msg)
        else:
          required_flag_msgs.append(msg)

      def TextIfExists(title, messages):
        if not messages:
          return None
        buf = StringIO.StringIO()
        buf.write('%s\n' % title)
        for (arg, helptxt) in messages:
          _WrapWithPrefix(arg, helptxt, help_indent, line_width,
                          spacing='  ', writer=buf)
        return buf.getvalue()

      all_messages = [
          TextIfExists('required flags:', required_messages),
          TextIfExists('optional flags:', optional_messages),
          TextIfExists('positional arguments:', positional_messages),
          TextIfExists('command groups:', group_messages),
          TextIfExists('commands:', command_messages),
      ]
      sys.stdout.write('\n'.join([msg for msg in all_messages if msg]))

      sys.exit(0)

  return Action
