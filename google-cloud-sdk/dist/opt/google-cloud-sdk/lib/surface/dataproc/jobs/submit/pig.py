# Copyright 2015 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Submit a Pig job to a cluster."""

from apitools.base.py import encoding

from googlecloudsdk.api_lib.dataproc import base_classes
from googlecloudsdk.calliope import arg_parsers


class Pig(base_classes.JobSubmitter):
  """Submit a Pig job to a cluster."""

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To submit a Pig job with a local script, run:

            $ {command} --cluster my_cluster --file my_queries.pig

          To submit a Pig job with inline queries, run:

            $ {command} --cluster my_cluster -e "LNS = LOAD 'gs://my_bucket/my_file.txt' AS (line)" -e "WORDS = FOREACH LNS GENERATE FLATTEN(TOKENIZE(line)) AS word" -e "GROUPS = GROUP WORDS BY word" -e "WORD_COUNTS = FOREACH GROUPS GENERATE group, COUNT(WORDS)" -e "DUMP WORD_COUNTS"
          """,
  }

  @staticmethod
  def Args(parser):
    super(Pig, Pig).Args(parser)
    parser.add_argument(
        '--execute', '-e',
        metavar='QUERY',
        dest='queries',
        action='append',
        default=[],
        help='A Pig query to execute as part of the job.')
    parser.add_argument(
        '--file', '-f',
        help='HCFS URI of file containing Pig script to execute as the job.')
    parser.add_argument(
        '--jars',
        type=arg_parsers.ArgList(),
        metavar='JAR',
        default=[],
        help=('Comma separated list of jar files to be provided to '
              'Pig and MR. May contain UDFs.'))
    parser.add_argument(
        '--params',
        type=arg_parsers.ArgDict(),
        metavar='PARAM=VALUE',
        help='A list of key value pairs to set variables in the Pig queries.')
    parser.add_argument(
        '--properties',
        type=arg_parsers.ArgDict(),
        metavar='PROPERTY=VALUE',
        help='A list of key value pairs to configure Pig.')
    parser.add_argument(
        '--continue-on-failure',
        action='store_true',
        help='Whether to continue if a single query fails.')
    parser.add_argument(
        '--driver-log-levels',
        type=arg_parsers.ArgDict(),
        metavar='PACKAGE=LEVEL',
        help=('A list of package to log4j log level pairs to configure driver '
              'logging. For example: root=FATAL,com.example=INFO'))

  def PopulateFilesByType(self, args):
    # TODO(user): Replace with argument group.
    if not args.queries and not args.file:
      raise ValueError('Must either specify --execute or --file.')
    if args.queries and args.file:
      raise ValueError('Cannot specify both --execute and --file.')

    self.files_by_type.update({
        'jars': args.jars,
        'file': args.file})

  def ConfigureJob(self, job, args):
    messages = self.context['dataproc_messages']

    log_config = self.BuildLoggingConfig(args.driver_log_levels)
    pig_job = messages.PigJob(
        continueOnFailure=args.continue_on_failure,
        jarFileUris=self.files_by_type['jars'],
        queryFileUri=self.files_by_type['file'],
        loggingConfig=log_config)

    if args.queries:
      pig_job.queryList = messages.QueryList(queries=args.queries)
    if args.params:
      pig_job.scriptVariables = encoding.DictToMessage(
          args.params, messages.PigJob.ScriptVariablesValue)
    if args.properties:
      pig_job.properties = encoding.DictToMessage(
          args.properties, messages.PigJob.PropertiesValue)

    job.pigJob = pig_job
