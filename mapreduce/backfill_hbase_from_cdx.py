#!/usr/bin/env python3
"""
Streaming Hadoop script to import CDX metadata into the HBase fulltext table,
primarily for URL-agnostic crawl de-duplication. Takes only "fulltext" file
formats.

Requires:
- happybase
- mrjob

TODO:
- argparse
- refactor into an object
- tests in separate file
- nose tests
- sentry integration for error reporting
"""

import sys
import json
import happybase
import mrjob
from mrjob.job import MRJob
from common import parse_cdx_line


class MRCDXBackfillHBase(MRJob):

    # CDX lines in; JSON status out
    INPUT_PROTOCOL = mrjob.protocol.RawValueProtocol
    OUTPUT_PROTOCOL = mrjob.protocol.JSONValueProtocol

    def configure_args(self):
        super(MRCDXBackfillHBase, self).configure_args()

        self.add_passthru_arg('--hbase-table',
                              type=str,
                              default='wbgrp-journal-extract-0-qa',
                              help='HBase table to backfill into (must exist)')
        self.add_passthru_arg('--hbase-host',
                              type=str,
                              default='localhost',
                              help='HBase thrift API host to connect to')

    def __init__(self, *args, **kwargs):

        # Allow passthrough for tests
        if 'hb_table' in kwargs:
            self.hb_table = kwargs.pop('hb_table')
        else:
            self.hb_table = None

        super(MRCDXBackfillHBase, self).__init__(*args, **kwargs)
        self.mime_filter = ['application/pdf']

    def mapper_init(self):

        if self.hb_table is None:
            try:
                host = self.options.hbase_host
                # TODO: make these configs accessible from... mrconf.cfg?
                hb_conn = happybase.Connection(host=host, transport="framed",
                    protocol="compact")
            except Exception as err:
                raise Exception("Couldn't connect to HBase using host: {}".format(host))
            self.hb_table = hb_conn.table(self.options.hbase_table)

    def mapper(self, _, raw_cdx):

        self.increment_counter('lines', 'total')

        if (raw_cdx.startswith(' ') or raw_cdx.startswith('filedesc') or
                raw_cdx.startswith('#')):

            # Skip line
            # XXX: tests don't cover this path; need coverage!
            self.increment_counter('lines', 'invalid')
            return _, dict(status="invalid")

        info = parse_cdx_line(raw_cdx)
        if info is None:
            self.increment_counter('lines', 'invalid')
            return _, dict(status="invalid")

        if info['file:mime'] not in self.mime_filter:
            self.increment_counter('lines', 'skip')
            return _, dict(status="skip")

        key = info.pop('key')
        info['f:c'] = json.dumps(info['f:c'], sort_keys=True, indent=None)
        info['file:cdx'] = json.dumps(info['file:cdx'], sort_keys=True,
            indent=None)

        self.hb_table.put(key, info)
        self.increment_counter('lines', 'success')

        yield _, dict(status="success")

if __name__ == '__main__':
    MRCDXBackfillHBase.run()
