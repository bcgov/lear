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
"""The Future Effective Date service.

This module script is for putting filings with future effective dates on the entity filer queue.
"""
import asyncio
import logging
import os
import random

import requests
import sentry_sdk  # noqa: I001; pylint: disable=ungrouped-imports; conflicts with Flake8
from dotenv import find_dotenv, load_dotenv
from entity_queue_common.service import ServiceWorker
from flask import Flask
from nats.aio.client import DEFAULT_CONNECT_TIMEOUT
from nats.aio.client import Client as NATS  # noqa N814; by convention the name is NATS # pylint: disable=unused-import
from sentry_sdk.integrations.logging import LoggingIntegration  # noqa: I001
from stan.aio.client import Client as STAN  # noqa N814; by convention the name is STAN

import config  # pylint: disable=import-error
from utils.logging import setup_logging  # pylint: disable=import-error


setup_logging(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'logging.conf'))  # important to do this first

default_nats_options = {
    'name': 'default_future_filing_job',
            'servers': os.getenv('NATS_SERVERS', '').split(','),
            'connect_timeout': os.getenv('NATS_CONNECT_TIMEOUT',  # pylint: disable=invalid-envvar-default
                                         DEFAULT_CONNECT_TIMEOUT)
}

default_stan_options = {
    'cluster_id': os.getenv('NATS_CLUSTER_ID'),
    'client_id': '_' + str(random.SystemRandom().getrandbits(0x58))
}

subject = os.getenv('NATS_FILER_SUBJECT', '')

# this will load all the envars from a .env file located in the project root
load_dotenv(find_dotenv())

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

    return app


def get_bearer_token(app: Flask, timeout):
    """Get a valid Bearer token for the service to use."""
    token_url = app.config.get('ACCOUNT_SVC_AUTH_URL')
    client_id = app.config.get('ACCOUNT_SVC_CLIENT_ID')
    client_secret = app.config.get('ACCOUNT_SVC_CLIENT_SECRET')

    data = 'grant_type=client_credentials'

    # get service account token
    res = requests.post(url=token_url,
                        data=data,
                        headers={'content-type': 'application/x-www-form-urlencoded'},
                        auth=(client_id, client_secret),
                        timeout=timeout)

    try:
        return res.json().get('access_token')
    except Exception:  # pylint: disable=broad-exception-caught;
        return None


def get_filing_ids(app: Flask):
    """Get filing id to process."""
    timeout = int(app.config.get('ACCOUNT_SVC_TIMEOUT'))
    token = get_bearer_token(app, timeout)
    response = requests.get(
        f'{app.config["LEGAL_API_URL"]}/internal/filings/future_effective',
        headers={'Content-Type': 'application/json',
                 'Authorization': 'Bearer ' + token},
        timeout=timeout)
    if not response or response.status_code != 200:
        app.logger.error(f'Failed to collect filings from legal-api. \
            {response} {response.json()} {response.status_code}')
        raise Exception  # pylint: disable=broad-exception-raised;
    return response.json()


async def run(loop, application: Flask):  # pylint: disable=redefined-outer-name
    """Run the methods for applying future effective filings."""
    queue_service = ServiceWorker(
        loop=loop,
        nats_connection_options=default_nats_options,
        stan_connection_options=default_stan_options,
        config=config.get_named_config('production')
    )

    await queue_service.connect()

    with application.app_context():
        try:
            if not (filing_ids := get_filing_ids(application)):
                application.logger.debug('No filings found to apply.')
            for filing_id in filing_ids:
                msg = {'filing': {'id': filing_id}}
                await queue_service.publish(subject, msg)
                application.logger.debug(f'Successfully put filing {filing_id} on the queue.')
        except Exception as err:  # pylint: disable=broad-except
            application.logger.error(err)

if __name__ == '__main__':
    application = create_app()
    try:
        event_loop = asyncio.get_event_loop()
        event_loop.run_until_complete(run(event_loop, application))
    except Exception as err:  # pylint: disable=broad-except; Catching all errors from the frameworks
        application.logger.error(err)  # pylint: disable=no-member
        raise err
