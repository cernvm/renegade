# Copyright 2015 Google Inc. All Rights Reserved.

"""Utilities for working with long running operations go/long-running-operation.
"""

import json
import time

from googlecloudsdk.api_lib.app.api import constants
from googlecloudsdk.api_lib.app.api import requests
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.third_party.apitools.base.py import encoding


class OperationError(exceptions.Error):
  pass


class OperationTimeoutError(exceptions.Error):
  pass


def WaitForOperation(operation_service, operation,
                     max_retries=None,
                     retry_interval=None):
  """Wait until the operation is complete or times out.

  Args:
    operation_service: The apitools service type for operations
    operation: The operation resource to wait on
    max_retries: Maximum number of times to poll the operation
    retry_interval: Frequency of polling
  Returns:
    The operation resource when it has completed
  Raises:
    OperationTimeoutError: when the operation polling times out
    OperationError: when the operation completed with an error
  """
  if max_retries is None:
    max_retries = constants.DEFAULT_OPERATION_MAX_RETRIES
  if retry_interval is None:
    retry_interval = constants.DEFAULT_OPERATION_RETRY_INTERVAL

  completed_operation = _PollUntilDone(operation_service, operation,
                                       max_retries, retry_interval)
  if not completed_operation:
    raise OperationTimeoutError(('Operation [{0}] timed out. This operation '
                                 'may still be underway.').format(
                                     operation.name))

  if completed_operation.error:
    raise OperationError(requests.ExtractErrorMessage(
        encoding.MessageToPyValue(completed_operation.error)))

  return completed_operation


def _PollUntilDone(operation_service, operation, max_retries,
                   retry_interval):
  """Polls the operation resource until it is complete or times out."""
  if operation.done:
    return operation

  request_type = operation_service.GetRequestType('Get')
  request = request_type(name=operation.name)

  for _ in xrange(max_retries):
    operation = requests.MakeRequest(operation_service.Get, request)
    if operation.done:
      log.debug('Operation [{0}] complete. Result: {1}'.format(
          operation.name,
          json.dumps(encoding.MessageToDict(operation), indent=4)))
      return operation
    log.debug('Operation [{0}] not complete. Waiting {1}s.'.format(
        operation.name, retry_interval))
    time.sleep(retry_interval)

  return None
