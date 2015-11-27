# Copyright 2014 Google Inc. All Rights Reserved.
"""Internal base classes for abstracting away common logic."""
import abc
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import request_helper
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.calliope import base
from googlecloudsdk.core.iam import iam_util


# TODO(broudy): Investigate sharing more code with BaseDescriber command.
class BaseGetIamPolicy(base_classes.BaseCommand):
  """Base class for getting the Iam Policy for a resource."""

  __metaclass__ = abc.ABCMeta

  @staticmethod
  def Args(parser, resource=None, list_command_path=None):
    BaseGetIamPolicy.AddArgs(parser, resource, list_command_path)

  @staticmethod
  def AddArgs(parser, resource=None, list_command_path=None):
    """Add required flags for set Iam policy."""
    parser.add_argument(
        'name',
        metavar='NAME',
        completion_resource=resource,
        list_command_path=list_command_path,
        help='The resources whose IAM policy to fetch.')

  @property
  def method(self):
    return 'GetIamPolicy'

  def ScopeRequest(self, ref, request):
    """Adds a zone or region to the request object if necessary."""

  def SetResourceName(self, ref, request):
    """Adds a the name of the resource to the request object."""
    resource_name = self.service.GetMethodConfig(self.method).ordered_params[-1]
    setattr(request, resource_name, ref.Name())

  @abc.abstractmethod
  def CreateReference(self, args):
    pass

  def Run(self, args):

    ref = self.CreateReference(args)
    request_class = self.service.GetRequestType(self.method)
    request = request_class(project=self.project)
    self.ScopeRequest(ref, request)
    self.SetResourceName(ref, request)

    get_policy_request = (self.service, self.method, request)
    errors = []
    objects = request_helper.MakeRequests(
        requests=[get_policy_request],
        http=self.http,
        batch_url=self.batch_url,
        errors=errors,
        custom_get_requests=None)

    # Converting the objects genrator to a list triggers the
    # logic that actually populates the errors list.
    resources = list(objects)
    if errors:
      utils.RaiseToolException(
          errors,
          error_message='Could not fetch resource:')

    # TODO(broudy): determine how this output should look when empty.

    # GetIamPolicy always returns either an error or a valid policy.
    # If no policy has been set it returns a valid empty policy (just an etag.)
    # It is not possible to have multiple policies for one resource.
    return resources[0]


def GetIamPolicyHelp(resource_name):
  return {
      'brief': 'Get the IAM Policy for a Google Compute Engine {0}.'.format(
          resource_name),
      'DESCRIPTION': """\
          *{{command}}* displays the Iam Policy associated with a Google Compute
          Engine {0} in a project.
          """.format(resource_name)}


class ZonalGetIamPolicy(BaseGetIamPolicy):
  """Base class for zonal iam_get_policy commands."""

  @staticmethod
  def Args(parser, resource=None, command=None):
    BaseGetIamPolicy.AddArgs(parser, resource, command)
    utils.AddZoneFlag(
        parser,
        resource_type='resource',
        operation_type='fetch')

  def CreateReference(self, args):
    return self.CreateZonalReference(args.name, args.zone)

  def ScopeRequest(self, ref, request):
    request.zone = ref.zone


def GenerateGetIamPolicy(
    command_type, resource_type, detailed_help,
    parser_resource=None, parser_command=None):
  """Function for generating GetIamPolicy commands."""

  @base.Hidden
  @base.ReleaseTracks(base.ReleaseTrack.ALPHA)
  class GetIamPolicy(command_type):
    """Command to get IAM policy for a resource."""

    @staticmethod
    def Args(parser):
      command_type.Args(parser, parser_resource, parser_command)

    @property
    def service(self):
      return getattr(self.compute, resource_type)

    @property
    def resource_type(self):
      return resource_type

  GetIamPolicy.detailed_help = GetIamPolicyHelp(detailed_help)
  return GetIamPolicy


class RegionalGetIamPolicy(BaseGetIamPolicy):
  """Base class for regional iam_get_policy commands."""

  @staticmethod
  def Args(parser, resource=None, command=None):
    BaseGetIamPolicy.AddArgs(parser, resource, command)
    utils.AddRegionFlag(
        parser,
        resource_type='resource',
        operation_type='fetch')

  def CreateReference(self, args):
    return self.CreateRegionalReference(args.name, args.region)

  def ScopeRequest(self, ref, request):
    request.region = ref.region


class GlobalGetIamPolicy(BaseGetIamPolicy):
  """Base class for global iam_get_policy commands."""

  def CreateReference(self, args):
    return self.CreateGlobalReference(args.name)


class BaseSetIamPolicy(base_classes.BaseCommand):
  """Base class for setting the Iam Policy for a resource."""

  __metaclass__ = abc.ABCMeta

  @staticmethod
  def Args(parser, resource=None, list_command_path=None):
    BaseSetIamPolicy.AddArgs(parser, resource, list_command_path)

  @staticmethod
  def AddArgs(parser, resource=None, list_command_path=None):
    """Add required flags for set Iam policy."""
    parser.add_argument(
        'name',
        metavar='NAME',
        completion_resource=resource,
        list_command_path=list_command_path,
        help='The resources whose IAM policy to set.')

    policy_file = parser.add_argument(
        'policy_file',
        metavar='POLICY_FILE',
        help='Path to a local JSON formatted file contining a valid policy.')
    policy_file.detailed_help = """\
        Path to a local JSON formatted file containing a valid policy.
        """
    # TODO(broudy): fill in detailed help.

  @property
  def method(self):
    return 'SetIamPolicy'

  def ScopeRequest(self, ref, request):
    """Adds a zone or region to the request object if necessary."""

  def SetResourceName(self, ref, request):
    """Adds a the name of the resource to the request object."""
    resource_name = self.service.GetMethodConfig(self.method).ordered_params[-1]
    setattr(request, resource_name, ref.Name())

  @abc.abstractmethod
  def CreateReference(self, args):
    pass

  def Run(self, args):

    policy = iam_util.ParseJsonPolicyFile(
        args.policy_file, self.messages.Policy)

    ref = self.CreateReference(args)
    request_class = self.service.GetRequestType(self.method)
    request = request_class(project=self.project)
    self.ScopeRequest(ref, request)
    self.SetResourceName(ref, request)
    request.policy = policy

    set_policy_request = (self.service, self.method, request)
    errors = []
    objects = request_helper.MakeRequests(
        requests=[set_policy_request],
        http=self.http,
        batch_url=self.batch_url,
        errors=errors,
        custom_get_requests=None)

    # Converting the objects genrator to a list triggers the
    # logic that actually populates the errors list.
    resources = list(objects)
    if errors:
      utils.RaiseToolException(
          errors,
          error_message='Could not fetch resource:')

    # TODO(broudy): determine how this output should look when empty.

    # SetIamPolicy always returns either an error or the newly set policy.
    # If the policy was just set to the empty policy it returns a valid empty
    # policy (just an etag.)
    # It is not possible to have multiple policies for one resource.
    return resources[0]


def SetIamPolicyHelp(resource_name):
  return {
      'brief': 'Set the IAM Policy for a Google Compute Engine {0}.'.format(
          resource_name),
      'DESCRIPTION': """\
        *{{command}}* sets the Iam Policy associated with a Google Compute
        Engine {0} in a project.
        """.format(resource_name)}


class ZonalSetIamPolicy(BaseSetIamPolicy):
  """Base class for zonal iam_get_policy commands."""

  @staticmethod
  def Args(parser, resource=None, command=None):
    BaseSetIamPolicy.AddArgs(parser, resource, command)
    utils.AddZoneFlag(
        parser,
        resource_type='resource',
        operation_type='fetch')

  def CreateReference(self, args):
    return self.CreateZonalReference(args.name, args.zone)

  def ScopeRequest(self, ref, request):
    request.zone = ref.zone


def GenerateSetIamPolicy(
    command_type, resource_type, detailed_help,
    parser_resource=None, parser_command=None):
  """Function for generating SetIamPolicy commands."""

  @base.Hidden
  @base.ReleaseTracks(base.ReleaseTrack.ALPHA)
  class SetIamPolicy(command_type):
    """Set the IAM Policy for a Google Compute Engine resource."""

    @staticmethod
    def Args(parser):
      command_type.Args(parser, parser_resource, parser_command)

    @property
    def service(self):
      return getattr(self.compute, resource_type)

    @property
    def resource_type(self):
      return resource_type

  SetIamPolicy.detailed_help = SetIamPolicyHelp(detailed_help)
  return SetIamPolicy


class RegionalSetIamPolicy(BaseSetIamPolicy):
  """Base class for regional iam_get_policy commands."""

  @staticmethod
  def Args(parser, resource=None, command=None):
    BaseSetIamPolicy.AddArgs(parser, resource)
    utils.AddRegionFlag(
        parser,
        resource_type='resource',
        operation_type='fetch')

  def CreateReference(self, args):
    return self.CreateRegionalReference(args.name, args.region)

  def ScopeRequest(self, ref, request):
    request.region = ref.region


class GlobalSetIamPolicy(BaseSetIamPolicy):
  """Base class for global iam_get_policy commands."""

  def CreateReference(self, args):
    return self.CreateGlobalReference(args.name)
