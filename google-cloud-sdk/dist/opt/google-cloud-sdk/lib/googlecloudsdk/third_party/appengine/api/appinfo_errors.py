#!/usr/bin/python2.4
#
# Copyright 2006 Google Inc.
# All Rights Reserved.

"""Errors used in the Python appinfo API, used by app developers."""


# WARNING: This file is externally viewable by our users.  All comments from
# this file will be stripped.  The docstrings will NOT.  Do not put sensitive
# information in docstrings.  If you must communicate internal information in
# this source file, please place them in comments only.





class Error(Exception):
  """Base datastore AppInfo type."""


class EmptyConfigurationFile(Error):
  """Tried to load empty configuration file"""


class ModuleAndServiceDefined(Error):
  """Configuration has both 'module' and 'service' instead of just one."""


class MultipleConfigurationFile(Error):
  """Tried to load configuration file with multiple AppInfo objects"""


class MultipleProjectNames(Error):
  """Configuration file had both "application:" and "project:" fields.

  A configuration file can specify the project name using either the old-style
  "application: name" syntax or the newer "project: name" syntax, but not both.
  """


class UnknownHandlerType(Error):
  """Raised when it is not possible to determine URL mapping type."""


class UnexpectedHandlerAttribute(Error):
  """Raised when a handler type has an attribute that it does not use."""


class MissingHandlerAttribute(Error):
  """Raised when a handler is missing an attribute required by its type."""


class MissingURLMapping(Error):
  """Raised when there are no URL mappings in external appinfo."""


class TooManyURLMappings(Error):
  """Raised when there are too many URL mappings in external appinfo."""


class PositionUsedInAppYamlHandler(Error):
  """Raised when position attribute is used in handler in AppInfoExternal."""


class InvalidBuiltinFormat(Error):
  """Raised when the name of the builtin in a list item cannot be identified."""


class MultipleBuiltinsSpecified(Error):
  """Raised when more than one builtin is specified in a single list element."""


class DuplicateBuiltinsSpecified(Error):
  """Raised when a builtin is specified more than once in the same file."""


class BackendNotFound(Error):
  """Raised when a Backend is required but not specified."""


class DuplicateBackend(Error):
  """Raised when a backend is found more than once in 'backends'."""


class MissingApiConfig(Error):
  """Raised if an api_endpoint handler is configured but no api_config."""


class LibrariesNotSupported(Error):
  """Raised if libraries are used outside of classic python27."""


class DuplicateLibrary(Error):
  """Raised when a library is found more than once in 'libraries'."""


class InvalidLibraryVersion(Error):
  """Raised when a library uses a version that isn't supported."""


class InvalidLibraryName(Error):
  """Raised when a library is specified that isn't supported."""


class ThreadsafeWithCgiHandler(Error):
  """Raised when threadsafe is enabled with a CGI handler specified."""


class MissingThreadsafe(Error):
  """Raised when the runtime needs a threadsafe declaration and it's missing."""


class InvalidHttpHeaderName(Error):
  """Raised when an invalid HTTP header name is used.

  This issue arrises what a static handler uses http_headers. For example, the
  following would not be allowed:

    handlers:
    - url: /static
      static_dir: static
      http_headers:
        D@nger: Will Robinson
  """


class InvalidHttpHeaderValue(Error):
  """Raised when an invalid HTTP header value is used.

  This issue arrises what a static handler uses http_headers. For example, the
  following would not be allowed:

    handlers:
    - url: /static
      static_dir: static
      http_headers:
        Some-Unicode: "\u2628"
  """


class ContentTypeSpecifiedMultipleTimes(Error):
  """Raised when mime_type and http_headers specify a mime type.

  N.B. This will be raised even when both fields specify the same content type.
  E.g. the following configuration (snippet) will be rejected:

    handlers:
    - url: /static
      static_dir: static
      mime_type: text/html
      http_headers:
        content-type: text/html

  This only applies to static handlers i.e. a handler that specifies static_dir
  or static_files.
  """


class TooManyHttpHeaders(Error):
  """Raised when a handler specified too many HTTP headers.

  The message should indicate the maximum number of headers allowed.
  """


class TooManyScalingSettingsError(Error):
  """Raised when more than one scaling settings section is present."""


class MissingRuntimeError(Error):
  """Raised when the "runtime" field is omitted for a non-vm."""
