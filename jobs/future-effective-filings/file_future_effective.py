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
from datetime import datetime
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

import config
import requests

from registry_schemas import validate
from utils.logging import setup_logging
from dotenv import find_dotenv, load_dotenv

class QueueHelper():
    
    name = ''
    nats_options = {}
    stan_options = {}
    loop = None
    nats_servers = None
    subject = None

    def __init__(self, loop=None):
        """Initialize, supports setting the app context on instantiation."""
        # Default NATS Options
        self.name = 'default_api_client'
        self.nats_options = {}
        self.stan_options = {}
        self.loop = loop
        self.nats_servers = None
        self.subject = None

        self.logger = logging.getLogger()

    def on_error(self):
        pass

    def on_close(self):
        pass

    def on_disconnect(self):
        pass

    def on_reconnect(self):
        pass

    def setup_queue(self):
    
        self.name = os.getenv('NATS_CLIENT_NAME', '')
        self.loop = asyncio.get_event_loop()
        self.nats_servers = os.getenv('NATS_SERVERS', '').split(',')
        self.subject = os.getenv('NATS_FILER_SUBJECT', '')

        default_nats_options = {
            'name': self.name,
            'io_loop': self.loop,
            'servers': self.nats_servers,
            'connect_timeout': os.getenv('NATS_CONNECT_TIMEOUT', 2),
            # NATS handlers
            'error_cb': self.on_error,
            'closed_cb': self.on_close,
            'reconnected_cb': self.on_reconnect,
            'disconnected_cb': self.on_disconnect,
        }

        self.nats_options = {**default_nats_options}

        default_stan_options = {
            'cluster_id': os.getenv('NATS_CLUSTER_ID'),
            'client_id':
            (self.name.
             lower().
             strip(string.whitespace)
             ).translate({ord(c): '_' for c in string.punctuation})
            + '_' + str(random.SystemRandom().getrandbits(0x58))
        }

        if not self.stan_options:
            stan_options = {}

        self.stan_options = {**default_stan_options, **stan_options}

    async def connect(self):
        """Connect to the queueing service."""
        #ctx = _app_ctx_stack.top
        #if ctx:
        if not hasattr(self, 'nats'):
            self.nats = NATS()
            self.stan = STAN()

        if not self.nats.is_connected:
            self.stan_options = {**self.stan_options, **{'nats': self.nats}}
            await self.nats.connect(**self.nats_options)
            await self.stan.connect(**self.stan_options)
    
    async def async_publish_filing(self, filing_id, status, payment_id):
        """Publish the json payload to the Queue Service."""
        message = {'statusChanged': {'id' : filing_id, 'newStatus' : status}, 'paymentToken' : {'id' : payment_id, 'statusCode' : status}}
        if not self.nats.is_connected:
            await self.connect()

        await self.stan.publish(subject=self.subject,
                                payload=json.dumps(message).encode('utf-8'))

# this will load all the envars from a .env file located in the project root
load_dotenv(find_dotenv())

setup_logging(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'logging.conf'))  # important to do this first

# lower case name as used by convention in most Flask apps
jwt = JwtManager()  # pylint: disable=invalid-name

SENTRY_LOGGING = LoggingIntegration(
    event_level=logging.ERROR  # send errors as events
)

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

    register_shellcontext(app)

    return app

def setup_jwt_manager(app, jwt_manager):
    """Use flask app to configure the JWTManager to work for a particular Realm."""
    def get_roles(a_dict):
        return a_dict['realm_access']['roles']  # pragma: no cover
    app.config['JWT_ROLE_CALLBACK'] = get_roles

    jwt_manager.init_app(app)

def register_shellcontext(app):
    """Register shell context objects."""
    def shell_context():
        """Shell context objects."""
        return {
            'app': app,
            'jwt': jwt}  # pragma: no cover

    app.shell_context_processor(shell_context)

def get_filings(app: Flask = None):
    """Get a filing with filing_id."""
    r = requests.get(f'{app.config["LEGAL_URL"]}/internal/filings/FUTURE')
    if not r or r.status_code != 200:
        app.logger.error(f'Failed to collect filings from legal-api. {r} {r.json()} {r.status_code}')
        raise Exception
    return r.json()

async def run(loop):
    application = create_app()
    queue =  QueueHelper(loop)
    queue.setup_queue()
    await queue.connect()
    with application.app_context():
        try:
            # get updater-job token
            creds = {'username': application.config['USERNAME'], 'password': application.config['PASSWORD']}
            auth = requests.post(application.config['AUTH_URL'], json=creds, headers={
                'Content-Type': 'application/json'})
            if auth.status_code != 200:
                application.logger.error(f'colin-updater failed to authenticate {auth.json()} {auth.status_code}')
                raise Exception
            token = dict(auth.json())['access_token']

            filings = get_filings(app=application)
            if not filings:
                application.logger.debug(f'No completed filings to send to colin.')
            for filing in filings:
                filing_id = filing["filing"]["header"]["filingId"]
                payment_id = filing["filing"]["header"]["paymentToken"]
                effective_date = filing["filing"]["header"]["futureEffectiveDate"]
                # TODO Use UTC time?
                now = pytz.UTC.localize(datetime.now())
                valid = effective_date and parse(effective_date) <= now
                if valid:
                    await queue.async_publish_filing(filing_id, 'COMPLETED', payment_id)
                    application.logger.error(f'Successfully updated filing {filing_id}')
        except Exception as err:
            application.logger.error(err)

if __name__ == "__main__":
    try:
        event_loop = asyncio.get_event_loop()
        event_loop.run_until_complete(run(event_loop))
        event_loop.run_forever()
    except Exception as err:  # pylint: disable=broad-except; Catching all errors from the frameworks
        logger.error('problem in running the service: %s', err, stack_info=True, exc_info=True)
    finally:
        event_loop.close()
