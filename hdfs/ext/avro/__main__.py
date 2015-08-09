#!/usr/bin/env python
# encoding: utf-8

"""HdfsCLI Avro: an Avro extension for HdfsCLI.

Usage:
  hdfscli-avro schema [-a ALIAS] [-v...] HDFS_PATH
  hdfscli-avro read [-a ALIAS] [-v...] [-F FREQ|-n NUM] [-p PARTS] HDFS_PATH
  hdfscli-avro write [-fa ALIAS] [-v...] [-S SCHEMA] HDFS_PATH
  hdfscli-avro -h | -L

Commands:
  schema                        Pretty print schema.
  read                          Read an Avro file from HDFS and output records
                                as JSON to standard out.
  write                         Read JSON records from standard in and
                                serialize them into a single Avro file on HDFS.

Arguments:
  HDFS_PATH                     Remote path to Avro file or directory
                                containing Avro part-files.

Options:
  -F FREQ --freq=FREQ           Probability of sampling a record.
  -L --log                      Show path to current log file and exit.
  -S SCHEMA --schema=SCHEMA     Schema for serializeing records. If not passed,
                                it will be inferred from the first record.
  -a ALIAS --alias=ALIAS        Alias.
  -f --force                    Overwrite any existing file.
  -h --help                     Show this message and exit.
  -n NUM --num=NUM              Cap number of records to output.
  -p PARTS --parts=PARTS        Part-files to read. Specify a number to
                                randomly select that many, or a comma-separated
                                list of numbers to read only these. Use a
                                number followed by a comma (e.g. `1,`) to get a
                                unique part-file. The default is to read all
                                part-files.
  -v --verbose                  Enable log output. Can be specified up to three
                                times (increasing verbosity each time).

Examples:
  hdfscli-avro schema /data/impressions.avro
  hdfscli-avro read -a dev snapshot.avro >snapshot.jsonl
  hdfscli-avro read -f 0.1 -p 2,3 clicks.avro

"""

from . import AvroReader, AvroWriter
from ...__main__ import CliConfig, parse_arg
from ...util import HdfsError, catch
from docopt import docopt
from itertools import islice
from json import dumps, loads
from random import random
import sys


@catch(HdfsError)
def main():
  """Entry point."""
  args = docopt(__doc__)
  config = CliConfig('hdfscli-avro', args['--verbose'])
  client = config.create_client(args['--alias'])
  if args['--log']:
    handler = config.get_file_handler()
    if handler:
      sys.stdout.write('%s\n' % (handler.baseFilename, ))
    else:
      sys.stdout.write('No log file active.\n')
    sys.exit(0)
  overwrite = args['--force']
  parts = parse_arg(args, '--parts', int, ',')
  if args['write']:
    writer = AvroWriter(
      client,
      args['HDFS_PATH'],
      overwrite=overwrite,
      schema=parse_arg(args, '--schema', loads),
    )
    with writer:
      records = (loads(line) for line in sys.stdin)
      for record in records:
        writer.write(record)
  else:
    reader = AvroReader(client, args['HDFS_PATH'], parts)
    with reader:
      if args['schema']:
        sys.stdout.write('%s\n' % (dumps(reader.schema, indent=2), ))
      elif args['read']:
        num = parse_arg(args, '--num', int)
        freq = parse_arg(args, '--freq', float)
        if freq:
          for record in reader:
            if random() <= freq:
              sys.stdout.write('%s\n' % (dumps(record), ))
        else:
          for record in islice(reader, num):
            sys.stdout.write('%s\n' % (dumps(record), ))

if __name__ == '__main__':
  main()