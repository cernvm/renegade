# Copyright 2014 Google Inc. All Rights Reserved.

"""List clusters command."""
from googlecloudsdk.api_lib.container import util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.third_party.apitools.base import py as apitools_base


class List(base.Command):
  """List existing clusters for running containers."""

  @staticmethod
  def Args(parser):
    """Register flags for this command.

    Args:
      parser: An argparse.ArgumentParser-like object. It is mocked out in order
          to capture some information, but behaves like an ArgumentParser.
    """
    pass

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Returns:
      Some value that we want to have printed later.
    """
    adapter = self.context['api_adapter']

    project = properties.VALUES.core.project.Get(required=True)
    zone = None
    if args.zone:
      zone = adapter.registry.Parse(args.zone, collection='compute.zones').zone

    try:
      return adapter.ListClusters(project, zone)
    except apitools_base.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))

  def Display(self, args, result):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    self.context['api_adapter'].PrintClusters(result.clusters)
