# Copyright 2013 Google Inc. All Rights Reserved.

"""The calliope CLI/API is a framework for building library interfaces."""

import abc
import argparse
import errno
import imp
import json
import os
import re
import sys
import textwrap
import argcomplete

from google.cloud.sdk.calliope import actions
from google.cloud.sdk.calliope import base
from google.cloud.sdk.calliope import exceptions
from google.cloud.sdk.core import log
from google.cloud.sdk.core import metrics
from google.cloud.sdk.core import properties


class LayoutException(Exception):
  """LayoutException is for problems with module directory structure."""
  pass


class ArgumentException(Exception):
  """ArgumentException is for problems with the provided arguments."""
  pass


class MissingArgumentException(ArgumentException):
  """An exception for when required arguments are not provided."""

  def __init__(self, command_path, missing_arguments):
    """Creates a new MissingArgumentException.

    Args:
      command_path: A list representing the command or group that had the
          required arguments
      missing_arguments: A list of the arguments that were not provided
    """
    message = ('The following required arguments were not provided for command '
               '[{0}]: [{1}]'.format('.'.join(command_path),
                                     ', '.join(missing_arguments)))
    super(MissingArgumentException, self).__init__(message)


class UnexpectedArgumentException(ArgumentException):
  """An exception for when required arguments are not provided."""

  def __init__(self, command_path, unexpected_arguments):
    """Creates a new UnexpectedArgumentException.

    Args:
      command_path: A list representing the command or group that was given the
          unexpected arguments
      unexpected_arguments: A list of the arguments that were not valid
    """
    message = ('The following arguments were unexpected for command '
               '[{0}]: [{1}]'.format('.'.join(command_path),
                                     ', '.join(unexpected_arguments)))
    super(UnexpectedArgumentException, self).__init__(message)


class CalliopeContext(object):
  """CalliopeContext holds parameters for a command's Run function.

  Attributes:
    tool_context: A dictionary containing tool-specific context information
        provided by the tool itself and the command's group ancestors.
    config: A dictionary that is read from a JSON config file before command
        execution, and written back to that same file after command execution.
        DEPRECATED IN FAVOR OF PROPERTIES
    args: The argument namespace returned by argparser, or a construction with
        the same field names.
    entry_point: An UnboundCommandGroup for the program's entry point. For
        example, the 'gcloud' object you get when you import gcloud_api. It can
        be used to invoke any command available to the tool.
    command: The bound Command object used to run this command.
    help_func: A function that takes a list of strings, and prints out the help
        text associated with the command indicated by that list.
  """
  # properties: {str:{str:str}}, Properties dict representing sectioned
  #     key-value pairs

  def __init__(self, tool_context, config, args, entry_point, command,
               help_func):
    self.tool_context = tool_context
    self.args = args
    self.config = config
    self.entry_point = entry_point
    self.command = command
    self.help_func = help_func


class _Args(object):
  """A helper class to convert a dictionary into an object with properties."""

  def __init__(self, args):
    self.__dict__.update(args)

  def __str__(self):
    return '_Args(%s)' % str(self.__dict__)

  def __iter__(self):
    for key, value in sorted(self.__dict__.iteritems()):
      yield key, value


class _ArgumentInterceptor(object):
  """_ArgumentInterceptor intercepts calls to argparse parsers.

  The argparse module provides no public way to access a complete list of
  all arguments, and we need to know these so we can do validation of arguments
  when this library is used in the python interpreter mode. Argparse itself does
  the validation when it is run from the command line.

  Attributes:
    parser: argparse.Parser, The parser whose methods are being intercepted.
    allow_positional: bool, Whether or not to allow positional arguments.
    defaults: {str:obj}, A dict of {dest: default} for all the arguments added.
    required: [str], A list of the dests for all required arguments.
    dests: [str], A list of the dests for all arguments.
    positional_args: [argparse.Action], A list of the positional arguments.
    flag_args: [argparse.Action], A list of the flag arguments.

  Raises:
    ArgumentException: if a positional argument is made when allow_positional
        is false.
  """

  def __init__(self, parser, allow_positional):
    self.parser = parser
    self.allow_positional = allow_positional
    self.defaults = {}
    self.required = []
    self.dests = []
    self.positional_args = []
    self.flag_args = []

  # pylint: disable=g-bad-name
  def add_argument(self, *args, **kwargs):
    """add_argument intercepts calls to the parser to track arguments."""
    # TODO(user): do not allow short-options without long-options.

    # we will choose the first option as the name
    name = args[0]

    positional = not name.startswith('-')
    if positional and not self.allow_positional:
      # TODO(user): More informative error message here about which group
      # the problem is in.
      raise ArgumentException('Illegal positional argument: ' + name)

    if positional and '-' in name:
      raise ArgumentException(
          "Positional arguments cannot contain a '-': " + name)

    dest = kwargs.get('dest')
    if not dest:
      # this is exactly what happens in argparse
      dest = name.lstrip(self.parser.prefix_chars).replace('-', '_')
    default = kwargs.get('default')
    required = kwargs.get('required')

    self.defaults[dest] = default
    if required:
      self.required.append(dest)
    self.dests.append(dest)

    if positional and 'metavar' not in kwargs:
      kwargs['metavar'] = name.upper()

    added_argument = self.parser.add_argument(*args, **kwargs)

    if positional:
      self.positional_args.append(added_argument)
    else:
      self.flag_args.append(added_argument)

    return added_argument

  # pylint: disable=redefined-builtin
  def register(self, registry_name, value, object):
    return self.parser.register(registry_name, value, object)

  def set_defaults(self, **kwargs):
    return self.parser.set_defaults(**kwargs)

  def get_default(self, dest):
    return self.parser.get_default(dest)

  def add_argument_group(self, *args, **kwargs):
    return self.parser.add_argument_group(*args, **kwargs)

  def add_mutually_exclusive_group(self, **kwargs):
    return self.parser.add_mutually_exclusive_group(**kwargs)


class _ConfigHooks(object):
  """This class holds function hooks for context and config loading/saving."""

  def __init__(
      self,
      load_context=None,
      context_filters=None,
      load_config=None,
      save_config=None):
    """Create a new object with the given hooks.

    Args:
      load_context: a function that takes a config object and returns the
          context to be sent to commands.
      context_filters: a list of functions that take (contex, config, args),
          that will be called in order before a command is run. They are
          described in the README under the heading GROUP SPECIFICATION.
      load_config: a zero-param function that returns the configuration
          dictionary to be sent to commands.
      save_config: a one-param function that takes a dictionary object and
          serializes it to a JSON file.
    """
    self.load_context = load_context if load_context else lambda cfg: {}
    self.context_filters = context_filters if context_filters else []
    self.load_config = load_config if load_config else lambda: {}
    self.save_config = save_config if save_config else lambda cfg: None

  def OverrideWithBase(self, group_base):
    """Get a new _ConfigHooks object with overridden functions based on module.

    If module defines any of the function, they will be used instead of what
    is in this object.  Anything that is not defined will use the existing
    behavior.

    Args:
      group_base: The base.Group instance corresponding to the group.

    Returns:
      A new _ConfigHooks object updated with any newly found hooks
    """

    def ContextFilter(context, config, args):
      group = group_base(config=config)
      group.Filter(context, args)
    # We want the new_context_filters to be a completely new list, if there is
    # a change.
    new_context_filters = self.context_filters + [ContextFilter]
    return _ConfigHooks(load_context=self.load_context,
                        context_filters=new_context_filters,
                        load_config=self.load_config,
                        save_config=self.save_config)


class _CommandCommon(object):
  """A base class for _CommandGroup and _Command.

  It is responsible for extracting arguments from the modules and does argument
  validation, since this is always the same for groups and commands.
  """

  def __init__(self, module_dir, module_path, path, config_hooks, help_func,
               parser_group, allow_positional_args):
    """Create a new _CommandCommon.

    Args:
      module_dir: str, The path to the tools directory that this command or
          group lives within. Used to find the command or group's source file.
      module_path: a list of command group names that brought us down to this
          command group or command from the top module directory
      path: similar to module_path, but is the path to this command or group
          with respect to the CLI itself.  This path should be used for things
          like error reporting when a specific element in the tree needs to be
          referenced
      config_hooks: a _ConfigHooks object to use for loading/saving config
      help_func: func([command path]), A function to call with --help.
      parser_group: argparse.Parser, The parser that this command or group will
          live in.
      allow_positional_args: bool, True if this command can have positional
          arguments.
    """
    module = self._GetModuleFromPath(module_path, module_dir)

    self._help_func = help_func
    self._config_hooks = config_hooks

    # pylint:disable=protected-access, The base module is effectively an
    # extension of calliope, and we want to leave _Common private so people
    # don't extend it directly.
    common_type = base._Common.FromModule(module)

    self.name = path[-1]
    # For the purposes of argparse and the help, we should use dashes.
    self.cli_name = self.name.replace('_', '-')
    path[-1] = self.cli_name
    self._module_path = module_path
    self._path = path

    self._common_type = common_type

    if self._common_type.__doc__:
      docstring = self._common_type.__doc__
      # If there is more than one line, the first line is the short help and
      # the rest is the long help.
      docitems = docstring.split('\n', 1)
      self.short_help = textwrap.dedent(docitems[0]).strip()
      if len(docitems) > 1:
        self.long_help = textwrap.dedent(docitems[1]).strip()
      else:
        self.long_help = None
      if not self.long_help:
        # Odd conditionals here in case an empty string is taken from the
        # pydoc.
        self.long_help = self.short_help
    else:
      self.short_help = None
      self.long_help = None

    self._AssignParser(
        parser_group=parser_group,
        help_func=help_func,
        allow_positional_args=allow_positional_args)

  def _AssignParser(self, parser_group, help_func, allow_positional_args):
    """Assign a parser group to model this Command or CommandGroup.

    Args:
      parser_group: argparse._ArgumentGroup, the group that will model this
          command or group's arguments.
      help_func: func([str]), The long help function that is used for --help.
      allow_positional_args: bool, Whether to allow positional args for this
          group or not.

    """
    if not parser_group:
      # This is the root of the command tree, so we create the first parser.
      self._parser = argparse.ArgumentParser(description=self.long_help,
                                             add_help=False)
    else:
      # This is a normal sub group, so just add a new subparser to the existing
      # one.
      self._parser = parser_group.add_parser(
          self.cli_name,
          help=self.short_help,
          description=self.long_help,
          add_help=False)
    self._sub_parser = None

    self._ai = _ArgumentInterceptor(
        parser=self._parser,
        allow_positional=allow_positional_args)
    self._AcquireArgs()

    if help_func:
      self._ai.add_argument(
          '-h', action=actions.ShortHelpAction(
              self, self._ai),
          help='Print this help message and exit.')
      def LongHelp():
        help_func(self._path)
      self._ai.add_argument(
          '--help', action=actions.FunctionExitAction(LongHelp),
          help='Print a detailed help message and exit.')
    else:
      self._ai.add_argument(
          '-h', '--help', action=actions.ShortHelpAction(
              self, self._ai),
          help='Print this help message and exit.')

  def GetPath(self):
    return self._path

  def GetDocString(self):
    if self.long_help:
      return self.long_help
    if self.short_help:
      return self.short_help
    return 'The {name} command.'.format(name=self.name)

  def GetSubCommandHelps(self):
    return {}

  def GetSubGroupHelps(self):
    return {}

  def _GetModuleFromPath(self, module_path, tools_path):
    """Import the module and dig into it to return the namespace we are after.

    Import the module relative to the top level directory.  Then return the
    actual module corresponding to the last bit of the path.

    Args:
      module_path: str, The path
      tools_path: str, The path to the directory from which this module must
          be imported.

    Returns:
      The imported module
    """

    src_dir = os.path.join(tools_path, *module_path[:-1])
    m = imp.find_module(module_path[-1], [src_dir])
    f, file_path, items = m
    module = imp.load_module('.'.join(module_path), f, file_path, items)
    return module

  def _AcquireArgs(self):
    """Call the function to register the arguments for this module."""
    args_func = self._common_type.Args
    if not args_func:
      return
    args_func(self._ai)

  def _GetSubPathsForNames(self, names):
    """Gets a list of (module path, path) for the given list of sub names.

    Args:
      names: The names of the sub groups or commands the paths are for

    Returns:
      A list of tuples of the new (module_path, path) for the given names.
      These terms are that as used by the constructor of _CommandGroup and
      _Command.
    """
    return [(self._module_path + [name], self._path + [name]) for name in names]

  def Parser(self):
    """Return the argparse parser this group is using.

    Returns:
      The argparse parser this group is using
    """
    return self._parser

  def SubParser(self):
    """Gets or creates the argparse sub parser for this group.

    Returns:
      The argparse subparser that children of this group should register with.
          If a sub parser has not been allocated, it is created now.
    """
    if not self._sub_parser:
      self._sub_parser = self._parser.add_subparsers()
    return self._sub_parser

  def CreateNewArgs(self, kwargs, current_args, ignore_unknown):
    """Make a new argument dictionary from default, existing, and new args.

    Args:
      kwargs: The keyword args the user provided for this level
      current_args: The arguments that have previously been collected at other
          levels
      ignore_unknown: If true, filter out any unknown arguments before doing
          the validation.

    Returns:
      A new argument dictionary
    """
    if ignore_unknown:
      # Filter out all the arguments that don't belong to this level.
      filtered_kwargs = {}
      for key, value in kwargs.iteritems():
        if key in self._ai.dests:
          filtered_kwargs[key] = value
      kwargs = filtered_kwargs

    # Make sure the args provided at this level are OK.
    self._ValidateArgs(kwargs)
    # Start with the defaults arguments for this level.
    new_args = dict(self._ai.defaults)
    # Add in anything that was already collected above us in the tree.
    new_args.update(current_args)
    # Add in the args from this invocation.
    new_args.update(kwargs)
    return new_args

  def _ValidateArgs(self, args):
    """Make sure the given arguments are correct for this level.

    Ensures that any required args are provided as well as that no unexpected
    arguments were provided.

    Args:
      args:  A dictionary of the arguments that were provided

    Raises:
      MissingArgumentException: if there are missing required arguments
      UnexpectedArgumentException: if there are unexpected arguments
    """
    missed_args = []
    for required in self._ai.required:
      if required not in args:
        missed_args.append(required)
    if missed_args:
      raise MissingArgumentException(self._path, missed_args)

    unexpected_args = []
    for dest in args:
      if dest not in self._ai.dests:
        unexpected_args.append(dest)
    if unexpected_args:
      raise UnexpectedArgumentException(self._path, unexpected_args)


class _CommandGroup(_CommandCommon):
  """A class to encapsulate a group of commands."""

  def __init__(self, module_dir, module_path, path, parser_group,
               config_hooks, help_func):
    """Create a new command group.

    Args:
      module_dir: always the root of the whole command tree
      module_path: a list of command group names that brought us down to this
          command group from the top module directory
      path: similar to module_path, but is the path to this command group
          with respect to the CLI itself.  This path should be used for things
          like error reporting when a specific element in the tree needs to be
          referenced
      parser_group: the current argparse parser, or None if this is the root
          command group.  The root command group will allocate the initial
          top level argparse parser.
      config_hooks: a _ConfigHooks object to use for loading/saving config
      help_func: func([command path]), A function to call with --help.

    Raises:
      LayoutException: if the module has no sub groups or commands
    """
    super(_CommandGroup, self).__init__(
        module_dir=module_dir,
        module_path=module_path,
        path=path,
        config_hooks=config_hooks,
        help_func=help_func,
        allow_positional_args=False,
        parser_group=parser_group)

    self._module_dir = module_dir

    self._LoadSubGroups()

  def _LoadSubGroups(self):
    """Load all of this group's subgroups and commands."""
    self._config_hooks = self._config_hooks.OverrideWithBase(self._common_type)

    # find sub groups and commands
    self.groups = []
    self.commands = []
    (group_names, command_names) = self._FindSubGroups()
    self.all_sub_names = set(group_names + command_names)
    if not group_names and not command_names:
      raise LayoutException('Group %s has no subgroups or commands'
                            % '.'.join(self._path))

    # recursively create the tree of command groups and commands
    sub_parser = self.SubParser()
    for (new_module_path, new_path) in self._GetSubPathsForNames(group_names):
      self.groups.append(
          _CommandGroup(self._module_dir, new_module_path, new_path,
                        sub_parser, self._config_hooks,
                        help_func=self._help_func))

    for (new_module_path, new_path) in self._GetSubPathsForNames(command_names):
      cmd = _Command(self._module_dir, new_module_path, new_path,
                     self._config_hooks, sub_parser, self._help_func)
      self.commands.append(cmd)

  def GetSubCommandHelps(self):
    return dict((item.cli_name, item.short_help or '')
                for item in self.commands)

  def GetSubGroupHelps(self):
    return dict((item.cli_name, item.short_help or '')
                for item in self.groups)

  def GetHelpFunc(self):
    return self._help_func

  def AddSubGroups(self, groups):
    """Merges other command groups under this one.

    If we load command groups for alternate locations, this method is used to
    make those extra sub groups fall under this main group in the CLI.

    Args:
      groups: Any other _CommandGroup objects that should be added to the CLI
    """
    self.groups.extend(groups)
    for group in groups:
      self.all_sub_names.add(group.name)

  def IsValidSubName(self, name):
    """See if the given name is a name of a registered sub group or command.

    Args:
      name: The name to check

    Returns:
      True if the given name is a registered sub group or command of this
      command group.
    """
    return name in self.all_sub_names

  def _FindSubGroups(self):
    """Final all the sub groups and commands under this group.

    Returns:
      A tuple containing two lists. The first is a list of strings for each
      command group, and the second is a list of strings for each command.

    Raises:
      LayoutException: if there is a command or group with an illegal name.
    """
    location = os.path.join(self._module_dir, *self._module_path)
    items = os.listdir(location)
    groups = []
    commands = []
    items.sort()
    for item in items:
      name, ext = os.path.splitext(item)
      itempath = os.path.join(location, item)

      if ext == '.py':
        if name == '__init__':
          continue
      elif not os.path.isdir(itempath):
        continue

      if re.search('[A-Z]', name):
        raise LayoutException('Commands and groups cannot have capital letters:'
                              ' %s.' % name)

      if not os.path.isdir(itempath):
        commands.append(name)
      else:
        init_path = os.path.join(itempath, '__init__.py')
        if os.path.exists(init_path):
          groups.append(item)
    return groups, commands


class _Command(_CommandCommon):
  """A class that encapsulates the configuration for a single command."""

  def __init__(self, module_dir, module_path, path, config_hooks,
               parser_group, help_func):
    """Create a new command.

    Args:
      module_dir: str, The root of the command tree.
      module_path: a list of command group names that brought us down to this
          command from the top module directory
      path: similar to module_path, but is the path to this command with respect
          to the CLI itself.  This path should be used for things like error
          reporting when a specific element in the tree needs to be referenced
      config_hooks: a _ConfigHooks object to use for loading/saving config
      parser_group: argparse.Parser, The parser to be used for this command.
      help_func: func([str]), Detailed help function.
    """
    super(_Command, self).__init__(
        module_dir=module_dir,
        module_path=module_path,
        path=path,
        config_hooks=config_hooks,
        help_func=help_func,
        allow_positional_args=True,
        parser_group=parser_group)

    self._parser.set_defaults(cmd_func=self.Run, command_path=self._path)

  def Run(self, args, command=None, cli_mode=False):
    """Run this command with the given arguments.

    Args:
      args: The arguments for this command as a namespace.
      command: The bound Command object that is used to run this _Command.
      cli_mode: If True, catch exceptions.ToolException and call Display().

    Returns:
      The object returned by the module's Run() function.

    Raises:
      exceptions.ToolException: if thrown by the Run() function.
    """
    config = self._config_hooks.load_config()

    cached_args = properties.VALUES.SetArgs(args)
    old_verbosity = log.SetVerbosity(
        verbosity=GetVerbosity(cli_mode=cli_mode))

    try:
      tool_context = self._config_hooks.load_context(config)
      for context_filter in self._config_hooks.context_filters:
        context_filter(tool_context, config, args)

      command_instance = self._common_type(
          context=tool_context,
          config=config,
          entry_point=command.EntryPoint(),
          command=command)
      result = command_instance.Run(args)
      self._config_hooks.save_config(config)
      command_instance.Display(args, result)
      return result

    except exceptions.ToolException as exc:
      exc.command_name = '.'.join(self._path)
      log.FileOnlyLogger().exception(exc)
      if cli_mode:
        log.error(exc)
        sys.exit(1)
      else:
        raise
    finally:
      properties.VALUES.SetArgs(cached_args)
      log.SetVerbosity(verbosity=old_verbosity)


class UnboundCommandGroup(object):
  """A class to represent an unbound command group in the REPL.

  Unbound refers to the fact that no arguments have been bound to this command
  group yet.  This object can be called with a set of arguments to set them.
  You can also access any sub group or command of this group as a property if
  this group does not require any arguments at this level.
  """

  def __init__(self, parent_group, group):
    """Create a new UnboundCommandGroup.

    Args:
      parent_group: The BoundCommandGroup this is a descendant of or None if
          this is the root command.
      group: The _CommandGroup that this object is representing
    """
    self._parent_group = parent_group
    self._group = group

    # We change the .__doc__ so that when calliope is used in interpreter mode,
    # the user can inspect .__doc__ and get the help messages provided by the
    # tool creator.
    self.__doc__ = self._group.GetDocString()

  def ParentGroup(self):
    """Gives you the bound command group this group is a descendant of.

    Returns:
      The BoundCommandGroup above this one in the tree or None if we are the top
    """
    return self._parent_group

  def __call__(self, **kwargs):
    return self._BindArgs(kwargs=kwargs, ignore_unknown=False)

  def _BindArgs(self, kwargs, ignore_unknown):
    """Bind arguments to this command group.

    This is called with the kwargs to bind to this command group.  It validates
    that the group has registered the provided args and that any required args
    are provided.

    Args:
      kwargs: The args to bind to this command group.
      ignore_unknown: If true, unknown arguments do not cause validation errors.

    Returns:
      A new BoundCommandGroup with the given arguments
    """
    # pylint: disable=protected-access, We don't want to expose the member or an
    # accessor since this is a user facing class.  These three classes all work
    # as a single unit.
    current_args = self._parent_group._args if self._parent_group else {}
    # Compute the new argument bindings for what was just provided.
    new_args = self._group.CreateNewArgs(
        kwargs=kwargs,
        current_args=current_args,
        ignore_unknown=ignore_unknown)

    bound_group = BoundCommandGroup(self, self._group, self._parent_group,
                                    new_args, kwargs)
    return bound_group

  def __getattr__(self, name):
    """Access sub groups or commands without using () notation.

    Accessing a sub group or command without using the above call, implicitly
    executes the binding with no arguments.  If the context has required
    arguments, this will fail.

    Args:
      name: the name of the attribute to get

    Returns:
      A new UnboundCommandGroup or Command created by binding this command group
      with no arguments.

    Raises:
      AttributeError: if the given name is not a valid sub group or command
    """
    # Map dashes in the CLI to underscores in the API.
    name = name.replace('-', '_')
    if self._group.IsValidSubName(name):
      # Bind zero arguments to this group and then get the name we actually
      # asked for
      return getattr(self._BindArgs(kwargs={}, ignore_unknown=False), name)
    raise AttributeError(name)

  def Name(self):
    return self._group.name

  def HelpFunc(self):
    return self._group.GetHelpFunc()

  def __repr__(self):
    s = ''
    if self._parent_group:
      s += '%s.' % repr(self._parent_group)
    s += self.Name()
    return s


class BoundCommandGroup(object):
  """A class to represent a bound command group in the REPL.

  Bound refers to the fact that arguments have already been provided for this
  command group.  You can access sub groups or commands of this group as
  properties.
  """

  def __init__(self, unbound_group, group, parent_group, args, new_args):
    """Create a new BoundCommandGroup.

    Args:
      unbound_group: the UnboundCommandGroup that this BoundCommandGroup was
          created from.
      group: The _CommandGroup equivalent for this group.
      parent_group: The BoundCommandGroup this is a descendant of
      args: All the default and provided arguments from above and including
          this group.
      new_args: The args used to bind this command group, not including those
          from its parent groups.
    """
    self._unbound_group = unbound_group
    self._group = group
    self._parent_group = parent_group
    self._args = args
    self._new_args = new_args
    # Create attributes for each sub group or command that can come next.
    for group in self._group.groups:
      setattr(self, group.name, UnboundCommandGroup(self, group))
    for command in self._group.commands:
      setattr(self, command.name, Command(self, command))

    self.__doc__ = self._group.GetDocString()

  def __getattr__(self, name):
    # Map dashes in the CLI to underscores in the API.
    fixed_name = name.replace('-', '_')
    if name == fixed_name:
      raise AttributeError
    return getattr(self, fixed_name)

  def UnboundGroup(self):
    return self._unbound_group

  def ParentGroup(self):
    """Gives you the bound command group this group is a descendant of.

    Returns:
      The BoundCommandGroup above this one in the tree or None if we are the top
    """
    return self._parent_group

  def __repr__(self):
    s = ''
    if self._parent_group:
      s += '%s.' % repr(self._parent_group)
    s += self._group.name

    # There are some things in the args which are set by default, like cmd_func
    # and command_path, which should not appear in the repr.
    # pylint:disable=protected-access
    valid_args = self._group._ai.dests
    args = ', '.join(['{0}={1}'.format(arg, repr(val))
                      for arg, val in self._new_args.iteritems()
                      if arg in valid_args])
    if args:
      s += '(%s)' % args
    return s


class Command(object):
  """A class representing a command that can be called in the REPL.

  At this point, contexts about this command have already been created and bound
  to any required arguments for those command groups.  This object can be called
  to actually invoke the underlying command.
  """

  def __init__(self, parent_group, command):
    """Create a new Command.

    Args:
      parent_group: The BoundCommandGroup this is a descendant of
      command: The _Command object to actually invoke
    """
    self._parent_group = parent_group
    self._command = command

    # We change the .__doc__ so that when calliope is used in interpreter mode,
    # the user can inspect .__doc__ and get the help messages provided by the
    # tool creator.
    self.__doc__ = self._command.GetDocString()

  def ParentGroup(self):
    """Gives you the bound command group this group is a descendant of.

    Returns:
      The BoundCommandGroup above this one in the tree or None if we are the top
    """
    return self._parent_group

  def __call__(self, **kwargs):
    return self._Execute(cli_mode=False, kwargs=kwargs)

  def EntryPoint(self):
    """Get the entry point that owns this command."""

    cur = self
    while cur.ParentGroup():
      cur = cur.ParentGroup()
    if type(cur) is BoundCommandGroup:
      cur = cur.UnboundGroup()
    return cur

  def _Execute(self, cli_mode, kwargs):
    """Invoke the underlying command with the given arguments.

    Args:
      cli_mode: If true, run in CLI mode without checking kwargs for validity.
      kwargs: The arguments with which to invoke the command.

    Returns:
      The result of executing the command determined by the command
      implementation
    """
    # pylint: disable=protected-access, We don't want to expose the member or an
    # accessor since this is a user facing class.  These three classes all work
    # as a single unit.
    parent_args = self._parent_group._args if self._parent_group else {}
    new_args = self._command.CreateNewArgs(
        kwargs=kwargs,
        current_args=parent_args,
        ignore_unknown=cli_mode)  # we ignore unknown when in cli mode
    arg_namespace = _Args(new_args)
    return self._command.Run(
        args=arg_namespace,
        command=self,
        cli_mode=cli_mode)

  def __repr__(self):
    s = ''
    if self._parent_group:
      s += '%s.' % repr(self._parent_group)
    s += self._command.name
    return s


class _RunHook(object):
  """Encapsulates a function to be run before or after command execution."""

  def __init__(self, func, include_commands=None, exclude_commands=None):
    """Constructs the hook.

    Args:
      func: function, The no args function to run.
      include_commands: str, A regex for the command paths to run.  If not
        provided, the hook will be run for all commands.
      exclude_commands: str, A regex for the command paths to exclude.  If not
        provided, nothing will be excluded.
    """
    self.__func = func
    self.__include_commands = include_commands if include_commands else '.*'
    self.__exclude_commands = exclude_commands

  def Run(self, command_path):
    """Runs this hook if the filters match the given command.

    Args:
      command_path: str, The calliope command path for the command that was run.

    Returns:
      bool, True if the hook was run, False if it did not match.
    """
    if not re.match(self.__include_commands, command_path):
      return False
    if self.__exclude_commands and re.match(self.__exclude_commands,
                                            command_path):
      return False
    self.__func()
    return True


def GetVerbosity(cli_mode):
  """Gets the verbosity we shoudl use for running a command.

  Args:
    cli_mode: bool, True if this command is being run from the command line,
      False for interactive mode.

  Returns:
    int, The verbosity that should be used for the logger.
  """
  # Global override or value for flag is passed in.
  verbosity = properties.VALUES.core.verbosity.GetInt()
  # Verbosity can be 0 so do explicit None check.
  if verbosity is not None:
    return verbosity

  # Backup verbosity setting for the mode we are in
  core = properties.VALUES.core
  prop = core.cli_verbosity if cli_mode else core.interactive_verbosity
  verbosity = prop.GetInt()
  if verbosity is not None:
    return verbosity

  # Fall back to standard defaults.
  return (log.DEFAULT_CLI_VERBOSITY if cli_mode else
          log.DEFAULT_INTERACTIVE_VERBOSITY)


class CommandLoader(object):
  """A class to encapsulate loading the CLI and bootstrapping the REPL."""

  def __init__(self, name, command_root_directory,
               top_level_command=None, module_directories=None,
               allow_non_existing_modules=False, load_context=None,
               config_file=None, logs_dir=None, version_func=None,
               help_func=None):
    """Initialize Calliope.

    Args:
      name: str, The name of the top level command, used for nice error
        reporting.
      command_root_directory: str, The path to the directory containing the main
        CLI module.
      top_level_command: str, If provided, this command within
        command_root_directory becomes the entire calliope command.  There are
        no groups at all, just this command at the top level.
      module_directories:  An optional dict of additional module directories
        that should be loaded as subgroups under the root command. The key is
        the name that identifies the command group that will be populated by
        the module directory.
      allow_non_existing_modules: True to allow extra module directories to not
        exist, False to raise an exception if a module does not exist.
      load_context: A function that takes the persistent config dict as a
        parameter and returns a context dict, or None for a default which
        always returns {}.
      config_file: str, A path to a config file to use for json config
        loading/saving, or None to disable config.
      logs_dir: str, The path to the root directory to store logs in, or None
        for no log files.
      version_func: func, A function to call for a top-level -v and
        --version flag. If None, no flags will be available.
      help_func: func([command path]), A function to call for in-depth help
        messages. It is passed the set of subparsers used (not including the
        top-level command). After it is called calliope will exit. This function
        will be called when a top-level 'help' command is run, or when the
        --help option is added on to any command.

    Raises:
      LayoutException: If no command root directory is given, or if you provide
        a top level command as well as additional module directories.
    """
    self.name = name

    if not command_root_directory:
      raise LayoutException('You must specify a command root directory.')
    if module_directories and top_level_command:
      raise LayoutException('You may not specify a top level command as well as'
                            ' additional module directories.')

    if not module_directories:
      module_directories = {}

    self.config_file = config_file
    self.config_hooks = _ConfigHooks(
        load_context=load_context,
        load_config=self._CreateLoadConfigFunction(),
        save_config=self._CreateSaveConfigFunction())

    if top_level_command:
      result = self._LoadCLIFromSingleCommand(command_root_directory,
                                              top_level_command,
                                              help_func=help_func)
    else:
      result = self._LoadCLIFromGroups(command_root_directory,
                                       module_directories,
                                       allow_non_existing_modules,
                                       help_func=help_func)

    (self._top_element, self._parser, self._entry_point) = result

    self.__pre_run_hooks = []
    self.__post_run_hooks = []

    if version_func is not None:
      self._parser.add_argument('-v', '--version',
                                action=actions.FunctionExitAction(version_func),
                                help='Print version information.')
    # pylint: disable=protected-access
    self._top_element._ai.add_argument(
        '--verbosity',
        type=int,
        default=None,
        help='Override the default verbosity for this command.  This must be '
        'an integer in the range of 0 to {max} inclusive (Default: {default}).'
        .format(max=log.MAX_VERBOSITY,
                default=log.DEFAULT_CLI_VERBOSITY))

    argcomplete.autocomplete(self._parser)

    # Some initialization needs to happen after autocomplete, so that it doesn't
    # run each time tab is hit.
    log.InitLogging(verbosity=GetVerbosity(cli_mode=False))
    log.AddFileLogging(logs_dir)

  def _CreateLoadConfigFunction(self):
    """Generates a function that loads config from a file if it is set.

    Returns:
      The function to load the configuration or None
    """
    if not self.config_file:
      return None
    def _LoadConfig():
      if os.path.exists(self.config_file):
        with open(self.config_file) as cfile:
          cfgdict = json.load(cfile)
          if cfgdict:
            return cfgdict
      return {}
    return _LoadConfig

  def _CreateSaveConfigFunction(self):
    """Generates a function that saves config from a file if it is set.

    Returns:
      The function to save the configuration or None
    """
    if not self.config_file:
      return None
    def _SaveConfig(cfg):
      """Save the config to the correct file."""
      config_dir, _ = os.path.split(self.config_file)
      try:
        if not os.path.isdir(config_dir):
          os.makedirs(config_dir)
      except OSError as e:
        if e.errno == errno.EEXIST and os.path.isdir(config_dir):
          pass
        else: raise

      with open(self.config_file, 'w') as cfile:
        json.dump(cfg, cfile, indent=2)
        cfile.write('\n')
    return _SaveConfig

  def _LoadCLIFromSingleCommand(self, command_root_directory,
                                top_level_command, help_func=None):
    """Load the CLI from a single command.

    When loaded for a single command, there are no groups and no global
    arguments.  This is use when a calliope command needs to be made a
    standalone command.

    Args:
      command_root_directory: str, The path to the directory containing the main
        CLI module to load.
      top_level_command: str, The command name in the root directory that should
        be made the entrypoint for the CLI.
      help_func: func, If not None, call this function and exit when --help is
        provided.

    Raises:
      LayoutException: If the top level command file does not exist.

    Returns:
      A tuple of the _Command object loaded from the given command, the argparse
      parser for the command tree, and the entry point into the REPL.
    """
    file_path = os.path.join(command_root_directory, top_level_command + '.py')
    if not os.path.isfile(file_path):
      raise LayoutException('The given command does not exist: {}'
                            .format(file_path))
    top_command = _Command(
        command_root_directory, [top_level_command], [self.name],
        self.config_hooks, parser_group=None, help_func=help_func)
    parser = top_command.Parser()
    entry_point = Command(None, top_command)

    return (top_command, parser, entry_point)

  def _LoadCLIFromGroups(self, command_root_directory, module_directories,
                         allow_non_existing_modules, help_func=None):
    """Load the CLI from a command directory.

    Args:
      command_root_directory: str, The path to the directory containing the main
        CLI module to load.
      module_directories:  An optional dict of additional module directories
        that should be loaded as subgroups under the root command. The key is
        the name that identifies the command group that will be populated by
        the module directory.
      allow_non_existing_modules: True to allow extra module directories to not
        exist, False to raise an exception if a module does not exist.
      help_func: func(command path), If not None, call this function and exit
        when --help is provided with any command or group.

    Returns:
      A tuple of the _CommandGroup object loaded from the given command groups,
      the argparse parser for the command tree, and the entry point into the
      REPL.
    """
    top_group = self._LoadGroup(self.name, command_root_directory, None,
                                help_func=help_func)
    sub_parser = top_group.SubParser()

    sub_groups = []
    for module_name, module_directory in module_directories.iteritems():
      group = self._LoadGroup(self.name, module_directory, sub_parser,
                              module_name=module_name,
                              allow_non_existing=allow_non_existing_modules,
                              help_func=help_func)
      if group:
        sub_groups.append(group)

    top_group.AddSubGroups(sub_groups)

    parser = top_group.Parser()
    entry_point = UnboundCommandGroup(None, top_group)
    return (top_group, parser, entry_point)

  def _LoadGroup(self, command_name, module_directory, parser,
                 module_name=None, allow_non_existing=False,
                 help_func=None):
    """Loads a single command group from a directory.

    Args:
      command_name: The name of the top level command the group is being
          registered under.  This is used mainly for error reporting to users
          when we need to identify the group or command where a problem has
          occurred.
      module_directory: The path to the location of the module
      parser: The argparse parser the module should register itself with or None
          if this is the top group.
      module_name: An optional name override for the module. If not set, it will
          default to using the name of the directory containing the module.
      allow_non_existing: True to allow this module to not exist, False to raise
          an exception if it does not exist.
      help_func: func(command path), If not None, call this function and exit
        when --help is provided with any command or group.

    Raises:
      LayoutException: If the module directory does not exist and
      allow_non_existing is False.

    Returns:
      The _CommandGroup object, or None if the module directory does not exist
      and allow_non_existing is True.
    """
    if not os.path.isdir(module_directory):
      if allow_non_existing:
        return None
      raise LayoutException('The given module directory does not exist: {}'
                            .format(module_directory))
    module_root, module = os.path.split(module_directory)
    if not module_name:
      module_name = module
    # If this is the top level, don't register the name of the module directory
    # itself, it should assume the name of the command.  If this is another
    # module directory, its name gets explicitly registered under the root
    # command.
    is_top = not parser  # Parser is undefined only for the top level command.
    path = [command_name] if is_top else [command_name, module_name]
    top_group = _CommandGroup(
        module_root, [module], path, parser, self.config_hooks,
        help_func=help_func)

    return top_group

  def RegisterPreRunHook(self, func,
                         include_commands=None, exclude_commands=None):
    """Register a function to be run before command execution.

    Args:
      func: function, The no args function to run.
      include_commands: str, A regex for the command paths to run.  If not
        provided, the hook will be run for all commands.
      exclude_commands: str, A regex for the command paths to exclude.  If not
        provided, nothing will be excluded.
    """
    hook = _RunHook(func, include_commands, exclude_commands)
    self.__pre_run_hooks.append(hook)

  def RegisterPostRunHook(self, func,
                          include_commands=None, exclude_commands=None):
    """Register a function to be run after command execution.

    Args:
      func: function, The no args function to run.
      include_commands: str, A regex for the command paths to run.  If not
        provided, the hook will be run for all commands.
      exclude_commands: str, A regex for the command paths to exclude.  If not
        provided, nothing will be excluded.
    """
    hook = _RunHook(func, include_commands, exclude_commands)
    self.__post_run_hooks.append(hook)

  def Execute(self, args=None):
    """Execute the CLI tool with the given arguments.

    Args:
      args: The arguments from the command line or None to use sys.argv
    """

    args = self._parser.parse_args(args)
    command_path_string = '.'.join(args.command_path)
    # TODO(user): put a real version here
    metrics.Commands(command_path_string, None)
    path = args.command_path[1:]
    kwargs = args.__dict__

    # Dig down into the groups and commands, binding the arguments at each step.
    # If the path is empty, this means that we have an actual command as the
    # entry point and we don't need to dig down, just call it directly.

    # The command_path will be, eg, ['top', 'group1', 'group2', 'command'], and
    # is set by each _Command when it's loaded from
    # 'tools/group1/group2/command.py'. It corresponds also to the python object
    # built to mirror the command line, with 'top' corresponding to the
    # entry point returned by the EntryPoint() method. Then, in this case, the
    # object found with self.EntryPoint().group1.group2.command is the runnable
    # command being targetted by this operation. The following code segment
    # does this digging and applies the relevant arguments at each step, taken
    # from the argparse results.

    # pylint: disable=protected-access
    cur = self.EntryPoint()
    while path:
      cur = cur._BindArgs(kwargs=kwargs, ignore_unknown=True)
      cur = getattr(cur, path[0])
      path = path[1:]

    old_verbosity = log.SetVerbosity(
        verbosity=GetVerbosity(cli_mode=True))
    try:
      for hook in self.__pre_run_hooks:
        hook.Run(command_path_string)
      cur._Execute(cli_mode=True, kwargs=kwargs)
      for hook in self.__post_run_hooks:
        hook.Run(command_path_string)
    finally:
      log.SetVerbosity(verbosity=old_verbosity)

  def EntryPoint(self):
    """Get the top entry point into the REPL for interactive mode.

    Returns:
      A REPL command group that allows you to bind args and call commands
      interactively in the same way you would from the command line.
    """
    return self._entry_point
