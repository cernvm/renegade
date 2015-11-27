# Copyright 2013 Google Inc. All Rights Reserved.
"""Manage parsing resource arguments for the cloud platform.

The Parse() function and Registry.Parse() method are to be used whenever a
Google Cloud Platform API resource is indicated in a command-line argument.
URLs, bare names with hints, and any other acceptable spelling for a resource
will be accepted, and a consistent python object will be returned for use in
code.
"""

import re
import types
import urllib

from googlecloudsdk.core import exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.third_party.apitools.base import py as apitools_base
from googlecloudsdk.third_party.apitools.base.py import util


_COLLECTION_SUB_RE = r'[a-zA-Z_]+(?:\.[a-zA-Z0-9_]+)+'

_COLLECTIONPATH_RE = re.compile(
    r'(?:(?P<collection>{collection})::)?(?P<path>.+)'.format(
        collection=_COLLECTION_SUB_RE))
# The first two wildcards in this are the API and the API's version. The rest
# are parameters into a specific collection in that API/version.
_URL_RE = re.compile(r'(https?://[^/]+/[^/]+/[^/]+/)(.+)')
_METHOD_ID_RE = re.compile(r'(?P<collection>{collection})\.get'.format(
    collection=_COLLECTION_SUB_RE))
_HTTP_RE = re.compile(r'^https?://')


class ClientDef(object):

  def __init__(self, classpath, urls_only=False):
    self.classpath = classpath
    self.urls_only = urls_only

  def Import(self):
    """Imports the client module and returns the client class.

    Returns:
      type: Class that can be used to contruct an instance of the client.
    """
    module, version, class_name = self.classpath.rsplit('.', 2)
    module_obj = __import__(module, fromlist=[version])
    version_obj = getattr(module_obj, version)
    return getattr(version_obj, class_name)


# Map of all known APIs and their clients.
_API_CLIENT_MAP = {
    'autoscaler': [
        ClientDef('googlecloudsdk.third_party.apis.autoscaler.v1beta2.'
                  'AutoscalerV1beta2')
    ],
    'bigquery': [
        ClientDef('googlecloudsdk.third_party.apis.bigquery.v2.BigqueryV2')
    ],
    'cloudresourcemanager': [
        ClientDef('googlecloudsdk.third_party.apis.cloudresourcemanager.'
                  'v1beta1.CloudresourcemanagerV1beta1')
    ],
    'compute': [
        ClientDef('googlecloudsdk.third_party.apis.compute.v1.ComputeV1'),
        ClientDef('googlecloudsdk.third_party.apis.compute.alpha.ComputeAlpha',
                  True),
        ClientDef('googlecloudsdk.third_party.apis.compute.beta.ComputeBeta',
                  True),
    ],
    'clouduseraccounts': [
        ClientDef('googlecloudsdk.third_party.apis.clouduseraccounts.beta.'
                  'ClouduseraccountsBeta'),
        ClientDef('googlecloudsdk.third_party.apis.clouduseraccounts.alpha.'
                  'ClouduseraccountsAlpha', True),
    ],
    'container': [
        ClientDef('googlecloudsdk.third_party.apis.container.v1.ContainerV1'),
    ],
    'dataflow': [
        ClientDef('googlecloudsdk.third_party.apis.dataflow.v1b3.DataflowV1b3')
    ],
    'dataproc': [
        ClientDef('googlecloudsdk.third_party.apis.dataproc.v1beta1.'
                  'DataprocV1beta1')
    ],
    'datastore': [
        ClientDef('googlecloudsdk.third_party.apis.datastore.v1beta3.'
                  'DatastoreV1')
    ],
    'dns': [
        ClientDef('googlecloudsdk.third_party.apis.dns.v1.DnsV1')
    ],
    'genomics': [
        ClientDef('googlecloudsdk.third_party.apis.genomics.v1.GenomicsV1')
    ],
    'logging': [
        ClientDef('googlecloudsdk.third_party.apis.logging.v1beta3.'
                  'LoggingV1beta3')
    ],
    'manager': [
        ClientDef('googlecloudsdk.third_party.apis.manager.v1beta2.'
                  'ManagerV1beta2')
    ],
    'replicapool': [
        ClientDef('googlecloudsdk.third_party.apis.replicapool.v1beta2.'
                  'ReplicapoolV1beta2')
    ],
    'replicapoolupdater': [
        ClientDef('googlecloudsdk.third_party.apis.replicapoolupdater.v1beta1.'
                  'ReplicapoolupdaterV1beta1')
    ],
    'resourceviews': [
        ClientDef('googlecloudsdk.third_party.apis.resourceviews.v1beta1.'
                  'ResourceviewsV1beta1')
    ],
    'sql': [
        ClientDef('googlecloudsdk.third_party.apis.sqladmin.v1beta3.'
                  'SqladminV1beta3')],
    'storage': [
        ClientDef('googlecloudsdk.third_party.apis.storage.v1.StorageV1')
    ],
    'testing': [
        ClientDef('googlecloudsdk.third_party.apis.testing.v1.TestingV1')
    ],
    'toolresults': [
        ClientDef('googlecloudsdk.third_party.apis.toolresults.v1beta3.'
                  'ToolresultsV1beta3')
    ],
}


class Error(Exception):
  """Exceptions for this module."""


class UnknownAPIException(Error):
  """Exception we are trying to register an unknown API."""

  def __init__(self, api):
    super(UnknownAPIException, self).__init__(
        'trying to register unknown API [{0}]'.format(api))


class InvalidEndpointException(Error):
  """Exception for when an API endpoint is malformed."""

  def __init__(self, url):
    super(InvalidEndpointException, self).__init__(
        "URL does not start with 'http://' or 'https://' [{0}]".format(url))


class _ResourceWithoutGetException(Error):
  """Exception for resources with no Get method."""


class BadResolverException(Error):
  """Exception to signal that a resource has no Get method."""

  def __init__(self, param):
    super(BadResolverException, self).__init__(
        'bad resolver for [{param}]'.format(param=param))


class AmbiguousAPIException(Error):
  """Exception for when two APIs try to define a resource."""

  def __init__(self, collection, base_urls):
    super(AmbiguousAPIException, self).__init__(
        'collection [{collection}] defined in multiple APIs: {apis}'.format(
            collection=collection,
            apis=repr(base_urls)))


class UserError(exceptions.Error, Error):
  """Exceptions that are caused by user input."""


class InvalidResourceException(UserError):
  """A collection-path that was given could not be parsed."""

  def __init__(self, line):
    super(InvalidResourceException, self).__init__(
        'could not parse resource: [{line}]'.format(line=line))


class WrongResourceCollectionException(UserError):
  """A command line that was given had the wrong collection."""

  def __init__(self, expected, got, path):
    super(WrongResourceCollectionException, self).__init__(
        'wrong collection: expected [{expected}], got [{got}], for '
        'path [{path}]'.format(
            expected=expected, got=got, path=path))


class WrongFieldNumberException(UserError):
  """A command line that was given had too many fields."""

  def __init__(self, path, ordered_params):
    possibilities = [
        '/'.join([p.upper() for p in ordered_params[1:]]),
        '/'.join([''] + [p.upper() for p in ordered_params]),
    ]

    if len(ordered_params) > 2:
      possibilities.insert(0, ordered_params[-1].upper())

    bits = ', '.join(possibilities)

    msg = ('wrong number of fields: [{got}] does not match any of'
           ' {bits}').format(got=path, bits=bits)
    super(WrongFieldNumberException, self).__init__(msg)


class UnknownFieldException(UserError):
  """A command line that was given did not specify a field."""

  def __init__(self, collection_path, expected):
    super(UnknownFieldException, self).__init__(
        'unknown field [{expected}] in [{path}]'.format(
            expected=expected, path=collection_path))


class UnknownCollectionException(UserError):
  """A command line that was given did not specify a collection."""

  def __init__(self, line):
    super(UnknownCollectionException, self).__init__(
        'unknown collection for [{line}]'.format(line=line))


class InvalidCollectionException(UserError):
  """A command line that was given did not specify a collection."""

  def __init__(self, collection):
    super(InvalidCollectionException, self).__init__(
        'unknown collection [{collection}]'.format(collection=collection))


# TODO(jasmuth): Ensure that all the user-facing error messages help the
# user figure out what to do.


class _ResourceParser(object):
  """Class that turns command-line arguments into a cloud resource message."""

  def __init__(self, client, service, registry):
    """Create a _ResourceParser for a given API and service, and register it.

    Args:
      client: apitools_base.BaseApiClient subclass, The client that handles
          requests to the API.
      service: apitools_base.BaseApiService subclass, The service that manages
          the resource type
      registry: Registry, The registry that this parser should be added to.
    """
    try:
      self.registry = registry
      self.method_config = service.GetMethodConfig('Get')
      self.request_type = service.GetRequestType('Get')
      match = _METHOD_ID_RE.match(self.method_config.method_id)
      if not match:
        raise _ResourceWithoutGetException()
      self.collection = match.group('collection')
      self.client = client
      self.service = service
    except KeyError:
      raise _ResourceWithoutGetException()

  def ParseCollectionPath(self, collection_path, kwargs, resolve):
    """Given a command line and some keyword args, get the resource.

    Args:
      collection_path: str, The human-typed collection-path from the command
          line. Can be None to indicate all params should be taken from kwargs.
      kwargs: {str:(str or func()->str)}, flags (available from context) or
          resolvers that can help parse this resource. If the fields in
          collection-path do not provide all the necessary information,
          kwargs will be searched for what remains.
      resolve: bool, If True, call the resource's .Resolve() method before
          returning, ensuring that all of the resource parameters are defined.
          If False, don't call them, under the assumption that it will be called
          later.

    Returns:
      protorpc.messages.Message, The object containing info about this resource.

    Raises:
      InvalidResourceException: If the provided collection-path is malformed.
      WrongResourceCollectionException: If the collection-path specified the
          wrong collection.
      WrongFieldNumberException: If the collection-path's path provided too many
          fields.
      UnknownFieldException: If the collection-path's path did not provide
          enough fields.
    """
    if collection_path is not None:
      fields = self._GetFieldsForKnownCollection(collection_path)
    else:
      fields = [None] * len(self.method_config.ordered_params)

    # Build up the resource params from kwargs or the fields in the
    # collection-path.
    request = self.request_type()
    for param, field in zip(self.method_config.ordered_params, fields):
      setattr(request, param, field)

    resource = Resource(
        self.collection, request, self.method_config.ordered_params, kwargs,
        collection_path, self)

    if resolve:
      resource.Resolve()

    return resource

  def _GetFieldsForKnownCollection(self, collection_path):
    """Get the ordered fields for the provided collection-path.

    Args:
      collection_path: str, The not-None string provided on the command line.

    Returns:
      [str], The ordered list of URL params corresponding to this parser's
      resource type.

    Raises:
      InvalidResourceException: If the provided collection-path is malformed.
      WrongResourceCollectionException: If the collection-path specified the
          wrong collection.
      WrongFieldNumberException: If the collection-path's path provided too many
          fields.
      UnknownFieldException: If the collection-path's path did not provide
          enough fields.
    """

    match = _COLLECTIONPATH_RE.match(collection_path)
    if not match:
      # Right now it is impossible for this exception to be raised: the
      # regular expression matches all strings. But we will leave it in
      # in case that ever changes.
      raise InvalidResourceException(collection_path)
    collection, path = match.groups()

    if collection and collection != self.collection:
      raise WrongResourceCollectionException(
          expected=self.collection, got=collection, path=collection_path)

    # collection-paths that begin with a slash must have an entry for all
    # ordered params, especially including the project.
    has_project = path.startswith('/')

    # Pending b/17727265, path might contain multiple items after being split
    # on a '/'.
    fields = path.split('/')

    if has_project:
      # first token must be empty, but we already recorded the fact that the
      # next token must be the project
      fields = fields[1:]

    total_param_count = len(self.method_config.ordered_params)

    if has_project and total_param_count != len(fields):
      raise WrongFieldNumberException(
          path=path, ordered_params=self.method_config.ordered_params)

    # Check if there were too many fields provided.
    if len(fields) > total_param_count:
      raise WrongFieldNumberException(
          path=path, ordered_params=self.method_config.ordered_params)

    # If the project is not included, we can either have only one or all-but-one
    # token. So, just simple names or everything that isn't the project.
    if not has_project and len(fields) not in [1, total_param_count - 1]:
      raise WrongFieldNumberException(
          path=path, ordered_params=self.method_config.ordered_params)

    num_missing = total_param_count - len(fields)
    # pad the beginning with Nones so we don't have to count backwards.
    fields = [None] * num_missing + fields

    # Did the user enter a literal empty argument at any stage?
    if '' in fields:
      raise WrongFieldNumberException(
          path=path, ordered_params=self.method_config.ordered_params)

    return fields

  def __str__(self):
    path_str = ''
    for param in self.method_config.ordered_params:
      path_str = '[{path}]/{param}'.format(path=path_str, param=param)
    return '[{collection}::]{path}'.format(
        collection=self.collection, path=path_str)


class Resource(object):
  """Information about a Cloud resource."""

  def __init__(self, collection, request, ordered_params, resolvers,
               collection_path, parser):
    """Create a Resource object that may be partially resolved.

    To allow resolving of unknown params to happen after parse-time, the
    param resolution code is in this class rather than the _ResourceParser
    class.

    Args:
      collection: str, The collection name for this resource.
      request: protorpc.messages.Message (not imported) subclass, An instance
          of a request that can be used to fetch the actual entity in the
          collection.
      ordered_params: [str], The list of parameters that define this resource.
      resolvers: {str:(str or func()->str)}, The resolution functions that can
          be used to fill in values that were not specified in the command line.
      collection_path: str, The original command-line argument used to create
          this Resource.
      parser: _ResourceParser, The parser used to create this Resource.
    """
    self.__collection = collection
    self.__request = request
    self.__name = None
    self.__self_link = None
    self.__ordered_params = ordered_params
    self.__resolvers = resolvers
    self.__collection_path = collection_path
    self.__parser = parser
    for param in ordered_params:
      setattr(self, param, getattr(request, param))

  def Collection(self):
    return self.__collection

  def Name(self):
    self.Resolve()
    return self.__name

  def SelfLink(self):
    self.Resolve()
    return self.__self_link

  def WeakSelfLink(self):
    """Returns a self link containing '*'s for unset parameters."""
    self.WeakResolve()
    return self.__self_link

  def Request(self):
    return self.__request

  def Resolve(self):
    """Resolve unknown parameters for this resource.

    Raises:
      UnknownFieldException: If, after resolving, one of the fields is still
          unknown.
    """
    self.WeakResolve()
    for param in self.__ordered_params:
      if not getattr(self, param, None):
        raise UnknownFieldException(self.__collection_path, param)

  def WeakResolve(self):
    """Attempts to resolve unknown parameters for this resource.

       Unknown parameters are left as None.
    """
    for param in self.__ordered_params:
      if getattr(self, param, None):
        continue

      def ResolveParam(value):
        # This is intended to close over param
        # pylint:disable=cell-var-from-loop
        setattr(self, param, value)
        setattr(self.__request, param, value)
        # pylint:enable=cell-var-from-loop

        # First try the resolvers given to this resource explicitly.
      resolver = self.__resolvers.get(param)
      if resolver:
        if callable(resolver):
          ResolveParam(resolver())
        else:
          ResolveParam(resolver)
        continue

      # Then try the registered defaults.
      api, collection = self.__collection.split('.', 1)
      try:
        value = self.__parser.registry.GetParamDefault(api, collection, param)
        ResolveParam(value)
      except properties.RequiredPropertyError:
        # If property lookup fails, that's ok.  Just don't resolve anything.
        pass

    effective_params = dict(
        [(k, getattr(self, k) or '*') for k in self.__ordered_params])

    self.__self_link = '%s%s' % (
        self.__parser.client.url,
        util.ExpandRelativePath(self.__parser.method_config, effective_params))

    if (self.Collection().startswith('compute.') or
        self.Collection().startswith('clouduseraccounts.') or
        self.Collection().startswith('resourceviews.')):
      # TODO(jasmuth): Unquote URLs for compute, clouduseraccounts, and
      # resourceviews pending b/15425944.
      self.__self_link = urllib.unquote(self.__self_link)

    if self.__ordered_params:
      # The last param is defined to be the resource's "name", and is the only
      # part of the resource that cannot be inferred by a resolver or other
      # context, and MUST be provided in the argument.
      self.__name = getattr(self, self.__ordered_params[-1])

  def __str__(self):
    return self.SelfLink()
    # TODO(jasmuth): Possibly change what is returned, here.
    # path = '/'.join([getattr(self, param) for param in self.__ordered_params])
    # return '{collection}::{path}'.format(
    #     collection=self.__collection, path=path)


def _CopyNestedDictSpine(maybe_dictionary):
  if type(maybe_dictionary) is types.DictType:
    result = {}
    for key, val in maybe_dictionary.iteritems():
      result[key] = _CopyNestedDictSpine(val)
    return result
  else:
    return maybe_dictionary


def _APINameFromURL(url):
  """Get the API name from a resource url.

  Supports four formats:
  http(s)://www.googleapis.com/api/version/resource-path,
  http(s)://www-googleapis-staging.sandbox.google.com/api/version/resource-path,
  http(s)://api.googleapis.com/version/resource-path, and
  http(s)://someotherdoman/api/version/resource-path.

  If there is an api endpoint override defined that maches the url,
  that api name will be returned.

  Args:
    url: str, The resource url.

  Returns:
    str: The API name.
  """
  endpoint_overrides = properties.VALUES.api_endpoint_overrides.AllValues()
  for name, overridden_url in endpoint_overrides.iteritems():
    if overridden_url == url:
      return name

  tokens = _StripUrl(url).split('/')
  domain = tokens[0]
  if ('googleapis' not in domain
      or domain.startswith('www.') or domain.startswith('www-')):
    api_name = tokens[1]
  else:
    api_name = tokens[0].split('.')[0]
  return api_name


def _APINameFromCollection(collection):
  """Get the API name from a collection name like 'api.parents.children'.

  Args:
    collection: str, The collection name.

  Returns:
    str: The API name.
  """
  return collection.split('.')[0]


class Registry(object):
  """Keep a list of all the resource collections and their parsing functions.

  Attributes:
    parsers_by_collection: {str:_ResourceParser}, All the resource parsers
        indexed by their collection.
    parsers_by_url: Deeply-nested dict. The first key is the API's URL root,
        and each key after that is one of the remaining tokens which can be
        either a constant or a parameter name. At the end, a key of None
        indicates the value is a _ResourceParser.
    default_param_funcs: Triply-nested dict. The first key is the param name,
        the second is the api name, and the third is the collection name. The
        value is a function that can be called to find values for params that
        aren't specified already. If the collection key is None, it matches
        all collections.
    registered_apis: {str}, All the apis that have been registered.
  """

  def __init__(self, parsers_by_collection=None, parsers_by_url=None,
               default_param_funcs=None, registered_apis=None):
    self.parsers_by_collection = parsers_by_collection or {}
    self.parsers_by_url = parsers_by_url or {}
    self.default_param_funcs = default_param_funcs or {}
    self.registered_apis = registered_apis or set()

  def _Clone(self):
    return Registry(
        parsers_by_collection=_CopyNestedDictSpine(self.parsers_by_collection),
        parsers_by_url=_CopyNestedDictSpine(self.parsers_by_url),
        default_param_funcs=_CopyNestedDictSpine(self.default_param_funcs),
        registered_apis=set(self.registered_apis))

  def _RegisterAPIByName(self, api_name):
    """Register the given API if it has not been registered already.

    Args:
      api_name: str, The API name.

    Raises:
      UnknownAPIException: If the API to register is not in _API_CLIENT_MAP.
    """
    if api_name in self.registered_apis:
      return

    api_clients = _API_CLIENT_MAP.get(api_name, None)

    if not api_clients:
      raise UnknownAPIException(api_name)

    for api_client in api_clients:
      api_client_class = api_client.Import()
      self._RegisterAPI(api_client_class(get_credentials=False),
                        urls_only=api_client.urls_only)

  def _RegisterAPI(self, api, urls_only=False):
    """Register a generated API with this registry.

    Args:
      api: apitools_base.BaseApiClient, The client for a Google Cloud API.
      urls_only: bool, True if this API should only be used to interpret URLs,
          and not to interpret collection-paths.
    """
    for potential_service in api.__dict__.itervalues():
      if not self._IsApiService(potential_service):
        continue
      try:
        self._RegisterService(api, potential_service, urls_only)
      except _ResourceWithoutGetException:
        pass
    self.registered_apis.add(_APINameFromURL(api.url))

  def _IsApiService(self, service):
    """"Check whether given object is actual service implementation."""
    if isinstance(service, apitools_base.BaseApiService):
      return True
    # TODO(cherba): fix tests not to use unreleased apis, so above condition
    # is sufficient.
    if (not hasattr(service, 'GetMethodConfig') or
        not hasattr(service, 'GetRequestType')):
      return False
    # Check actual name, just in case it is MagicMock.
    for base in service.__class__.__bases__:
      if 'BaseApiService' in base.__name__:
        return True
    return False

  def _RegisterService(self, api, service, urls_only):
    """Register one service for an API with this registry.

    Args:
      api: apitools_base.BaseApiClient, The client for a Google Cloud API.
      service: apitools_base.BaseApiService, the service to be registered.
      urls_only: bool, True if this API should only be used to interpret URLs,
          and not to interpret collection-paths.

    Raises:
      AmbiguousAPIException: If the API defines a collection that has already
          been added.
    """
    parser = _ResourceParser(api, service, self)

    if not urls_only:
      if parser.collection in self.parsers_by_collection:
        urls = [api.url,
                self.parsers_by_collection[parser.collection].client.url]
        raise AmbiguousAPIException(parser.collection, urls)
      self.parsers_by_collection[parser.collection] = parser
    method_config = service.GetMethodConfig('Get')

    # so we don't confuse the splitting
    endpoint = _StripUrl(api.url)

    tokens = endpoint.split('/') + method_config.relative_path.split('/')
    # Build up a search tree to match URLs against URL templates.
    # The tree will branch at each URL segment, where the first segment
    # is the API's base url, and each subsequent segment is a token in
    # the instance's get method's relative path. At the leaf, a key of
    # None indicates that the URL can finish here, and provides the parser
    # for this resource.
    cur_level = self.parsers_by_url
    while tokens:
      token = tokens.pop(0)
      if token not in cur_level:
        cur_level[token] = {}
      cur_level = cur_level[token]
    cur_level[None] = parser

  def _SwitchAPI(self, api):
    """Replace the registration of one version of an API with another.

    This method will remove references to the previous version of the provided
    API from self.parsers_by_collection, but leave self.parsers_by_url intact.

    Args:
      api: apitools_base.BaseApiClient, The client for a Google Cloud API.
    """
    # Clear out the old collections.
    for collection, parser in self.parsers_by_collection.items():
      if parser.client._PACKAGE == api._PACKAGE:  # pylint:disable=protected-access
        del self.parsers_by_collection[collection]
    # TODO(jasmuth): Maybe remove the url parsers as well?

    self._RegisterAPI(api)

  def CloneAndSwitchAPIs(self, *apis):
    """Clone registry and replace any given apis."""
    reg = self._Clone()
    for _, parser in reg.parsers_by_collection.iteritems():
      parser.registry = reg

    def _UpdateParser(dict_or_parser):
      if type(dict_or_parser) is types.DictType:
        for _, val in dict_or_parser.iteritems():
          _UpdateParser(val)
      else:
        dict_or_parser.registry = reg
    _UpdateParser(reg.parsers_by_url)
    for api in apis:
      reg._SwitchAPI(api)  # pylint:disable=protected-access
    return reg

  def SetParamDefault(self, api, collection, param, resolver):
    """Provide a function that will be used to fill in missing values.

    Args:
      api: str, The name of the API that func will apply to.
      collection: str, The name of the collection that func will apploy to. Can
          be None to indicate all collections within the API.
      param: str, The param that can be satisfied with func, if no value is
          provided by the path.
      resolver: str or func()->str, A function that returns a string or raises
          an exception that tells the user how to fix the problem, or the value
          itself.

    Raises:
      ValueError: If api or param is None.
    """
    if not api:
      raise ValueError('provided api cannot be None')
    if not param:
      raise ValueError('provided param cannot be None')
    if param not in self.default_param_funcs:
      self.default_param_funcs[param] = {}
    api_collection_funcs = self.default_param_funcs[param]
    if api not in api_collection_funcs:
      api_collection_funcs[api] = {}
    collection_funcs = api_collection_funcs[api]
    collection_funcs[collection] = resolver

  def GetParamDefault(self, api, collection, param):
    """Return the default value for the specified parameter.

    Args:
      api: str, The name of the API that param is part of.
      collection: str, The name of the collection to query. Can be None to
          indicate all collections within the API.
      param: str, The param to return a default for.

    Raises:
      ValueError: If api or param is None.

    Returns:
      The default value for a parameter or None if there is no default.
    """
    if not api:
      raise ValueError('provided api cannot be None')
    if not param:
      raise ValueError('provided param cannot be None')
    api_collection_funcs = self.default_param_funcs.get(param)
    if not api_collection_funcs:
      return None
    collection_funcs = api_collection_funcs.get(api)
    if not collection_funcs:
      return None
    if collection in collection_funcs:
      resolver = collection_funcs[collection]
    elif None in collection_funcs:
      resolver = collection_funcs[None]
    else:
      return None
    return resolver() if callable(resolver) else resolver

  def ParseCollectionPath(self, collection, collection_path, kwargs,
                          resolve=True):
    """Parse a collection path into a Resource.

    Args:
      collection: str, the name/id for the resource from commandline argument.
      collection_path: str, The human-typed collection-path from the command
          line. Can be None to indicate all params should be taken from kwargs.
      kwargs: {str:(str or func()->str)}, flags (available from context) or
          resolvers that can help parse this resource. If the fields in
          collection-path do not provide all the necessary information,
          kwargs will be searched for what remains.
      resolve: bool, If True, call the resource's .Resolve() method before
          returning, ensuring that all of the resource parameters are defined.
          If False, don't call them, under the assumption that it will be called
          later.
    Returns:
      protorpc.messages.Message, The object containing info about this resource.

    Raises:
      InvalidCollectionException: If the provided collection-path is malformed.

    """
    # Register relevant API if necessary and possible
    self._RegisterAPIByName(_APINameFromCollection(collection))

    if collection not in self.parsers_by_collection:
      raise InvalidCollectionException(collection)
    return self.parsers_by_collection[collection].ParseCollectionPath(
        collection_path, kwargs, resolve)

  def ParseURL(self, url, collection):
    """Parse a URL into a Resource.

    This method does not yet handle "api.google.com" in place of
    "www.googleapis.com/api/version".

    Searches self.parsers_by_url to find a _ResourceParser. The parsers_by_url
    attribute is a deeply nested dictionary, where each key corresponds to
    a URL segment. The first segment is an API's base URL (eg.
    "https://www.googleapis.com/compute/v1/"), and after that it's each
    remaining token in the URL, split on '/'. Then a path down the tree is
    followed, keyed by the extracted pieces of the provided URL. If the key in
    the tree is a literal string, like "project" in .../project/{project}/...,
    the token from the URL must match exactly. If it's a parameter, like
    "{project}", then any token can match it, and that token is stored in a
    dict of params to with the associated key ("project" in this case). If there
    are no URL tokens left, and one of the keys at the current level is None,
    the None points to a _ResourceParser that can turn the collected
    params into a Resource.

    Args:
      url: str, The URL of the resource.
      collection: str, The intended collection for the parsed resource, or None
          if unconstrained.

    Returns:
      Resource, The resource indicated by the provided URL.

    Raises:
      InvalidResourceException: If the provided URL could not be turned into
          a cloud resource.
      WrongResourceCollectionException: If the provided URL points into a
          collection other than the one specified.
    """
    match = _URL_RE.match(url)
    if not match:
      raise InvalidResourceException('unknown API host: [{0}]'.format(url))
    endpoint, path = match.groups()
    tokens = _StripUrl(endpoint).split('/') + path.split('/')
    params = {}

    # Register relevant API if necessary and possible
    self._RegisterAPIByName(_APINameFromURL(url))

    cur_level = self.parsers_by_url
    for token in tokens:
      if token in cur_level:
        # If the literal token is already here, follow it down.
        cur_level = cur_level[token]
      elif len(cur_level) == 1:
        # If the literal token is not here, and there is only one key, it must
        # be a parameter that will be added to the params dict.
        param = cur_level.keys()[0]
        if not param.startswith('{') or not param.endswith('}'):
          raise InvalidResourceException(url)
        # Clean up the provided value
        params[param[1:-1]] = urllib.unquote(token)
        # Keep digging down.
        cur_level = cur_level[param]
      else:
        # If the token we want isn't here, and there isn't a single parameter,
        # the URL we've been given doesn't match anything we know about.
        raise InvalidResourceException(url)
      # Note: This will break if there are multiple parameters that could be
      # specified at a given level. As far as I can tell, this never happens and
      # never should happen. But in theory it's possible so we'll keep an eye
      # out for this issue.

      # No more tokens, so look for a parser.
    if None not in cur_level:
      raise InvalidResourceException(url)
    parser = cur_level[None]
    resource = parser.ParseCollectionPath(None, params, resolve=True)

    if collection and resource.Collection() != collection:
      raise WrongResourceCollectionException(
          expected=collection, got=resource.Collection(), path=url)
    return resource

  def Parse(self, line, params=None, collection=None, resolve=True):
    """Parse a Cloud resource from a command line.

    Args:
      line: str, The argument provided on the command line.
      params: {str:(str or func()->str)}, flags (available from context) or
        resolvers that can help parse this resource. If the fields in
        collection-path do not provide all the necessary information, params
        will be searched for what remains.
      collection: str, The resource's collection, or None if it should be
        inferred from the line.
      resolve: bool, If True, call the resource's .Resolve() method before
          returning, ensuring that all of the resource parameters are defined.
          If False, don't call them, under the assumption that it will be called
          later.

    Returns:
      A resource object.

    Raises:
      InvalidResourceException: If the line is invalid.
      UnknownCollectionException: If no collection is provided or can be
          inferred.
    """
    if line and (line.startswith('https://') or line.startswith('http://')):
      return self.ParseURL(line, collection)
    else:
      if not collection:
        match = _COLLECTIONPATH_RE.match(line)
        if not match:
          raise InvalidResourceException(line)
        collection, unused_path = match.groups()
      if not collection:
        raise UnknownCollectionException(line)

      return self.ParseCollectionPath(collection, line, params or {}, resolve)

  def Create(self, collection, **params):
    """Create a Resource from known collection and params.

    Args:
      collection: str, The name of the collection the resource belongs to.
      **params: {str:str}, The values for each of the resource params.

    Returns:
      Resource, The constructed resource.
    """
    return self.Parse(None, collection=collection, params=params)


# TODO(jasmuth): Deglobalize this object, force gcloud to manage it on its own.
REGISTRY = Registry()


def SetParamDefault(api, collection, param, resolver):
  """Provide a function that will be used to fill in missing values.

  Args:
    api: str, The name of the API that func will apply to.
    collection: str, The name of the collection that func will apply to. Can
        be None to indicate all collections within the API.
    param: str, The param that can be satisfied with func, if no value is
        provided by the path.
    resolver: str or func()->str, A function that returns a string or raises an
        exception that tells the user how to fix the problem, or the value
        itself.
  """
  REGISTRY.SetParamDefault(api, collection, param, resolver)


def GetParamDefault(api, collection, param):
  """Return the default value for the specified parameter.

  Args:
    api: str, The name of the API that param is part of.
    collection: str, The name of the collection to query. Can be None to
        indicate all collections within the API.
    param: str, The param to return a default for.

  Raises:
    ValueError: If api or param is None.

  Returns:
    The default value for a parameter or None if there is no default.
  """
  return REGISTRY.GetParamDefault(api, collection, param)


def _ClearAPIs():
  """For testing, clear out any APIs to start with a clean slate.

  """
  global REGISTRY
  REGISTRY = Registry()


def Parse(line, params=None, collection=None, resolve=True):
  """Parse a Cloud resource from a command line.

  Args:
    line: str, The argument provided on the command line.
    params: {str:str}, The keyword argument context.
    collection: str, The resource's collection, or None if it should be
      inferred from the line.
    resolve: bool, If True, call the resource's .Resolve() method before
        returning, ensuring that all of the resource parameters are defined.
        If False, don't call them, under the assumption that it will be called
        later.

  Returns:
    A resource object.

  Raises:
    InvalidResourceException: If the line is invalid.
    UnknownCollectionException: If no collection is provided or can be inferred.
    WrongProtocolException: If the input was http:// instead of https://
  """
  return REGISTRY.Parse(
      line=line, params=params, collection=collection, resolve=resolve)


def Create(collection, **params):
  """Create a Resource from known collection and params.

  Args:
    collection: str, The name of the collection the resource belongs to.
    **params: {str:str}, The values for each of the resource params.

  Returns:
    Resource, The constructed resource.
  """
  return REGISTRY.Create(collection, **params)


def _StripUrl(url):
  """Strip a http: or https: prefix, then strip leading and trailing slashes."""
  if not _HTTP_RE.match(url):
    raise InvalidEndpointException(url)
  return url[url.index(':') + 1:].strip('/')
