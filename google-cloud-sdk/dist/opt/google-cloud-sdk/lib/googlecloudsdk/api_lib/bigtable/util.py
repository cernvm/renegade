# Copyright 2015 Google Inc. All Rights Reserved.

"""A library that is used to support our commands."""

import json
import re
import time

from googlecloudsdk.calliope import exceptions as sdk_ex
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io
from googlecloudsdk.third_party.apitools.base.py import exceptions as api_ex


def AddClusterIdArgs(parser):
  """Adds --zone and --cluster args to the parser."""
  parser.add_argument(
      '--zone',
      help='ID of the zone where the cluster is located.',
      # TODO(bgt): specify list of zones or not? eg...
      # choices=['europe-west1-c', 'us-central1-b'],
      required=True)
  parser.add_argument(
      'cluster',
      help='Unique ID of the cluster.')


def AddClusterInfoArgs(parser):
  """Adds --name and --nodes args to the parser."""
  parser.add_argument(
      '--description',
      help='Friendly name of the cluster.',
      required=True)
  parser.add_argument(
      '--nodes',
      help='Number of Cloud Bigtable nodes to serve.',
      required=True,
      type=int)
  parser.add_argument(
      '--async',
      help='Return immediately, without waiting for operation to finish.',
      action='store_true')


def ProjectUrl():
  return '/'.join(['projects', properties.VALUES.core.project.Get()])


def ZoneUrl(args):
  return '/'.join([ProjectUrl(), 'zones', args.zone])


def ClusterUrl(args):
  """Creates the canonical URL for a cluster resource."""
  return '/'.join([ZoneUrl(args), 'clusters', args.cluster])


def MakeCluster(args):
  """Creates a dict representing a Cluster proto from user-specified args."""
  cluster = {}
  if args.description:
    cluster['display_name'] = args.description
  if args.nodes:
    cluster['serve_nodes'] = args.nodes
  return cluster


def MapHttpError(f):
  def Func(*args, **kwargs):
    try:
      return f(*args, **kwargs)
    except api_ex.HttpError as e:
      raise sdk_ex.HttpException(json.loads(e.content)['error']['message'])
  return Func


def ExtractZoneAndCluster(cluster_id):
  m = re.match('projects/[^/]+/zones/([^/]+)/clusters/(.*)', cluster_id)
  return m.group(1), m.group(2)


@MapHttpError
def WaitForOp(context, op_id, text):
  cli = context['clusteradmin']
  msg = context['clusteradmin-msgs'].BigtableclusteradminOperationsGetRequest(
      name=op_id)
  with console_io.ProgressTracker(text, autotick=False) as pt:
    while not cli.operations.Get(msg).done:
      pt.Tick()
      time.sleep(0.5)

