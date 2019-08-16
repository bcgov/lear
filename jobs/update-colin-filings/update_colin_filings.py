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
from sentry_sdk.integrations.logging import LoggingIntegration  # noqa: I001
from flask import Flask
from flask_jwt_oidc import JwtManager

import config
import requests

from registry_schemas import validate
from utils.logging import setup_logging

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
    r = requests.get(f'{app.config["LEGAL_URL"]}/internal/filings')
    if not r or r.status_code != 200:
        app.logger.error(f'Failed to collect filings from legal-api. {r} {r.json()} {r.status_code}')
        raise Exception
    return r.json()


def send_filing(app: Flask = None, filing: dict = None):
    """Post to colin-api with filing."""
    clean_none(filing)
    # validate schema
    is_valid, errors = validate(filing, 'filing', validate_schema=True)
    if errors:
        for err in errors:
            app.logger.error(err.message)
        raise Exception
    else:
        filing_type = filing["filing"]["header"]["name"]
        filing_id = filing["filing"]["header"]["filingId"]
        app.logger.debug(f'Filing {filing_id} in colin for {filing["filing"]["business"]["identifier"]}.')
        r = requests.post(f'{app.config["COLIN_URL"]}/{filing["filing"]["business"]["identifier"]}/filings/'
                          f'{filing_type}', json=filing)
        if not r or r.status_code != 201:
            app.logger.error(f'Filing {filing_id} not created in colin {filing["filing"]["business"]["identifier"]}.')
            raise Exception
        # if it's an AR containing multiple filings we match it with the colin id of the AR only
        return r.json()['filing'][filing_type]['eventId']


def update_colin_id(app: Flask = None, filing_id: str = None, colin_id: str = None, token: jwt = None):
    """Update the colin_id in the filings table."""
    r = requests.patch(f'{app.config["LEGAL_URL"]}/internal/filings/{filing_id}',
                       json={'colinId': colin_id},
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


def run():
    application = create_app()

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
                colin_id = send_filing(app=application, filing=filing)
                update = update_colin_id(app=application, filing_id=filing_id, colin_id=colin_id, token=token)
                if update:
                    application.logger.error(f'Successfully updated filing {filing_id}')
                else:
                    application.logger.error(f'Failed to update filing {filing_id}')
        except Exception as err:
            application.logger.error(err)


if __name__ == "__main__":
    run()
