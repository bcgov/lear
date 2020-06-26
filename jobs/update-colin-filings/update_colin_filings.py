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

import sentry_sdk  # noqa: I001; pylint: disable=ungrouped-imports; conflicts with Flake8
from flask import Flask
from legal_api.services.bootstrap import AccountService
from registry_schemas import validate
from sentry_sdk.integrations.logging import LoggingIntegration  # noqa: I001

import config
import requests
from utils.logging import setup_logging

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


def get_filings(app: Flask = None):
    """Get a filing with filing_id."""
    r = requests.get(f'{app.config["LEGAL_URL"]}/internal/filings')
    if not r or r.status_code != 200:
        app.logger.error(f'Failed to collect filings from legal-api. {r} {r.json()} {r.status_code}')
        raise Exception
    return r.json()


def send_filing(app: Flask = None, filing: dict = None, filing_id: str = None):
    """Post to colin-api with filing."""
    clean_none(filing)

    # validate schema
    is_valid, errors = validate(filing, 'filing')
    if errors:
        for err in errors:
            app.logger.error(err.message)
        return None
    else:
        filing_type = filing['filing']['header']['name']
        app.logger.debug(f'Filing {filing_id} in colin for {filing["filing"]["business"]["identifier"]}.')
        r = requests.post(f'{app.config["COLIN_URL"]}/{filing["filing"]["business"]["identifier"]}/filings/'
                          f'{filing_type}', json=filing)
        if not r or r.status_code != 201:
            app.logger.error(f'Filing {filing_id} not created in colin {filing["filing"]["business"]["identifier"]}.')
            # raise Exception
            return None
        # if it's an AR containing multiple filings it will have multiple colinIds
        return r.json()['filing']['header']['colinIds']


def update_colin_id(app: Flask = None, filing_id: str = None, colin_ids: list = None, token: jwt = None):
    """Update the colin_id in the filings table."""
    r = requests.patch(f'{app.config["LEGAL_URL"]}/internal/filings/{filing_id}',
                       json={'colinIds': colin_ids},
                       headers={'Authorization': f'Bearer {token}'}
                       )
    if not r or r.status_code != 202:
        app.logger.error(f'Failed to update colin id in legal db for filing {filing_id} {r.status_code}')
        return False
    else:
        return True


def clean_none(dictionary: dict = None):
    for key in dictionary.keys():
        if dictionary[key]:
            if isinstance(dictionary[key], dict):
                clean_none(dictionary[key])
        else:
            dictionary[key] = ''


def is_bcomp(identifier: str):
    return 'bc' in identifier.lower()


def is_test_coop(identifier: str):
    return 'CP1' in identifier


def run():
    application = create_app()
    corps_with_failed_filing = []
    with application.app_context():
        try:
            # get updater-job token
            token = AccountService.get_bearer_token()

            filings = get_filings(app=application)
            if not filings:
                application.logger.debug(f'No completed filings to send to colin.')
            for filing in filings:
                filing_id = filing['filingId']
                identifier = filing['filing']['business']['identifier']
                if identifier in corps_with_failed_filing or is_bcomp(identifier) or is_test_coop(identifier):
                    application.logger.debug(f'Skipping filing {filing_id} for'
                                             f' {filing["filing"]["business"]["identifier"]}.')
                else:
                    colin_ids = send_filing(app=application, filing=filing, filing_id=filing_id)
                    update = None
                    if colin_ids:
                        update = update_colin_id(app=application, filing_id=filing_id, colin_ids=colin_ids, token=token)
                    if update:
                        application.logger.debug(f'Successfully updated filing {filing_id}')
                    else:
                        corps_with_failed_filing.append(filing['filing']['business']['identifier'])
                        application.logger.error(f'Failed to update filing {filing_id} with colin event id.')

        except Exception as err:
            application.logger.error(err)


if __name__ == '__main__':
    run()
