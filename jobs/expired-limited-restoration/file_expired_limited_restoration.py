# Copyright © 2025 Province of British Columbia
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
"""The Expired Limited Restoration service.

This module is being used to process businesses with expired limited restorations.
"""
import asyncio
import logging
import os
from datetime import datetime

import requests
import sentry_sdk  # noqa: I001; pylint: disable=ungrouped-imports; conflicts with Flake8
from dotenv import find_dotenv, load_dotenv
from flask import Flask
from sentry_sdk.integrations.logging import LoggingIntegration  # noqa: I001

import config  # pylint: disable=import-error
from utils.logging import setup_logging  # pylint: disable=import-error


setup_logging(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'logging.conf'))  # important to do this first

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
    except Exception:  # pylint: disable=broad-exception-caught; # noqa: B902
        return None


def get_businesses_to_process(app: Flask):
    """Get list of business identifiers that need processing."""
    timeout = int(app.config.get('ACCOUNT_SVC_TIMEOUT'))
    token = get_bearer_token(app, timeout)

    response = requests.get(
        f'{app.config["LEGAL_API_URL"]}/internal/expired_restoration',
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        },
        timeout=timeout
    )

    if not response or response.status_code != 200:
        app.logger.error(f'Failed to get businesses from legal-api.  \
            {response} {response.json()} {response.status_code}')
        raise Exception  # pylint: disable=broad-exception-raised;

    return response.json().get('businesses', [])


def create_put_back_off_filing(app: Flask, business):
    """Create a putBackOff filing for the business."""
    timeout = int(app.config.get('ACCOUNT_SVC_TIMEOUT'))
    token = get_bearer_token(app, timeout)
    identifier = business['identifier']
    filing_data = {
        'filing': {
            'header': {
                'date': datetime.utcnow().date().isoformat(),
                'name': 'putBackOff',
                'certifiedBy': 'system'
            },
            'business': {
                'identifier': business['identifier'],
                'legalType': business['legal_type']
            },
            'putBackOff': {
                'details': 'Put back off filing due to expired limited restoration.'
            }
        }
    }

    response = requests.post(
        f'{app.config["LEGAL_API_URL"]}/businesses/{identifier}/filings',
        json=filing_data,
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}',
            'hide-in-ledger': 'true'  # Add this header to hide from ledger
        },
        timeout=timeout
    )

    if not response or response.status_code != 201:
        app.logger.error(f'Failed to create filing from legal-api. \
            {response} {response.json()} {response.status_code}')
        raise Exception  # pylint: disable=broad-exception-raised;

    return response.json()


async def run(loop, application: Flask):  # pylint: disable=redefined-outer-name
    """Run the methods for processing expired limited restorations."""
    with application.app_context():
        try:
            # 1. get businesses that need to be processed
            businesses = get_businesses_to_process(application)

            if not businesses:
                application.logger.debug('No businesses to process')
                return

            application.logger.debug(f'Processing {len(businesses)} businesses')

            # 2. create put back off filing for each business
            for business in businesses:
                try:
                    # create putBackOff filing via API
                    identifier = business['identifier']
                    filing = create_put_back_off_filing(application, business)
                    filing_id = filing['filing']['header']['filingId']
                    application.logger.debug(
                        f'Successfully created put back off filing {filing_id} for {identifier}'
                    )
                except Exception as err:  # pylint: disable=broad-except;  # noqa: B902
                    application.logger.error(f'Error processing business {identifier}: {err}')
                    continue
        except Exception as err:  # pylint: disable=broad-except;  # noqa: B902
            application.logger.error(f'Job failed: {err}')


if __name__ == '__main__':
    application = create_app()
    try:
        event_loop = asyncio.get_event_loop()
        event_loop.run_until_complete(run(event_loop, application))
    except Exception as err:  # pylint: disable=broad-except;  # noqa: B902; Catching all errors from the frameworks
        application.logger.error(err)  # pylint: disable=no-member
        raise err
