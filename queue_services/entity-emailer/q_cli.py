#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Service for listening and handling Queue Messages.

This service registers interest in listening to a Queue and processing received messages.
"""
import asyncio
import functools
import getopt
import json
import os
import random
import signal
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Final

from nats.aio.client import Client as NATS  # noqa N814; by convention the name is NATS
from stan.aio.client import Client as STAN  # noqa N814; by convention the name is STAN

from entity_queue_common.service_utils import error_cb, logger, signal_handler


affiliation_type: Final = 'bc.registry.affiliation'
dissolution_type: Final = 'bc.registry.dissolution'
bn: Final = 'businessNumber'


async def run(loop, email_info):  # pylint: disable=too-many-locals
    """Run the main application loop for the service.

    This runs the main top level service functions for working with the Queue.
    """
    # NATS client connections
    nc = NATS()
    sc = STAN()

    async def close():
        """Close the stream and nats connections."""
        await sc.close()
        await nc.close()

    # Connection and Queue configuration.
    def nats_connection_options():
        return {
            'servers': os.getenv('NATS_SERVERS', 'nats://127.0.0.1:4222').split(','),
            'io_loop': loop,
            'error_cb': error_cb,
            'name': os.getenv('NATS_CLIENT_NAME', 'entity.filing.tester')
        }

    def stan_connection_options():
        return {
            'cluster_id': os.getenv('NATS_CLUSTER_ID', 'test-cluster'),
            'client_id': str(random.SystemRandom().getrandbits(0x58)),
            'nats': nc
        }

    def subscription_options():
        return {
            'subject': os.getenv('NATS_EMAILER_SUBJECT', 'error'),
            'queue': os.getenv('NATS_QUEUE', 'error'),
            'durable_name': os.getenv('NATS_QUEUE', 'error') + '_durable'
        }

    try:
        # Connect to the NATS server, and then use that for the streaming connection.
        await nc.connect(**nats_connection_options())
        await sc.connect(**stan_connection_options())

        # register the signal handler
        for sig in ('SIGINT', 'SIGTERM'):
            loop.add_signal_handler(getattr(signal, sig),
                                    functools.partial(signal_handler, sig_loop=loop, sig_nc=nc, task=close)
                                    )

        if email_info['type'] in [affiliation_type, dissolution_type]:
            payload = email_info
        else:
            payload = {'email': email_info}

        print('publishing:', payload)
        await sc.publish(subject=subscription_options().get('subject'),
                         payload=json.dumps(payload).encode('utf-8'))

    except Exception as e:  # pylint: disable=broad-except
        # TODO tighten this error and decide when to bail on the infinite reconnect
        logger.error(e)


if __name__ == '__main__':
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'f:t:o:i:n:', ['fid=', 'etype=', 'option=', 'identifier=', 'name='])
    except getopt.GetoptError:
        print('q_cli.py -f <filing_id> -t <email_type> -o <option> -i <identifier> -n <name>')
        sys.exit(2)
    fid, etype, option, identifier, name = None, None, None, None, None
    for opt, arg in opts:
        if opt in ('-f', '--fid'):
            fid = arg
        elif opt in ('-t', '--etype'):
            etype = arg
        elif opt in ('-o', '--option'):
            option = arg
        elif opt in ('-i', '--identifier'):
            identifier = arg
        elif opt in ('-n', '--name'):
            name = arg
    if not etype or (etype not in [affiliation_type, dissolution_type, bn] and not all([fid, etype, option])):
        print('q_cli.py -f <filing_id> -t <email_type> -o <option> -i <identifier>')
        sys.exit()
    elif etype and etype in [affiliation_type] and not all([fid, etype]):
        print('q_cli.py -f <filing_id> -t <email_type>')
        sys.exit()
    elif etype and etype in [dissolution_type] and not all([fid, etype, identifier, name]):
        print('q_cli.py -f <furnishing_id> -t <email_type> -i <identifier> -n <furnishing_name>')
    elif etype and etype in [bn] and not all([etype, identifier]):
        print('q_cli.py -t <email_type> -i <identifier>')

    if etype in [affiliation_type]:
        msg_id = str(uuid.uuid4())
        source = f'/businesses/{identifier}'
        time = datetime.utcfromtimestamp(time.time()).replace(tzinfo=timezone.utc).isoformat()
        email_info = {
                        'specversion': '1.x-wip',
                        'type': etype,
                        'source': source,
                        'id': msg_id,
                        'time': time,
                        'datacontenttype': 'application/json',
                        'identifier': identifier,
                        'data': {'filing': {'header': {'filingId': fid}}},
                     }
    elif etype in [dissolution_type]:
        msg_id = str(uuid.uuid4())
        time = datetime.utcfromtimestamp(time.time()).replace(tzinfo=timezone.utc).isoformat()
        email_info = {
                        'specversion': '1.x-wip',
                        'type': etype,
                        'source': 'furnishingJob',
                        'id': msg_id,
                        'time': time,
                        'datacontenttype': 'application/json',
                        'identifier': identifier,
                        'data': {'furnishing': {'type':'INVOLUNTARY_DISSOLUTION', 'furnishingId': fid, 'furnishingName': name}},
                     }
    else:
        email_info = {'filingId': fid, 'type': etype, 'option': option, 'identifier': identifier}

    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(run(event_loop, email_info))
