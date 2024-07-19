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
import os

import requests
import sentry_sdk  # noqa: I001; pylint: disable=ungrouped-imports; conflicts with Flake8
from flask import Flask
from legal_api.services.bootstrap import AccountService
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

    # Static class load the variables while importing the class for the first time,
    # By then config is not loaded, so it never get the config value
    AccountService.timeout = int(app.config.get('ACCOUNT_SVC_TIMEOUT'))

    register_shellcontext(app)

    return app


def register_shellcontext(app):
    """Register shell context objects."""
    def shell_context():
        """Shell context objects."""
        return {'app': app}

    app.shell_context_processor(shell_context)


def get_filings(app: Flask, token, page, limit):
    """Get a filing with filing_id."""
    req = requests.get(f'{app.config["LEGAL_API_URL"]}/internal/filings?page={page}&limit={limit}',
                       headers={'Authorization': AccountService.BEARER + token},
                       timeout=AccountService.timeout)
    if not req or req.status_code != 200:
        app.logger.error(f'Failed to collect filings from legal-api. {req} {req.json()} {req.status_code}')
        raise Exception  # pylint: disable=broad-exception-raised
    return req.json()


def send_filing(app: Flask = None, filing: dict = None, filing_id: str = None):
    """Post to colin-api with filing."""
    token = AccountService.get_bearer_token()
    clean_none(filing)

    filing_type = filing['filing']['header'].get('name', None)
    identifier = filing['filing']['business'].get('identifier', None)
    legal_type = filing['filing']['business'].get('legalType', None)

    req = None
    if legal_type and identifier and filing_type:
        req = requests.post(f'{app.config["COLIN_URL"]}/{legal_type}/{identifier}/filings/{filing_type}',
                            headers={**AccountService.CONTENT_TYPE_JSON,
                                     'Authorization': AccountService.BEARER + token},
                            json=filing,
                            timeout=AccountService.timeout)

    if not req or req.status_code != 201:
        app.logger.error(f'Filing {filing_id} not created in colin {identifier}.')
        # raise Exception
        return None
    # if it's an AR containing multiple filings it will have multiple colinIds
    return req.json()['filing']['header']['colinIds']


def update_colin_id(app: Flask = None, filing_id: str = None, colin_ids: list = None, token: dict = None):
    """Update the colin_id in the filings table."""
    req = requests.patch(
        f'{app.config["LEGAL_API_URL"]}/internal/filings/{filing_id}',
        headers={'Authorization': AccountService.BEARER + token},
        json={'colinIds': colin_ids},
        timeout=AccountService.timeout
    )
    if not req or req.status_code != 202:
        app.logger.error(f'Failed to update colin id in legal db for filing {filing_id} {req.status_code}')
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


def run():
    """Get filings that haven't been synced with colin and send them to the colin-api."""
    application = create_app()
    corps_with_failed_filing = []
    with application.app_context():
        try:
            # get updater-job token
            token = AccountService.get_bearer_token()

            page = 1
            total_pages = None
            while ((total_pages is None or page <= total_pages) and
                   (results := get_filings(application, token, page, 50))):
                page += 1
                total_pages = results.get('pages')
                if not (filings := results.get('filings')):
                    # pylint: disable=no-member; false positive
                    application.logger.debug('No completed filings to send to colin.')
                for filing in filings:
                    filing_id = filing['filingId']
                    identifier = filing['filing']['business']['identifier']
                    if identifier in corps_with_failed_filing:
                        # pylint: disable=no-member; false positive
                        application.logger.debug(f'Skipping filing {filing_id} for'
                                                 f' {filing["filing"]["business"]["identifier"]}.')
                    else:
                        colin_ids = send_filing(app=application, filing=filing, filing_id=filing_id)
                        update = None
                        if colin_ids:
                            update = update_colin_id(app=application, filing_id=filing_id,
                                                     colin_ids=colin_ids, token=token)
                        if update:
                            # pylint: disable=no-member; false positive
                            application.logger.debug(f'Successfully updated filing {filing_id}')
                        else:
                            corps_with_failed_filing.append(filing['filing']['business']['identifier'])
                            # pylint: disable=no-member; false positive
                            application.logger.error(f'Failed to update filing {filing_id} with colin event id.')

        except Exception as err:  # noqa: B902
            # pylint: disable=no-member; false positive
            application.logger.error(err)


if __name__ == '__main__':
    run()
