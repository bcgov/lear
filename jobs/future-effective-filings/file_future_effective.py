# Copyright © 2019 Province of British Columbia
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
"""The Legal API service.

This module is the API for the Legal Entity system.
"""
import asyncio
from datetime import datetime, timezone
import json
import logging
import os
import random
import string

import sentry_sdk  # noqa: I001; pylint: disable=ungrouped-imports; conflicts with Flake8
from dateutil.parser import parse
from sentry_sdk.integrations.logging import LoggingIntegration  # noqa: I001
from flask import Flask
from flask_jwt_oidc import JwtManager
from nats.aio.client import Client as NATS, DEFAULT_CONNECT_TIMEOUT  # noqa N814; by convention the name is NATS
from stan.aio.client import Client as STAN  # noqa N814; by convention the name is STAN
import pytz

import requests
from dotenv import find_dotenv, load_dotenv
import config


from utils.logging import setup_logging
from entity_queue_common.service import QueueServiceManager, ServiceWorker

setup_logging(os.path.join(os.path.abspath(os.path.dirname(__file__)), \
    'logging.conf'))  # important to do this first

default_nats_options = {
            'name': 'default_future_filing_job',
            'servers':  os.getenv('NATS_SERVERS', '').split(','),
            'connect_timeout': os.getenv('NATS_CONNECT_TIMEOUT', DEFAULT_CONNECT_TIMEOUT)
        }

default_stan_options = {
            'cluster_id': os.getenv('NATS_CLUSTER_ID'),
            'client_id':
             '_' + str(random.SystemRandom().getrandbits(0x58))
        }

subject = os.getenv('NATS_FILER_SUBJECT', '')

# this will load all the envars from a .env file located in the project root
load_dotenv(find_dotenv())

# lower case name as used by convention in most Flask apps
jwt = JwtManager()  # pylint: disable=invalid-name

SENTRY_LOGGING = LoggingIntegration(
    event_level=logging.ERROR  # send errors as events
)

def format_message(filing_id, payment_id, status):
    return {
        'statusChanged' : {
            'id' : filing_id,
            'newStatus' : status
            },
        'paymentToken' : {
            'id' : payment_id,
            'statusCode' : status
        }
    }
def create_app(run_mode=os.getenv('FLASK_ENV', 'production')):
    """Return a configured Flask App using the Factory method."""
    app = Flask(__name__)
    app.config.from_object(config.CONFIGURATION[run_mode])
    # Configure Sentry
    if app.config.get('SENTRY_DSN', None):
        sentry_sdk.init(
            dsn=app.config.get('SENTRY_DSN'),
            integrations=[SENTRY_LOGGING]
        )

    setup_jwt_manager(app, jwt)

    return app

def setup_jwt_manager(app, jwt_manager):
    """Use flask app to configure the JWTManager to work for a particular Realm."""
    def get_roles(a_dict):
        return a_dict['realm_access']['roles']  # pragma: no cover
    app.config['JWT_ROLE_CALLBACK'] = get_roles

    jwt_manager.init_app(app)


def get_filings(app: Flask = None):
    """Get a filing with filing_id."""
    r = requests.get(f'{app.config["LEGAL_URL"]}/internal/filings/PAID')
    if not r or r.status_code != 200:
        app.logger.error(f'Failed to collect filings from legal-api. \
            {r} {r.json()} {r.status_code}')
        raise Exception
    return r.json()

async def run(loop, application: Flask = None):
    application = create_app()
    queue_service = ServiceWorker(loop=loop, nats_connection_options=default_nats_options,
    stan_connection_options=default_stan_options, config=config.get_named_config('production'))

    await queue_service.connect()

    with application.app_context():
        try:
            # get updater-job token
            creds = {'username': application.config['USERNAME'],
                     'password': application.config['PASSWORD']
                     }
            auth = requests.post(application.config['AUTH_URL'],
                                 json=creds,
                                 headers={
                                     'Content-Type': 'application/json'}
                                )
            if auth.status_code != 200:
                application.logger.error(f'file_future_effective failed to authenticate {auth.json()} {auth.status_code}')
                raise Exception
            # TODO token = dict(auth.json())['access_token']

            filings = get_filings(app=application)
            if not filings:
                application.logger.debug(f'No completed filings to send to colin.')
            for filing in filings:
                filing_id = filing["filing"]["header"]["filingId"]
                payment_id = filing["filing"]["header"]["paymentToken"]
                effective_date = filing["filing"]["header"]["effectiveDate"]
                # TODO Use UTC time?
                now = datetime.utcnow().replace(tzinfo=timezone.utc)
                valid = effective_date and parse(effective_date) <= now
                if valid:
                    msg = format_message(filing_id, payment_id, 'COMPLETE')
                    await queue_service.publish(subject, msg)
                    #await queue.async_publish_filing(filing_id, 'COMPLETED', payment_id)
                    application.logger.error(f'Successfully updated filing {filing_id}')
        except Exception as err:
            application.logger.error(err)

if __name__ == "__main__":
    try:
        event_loop = asyncio.get_event_loop()
        event_loop.run_until_complete(run(event_loop))
    except Exception as err:  # pylint: disable=broad-except; Catching all errors from the frameworks
        print('problem in running the service: %s', err, stack_info=True, exc_info=True)

