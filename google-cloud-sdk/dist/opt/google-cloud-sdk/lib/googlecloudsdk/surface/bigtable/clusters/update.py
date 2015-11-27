# Copyright 2015 Google Inc. All Rights Reserved.

"""bigtable clusters update command."""

from googlecloudsdk.api_lib.bigtable import util
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log


class UpdateCluster(base.Command):
  """Update a Bigtable cluster's friendly name and serving nodes."""

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    util.AddClusterIdArgs(parser)
    util.AddClusterInfoArgs(parser)

  @util.MapHttpError
  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Returns:
      Some value that we want to have printed later.
    """
    cli = self.context['clusteradmin']
    msg = self.context['clusteradmin-msgs'].Cluster(
        name=util.ClusterUrl(args),
        displayName=args.description,
        serveNodes=args.nodes)
    result = cli.projects_zones_clusters.Update(msg)
    if not args.async:
      util.WaitForOp(
          self.context,
          result.currentOperation.name,
          'Updating cluster')
    return result

  def Display(self, args, result):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    # Always use this log module for printing (never use print directly).
    # This allows us to control the verbosity of commands in a global way.
    writer = log.out
    writer.Print('Cluster [{0}] in zone [{1}] update{2}.'.format(
        args.cluster, args.zone, ' in progress' if args.async else 'd'))

