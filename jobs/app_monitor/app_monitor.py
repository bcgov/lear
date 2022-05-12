# Copyright © 2021 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""App monitor."""
"""SMTP found in auth-api\sbc-auth\queue_services\notify-queue\src\notifiy_service\worker.py"""

from email.message import EmailMessage
from pandas import to_datetime
import random
import requests
import asyncio
import logging
import os
import sys

from datetime import datetime, timezone
from email.mime.text import MIMEText
from flask import Flask
from legal_api.services.queue import QueueService
# from entity_queue_common.service import ServiceWorker
# from entity_filer.worker import APP_CONFIG, publish_event, qsm
from nats.aio.client import DEFAULT_CONNECT_TIMEOUT
from nats.aio.client import Client as NATS  # noqa N814; by convention the name is NATS # pylint: disable=unused-import
from stan.aio.client import Client as STAN  # noqa N814; by convention the name is STAN

from aiosmtplib import SMTP
import config  # pylint: disable=import-error
from utils.logging import setup_logging  # pylint: disable=import-error

future = asyncio.Future()

def create_app(run_mode=os.getenv('FLASK_ENV', 'production')):
    """Return a configured Flask App using the Factory method."""
    app = Flask(__name__)
    app.config.from_object(config.CONFIGURATION[run_mode])

    register_shellcontext(app)

    return app


def register_shellcontext(app):
    """Register shell context objects."""
    def shell_context():
        """Shell context objects."""
        return {'app': app}

    app.shell_context_processor(shell_context)


default_nats_options = {
            'name': 'default_future_filing_job',
            'servers':  os.getenv('NATS_SERVERS', '').split(','),
            'connect_timeout': os.getenv('NATS_CONNECT_TIMEOUT',  # pylint: disable=invalid-envvar-default
                                         DEFAULT_CONNECT_TIMEOUT)
        }

default_stan_options = {
            'cluster_id': os.getenv('NATS_CLUSTER_ID'),
            'client_id': '_' + str(random.SystemRandom().getrandbits(0x58))
        }

async def check_queue(queue_service, application):  # pylint: disable=redefined-outer-name
    """Run the methods for applying future effective filings."""
    print('checking queue')

    try:
        server = default_nats_options['servers']
        print('ENV-Servers: ', server)

        print('Attempting to connect to queue')
        await asyncio.wait_for(queue_service.connect(), timeout=7.0)
        # await queue_service.connect()        
        print('Connected to queue')
    except:
        print('Cannot connect to queue')
        await send_email_using_SMTP('queue', 'Error: connection failure')
        return

    with application.app_context():
        try:
            print('Attempting to post message to queue')
            async def cb(msg):
                future.set_result(msg)

            channel = "entity.events"
            # await queue_service.subscribe(channel)
            await queue_service.subscribe(channel, cb=cb )
            print('Here2')

            msg = "Testing Connection"
            await queue_service.publish(channel, msg)

            msg = await asyncio.wait_for(future,1)

        except Exception as err:  # pylint: disable=broad-except
            print('Error: Queue message failure')
            await send_email_using_SMTP('queue', 'Error: Queue message failure')


def check_entity_emailer():
    '''Checking that emailer is functioning'''
    # send_direct_email('entity_emailer','APPLICATION FAILURE')


def check_minio():
    '''Checking if mino is responding'''
    # send_direct_email('minio', 'APPLICATION FAILURE')


async def send_email_using_SMTP(app_name, app_error):
    """Send notification that app_name may not be functioning."""
    print('Sending email notification: ', app_name, ' ', app_error)
    try:
        mailList = os.getenv('email_notification_list')
        mailTo = mailList.split(',')

        message = EmailMessage()
        message.set_content( app_name + " " + app_error)
        message["From"] = 'BCRegistries@gov.bc.ca'
        message["To"] = mailTo
        message["Subject"] = "Application Error"
        await send_email(message)

    except Exception as err:  # pylint: disable=broad-except # noqa F841;
        # mark any failure for human review
        print("send_email_using_SMTP Failure")


async def send_email(message):
    """Send email."""
    try:
        smtp_client = SMTP(hostname=os.getenv('MAIL_SERVER'), port=os.getenv('MAIL_PORT'))
        await smtp_client.connect()
        await smtp_client.send_message(message)
        await smtp_client.quit()

    except Exception as err:  # pylint: disable=broad-except # noqa F841;
        print('Send_email Error: %s', err)
        return False
    return True


def run():

    print('Running App')
    condition = sys.argv[1] if sys.argv and len(sys.argv) > 1 else None
    application = create_app()

    with application.app_context():
        event_loop = asyncio.get_event_loop()
        queue_service = QueueService(app=application, loop=event_loop)
        event_loop.run_until_complete( check_queue(queue_service, application))
        queue_service.close

    # checK_entity_emailer
    # check_minio


if __name__ == '__main__':
    run()

