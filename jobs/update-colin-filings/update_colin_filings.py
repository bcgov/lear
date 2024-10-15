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
import logging
import math
import os

import requests
import sentry_sdk  # noqa: I001; pylint: disable=ungrouped-imports; conflicts with Flake8
from flask import Flask
from sentry_sdk.integrations.logging import LoggingIntegration  # noqa: I001

import config  # pylint: disable=import-error; false positive in gha only
from utils.logging import setup_logging  # noqa: I001; pylint: disable=import-error; false positive in gha only
# noqa: 1005
setup_logging(os.path.join(
    os.path.abspath(os.path.dirname(__file__)), 'logging.conf'))

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

    register_shellcontext(app)

    return app


def register_shellcontext(app):
    """Register shell context objects."""
    def shell_context():
        """Shell context objects."""
        return {'app': app}

    app.shell_context_processor(shell_context)


def get_filings(app: Flask, token, page, limit):
    """Get filings ready for colin sync."""
    requests_timeout = int(app.config.get('ACCOUNT_SVC_TIMEOUT'))
    req = requests.get(f'{app.config["LEGAL_API_URL"]}/businesses/internal/filings?page={page}&limit={limit}',
                       headers={'Authorization': 'Bearer ' + token},
                       timeout=requests_timeout)
    if not req or req.status_code != 200:
        app.logger.error(f'Failed to collect filings from legal-api. {req} {req.json()} {req.status_code}')
        raise Exception  # pylint: disable=broad-exception-raised
    return req.json()


def get_batch_processings(app: Flask, token, page, limit):
    """Get a batch processings ready for colin sync."""
    requests_timeout = int(app.config.get('ACCOUNT_SVC_TIMEOUT'))
    req = requests.get(f'{app.config["LEGAL_API_URL"]}/businesses/internal/batch_processings?page={page}&limit={limit}',
                       headers={'Authorization': 'Bearer ' + token},
                       timeout=requests_timeout)
    if not req or req.status_code != 200:
        app.logger.error(f'Failed to collect batch processings from legal-api. {req} {req.json()} {req.status_code}')
        raise Exception  # pylint: disable=broad-exception-raised
    return req.json()


def send_filing(app: Flask, token: str, filing: dict, filing_id: str):
    """Post to colin-api with filing."""
    clean_none(filing)

    filing_type = filing['filing']['header'].get('name', None)
    identifier = filing['filing']['business'].get('identifier', None)
    legal_type = filing['filing']['business'].get('legalType', None)

    req = None
    if legal_type and identifier and filing_type:
        requests_timeout = int(app.config.get('ACCOUNT_SVC_TIMEOUT'))
        req = requests.post(f'{app.config["COLIN_URL"]}/{legal_type}/{identifier}/filings/{filing_type}',
                            headers={'Content-Type': 'application/json',
                                     'Authorization': 'Bearer ' + token},
                            json=filing,
                            timeout=requests_timeout)

    if not req or req.status_code != 201:
        app.logger.error(f'Filing {filing_id} not created in colin {identifier}.')
        # raise Exception
        return None
    # if it's an AR containing multiple filings it will have multiple colinIds
    return req.json()['filing']['header']['colinIds']


def send_batch_processing(app: Flask, token: str, batch_processing: dict, batch_processing_id: str):
    """Post to colin-api with batch processing."""
    clean_none(batch_processing)

    identifier = batch_processing.get('businessIdentifier', None)
    legal_type = batch_processing.get('businessLegalType', None)

    req = None
    if legal_type and identifier:
        requests_timeout = int(app.config.get('ACCOUNT_SVC_TIMEOUT'))
        req = requests.patch(f'{app.config["COLIN_URL"]}/internal/{legal_type}/{identifier}',
                             headers={'Content-Type': 'application/json',
                                      'Authorization': 'Bearer ' + token},
                             json=batch_processing,
                             timeout=requests_timeout)

    if not req or req.status_code != 201:
        app.logger.error(f'Batch processing {batch_processing_id} not created in colin {identifier}.')
        # raise Exception
        return None
    return req.json()['batchProcessing']['colinIds']


def update_colin_id(app: Flask, token: dict, filing_id: str, colin_ids: list):
    """Update the colin_id in the filings table."""
    requests_timeout = int(app.config.get('ACCOUNT_SVC_TIMEOUT'))
    req = requests.patch(
        f'{app.config["LEGAL_API_URL"]}/businesses/internal/filings/{filing_id}',
        headers={'Authorization': 'Bearer ' + token},
        json={'colinIds': colin_ids},
        timeout=requests_timeout
    )
    if not req or req.status_code != 202:
        app.logger.error(f'Failed to update colin id in legal db for filing {filing_id} {req.status_code}')
        return False
    return True


def update_batch_processing_colin_id(app: Flask, token: dict, batch_processing_id: str, colin_ids: list):
    """Update the colin_id in the batch processing table."""
    requests_timeout = int(app.config.get('ACCOUNT_SVC_TIMEOUT'))
    req = requests.patch(
        f'{app.config["LEGAL_API_URL"]}/businesses/internal/batch_processings/{batch_processing_id}',
        headers={'Authorization': 'Bearer ' + token},
        json={'colinIds': colin_ids},
        timeout=requests_timeout
    )
    if not req or req.status_code != 202:
        app.logger.error(f'Failed to update colin id in legal db for batch '
                         f'processing {batch_processing_id} {req.status_code}')
        return False
    return True


def clean_none(dictionary: dict = None):
    """Replace all none values with empty string."""
    for key in dictionary.keys():
        if dictionary[key]:
            if isinstance(dictionary[key], dict):
                clean_none(dictionary[key])
        elif dictionary[key] is None:
            dictionary[key] = ''


def get_bearer_token(app):
    """Get a valid Bearer token for the service to use."""
    token_url = app.config.get('ACCOUNT_SVC_AUTH_URL')
    client_id = app.config.get('ACCOUNT_SVC_CLIENT_ID')
    client_secret = app.config.get('ACCOUNT_SVC_CLIENT_SECRET')
    requests_timeout = int(app.config.get('ACCOUNT_SVC_TIMEOUT'))

    data = 'grant_type=client_credentials'

    # get service account token
    res = requests.post(url=token_url,
                        data=data,
                        headers={'content-type': 'application/x-www-form-urlencoded'},
                        auth=(client_id, client_secret),
                        timeout=requests_timeout)

    try:
        return res.json().get('access_token')
    except Exception:  # noqa: B902
        return None


def update_filings(app: Flask, token: dict):
    """Get filings that haven't been synced with colin and send them to the colin-api."""
    page = 1
    limit = 50
    pending_filings = None
    corps_with_failed_filing = []

    while ((pending_filings is None or page <= math.ceil(pending_filings/limit)) and
           (results := get_filings(app, token, page, limit))):
        page += 1
        pending_filings = results.get('total')
        if not (filings := results.get('filings')):
            # pylint: disable=no-member; false positive
            app.logger.debug('No completed filings to send to colin.')
        for filing in filings:
            filing_id = filing['filingId']
            identifier = filing['filing']['business']['identifier']
            if identifier in corps_with_failed_filing:
                # pylint: disable=no-member; false positive
                app.logger.debug(f'Skipping filing {filing_id} for'
                                 f' {filing["filing"]["business"]["identifier"]}.')
            else:
                colin_ids = send_filing(app, token, filing, filing_id)
                update = None
                if colin_ids:
                    update = update_colin_id(app, token, filing_id, colin_ids)
                if update:
                    # pylint: disable=no-member; false positive
                    app.logger.debug(f'Successfully updated filing {filing_id}')
                    pending_filings -= 1
                else:
                    corps_with_failed_filing.append(filing['filing']['business']['identifier'])
                    # pylint: disable=no-member; false positive
                    app.logger.error(f'Failed to update filing {filing_id} with colin event id.')


def update_batch_processings(app: Flask, token: dict):
    """Get eligible batch processings and send them to the colin-api."""
    page = 1
    limit = 50
    pending_batch_processings = None
    corps_with_failed_batch_processing = []

    while (
        (pending_batch_processings is None or page <= math.ceil(pending_batch_processings/limit)) and
        (results := get_batch_processings(app, token, page, limit))
    ):
        page += 1
        pending_batch_processings = results.get('total')
        if not (batch_processings := results.get('batchProcessings')):
            # pylint: disable=no-member; false positive
            app.logger.debug('No eligible batch processings to send to colin.')
        for batch_processing in batch_processings:
            batch_processing_id = batch_processing['id']
            identifier = batch_processing['businessIdentifier']
            if identifier in corps_with_failed_batch_processing:
                # pylint: disable=no-member; false positive
                app.logger.debug(f'Skipping batch processing {batch_processing_id} for {identifier}.')
            else:
                colin_ids = send_batch_processing(app, token, batch_processing, batch_processing_id)
                update = None
                if colin_ids:
                    update = update_batch_processing_colin_id(app, token, batch_processing_id, colin_ids)
                if update:
                    # pylint: disable=no-member; false positive
                    app.logger.debug(f'Successfully updated batch processing {batch_processing_id}')
                    pending_batch_processings -= 1
                else:
                    corps_with_failed_batch_processing.append(batch_processing['businessIdentifier'])
                    # pylint: disable=no-member; false positive
                    app.logger.error(f'Failed to update batch processing {batch_processing_id} with colin event id.')


def run():
    """Run the job to update filings and batch processings."""
    application = create_app()
    with application.app_context():
        try:
            # get updater-job token
            token = get_bearer_token(application)
            update_filings(application, token)
            update_batch_processings(application, token)

        except Exception as err:  # noqa: B902
            # pylint: disable=no-member; false positive
            application.logger.error(err)


if __name__ == '__main__':
    run()
