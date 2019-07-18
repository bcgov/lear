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
import os

from flask import Flask, jsonify
from flask_jwt_oidc import JwtManager
from registry_schemas import validate
import requests
import config
from utils.logging import setup_logging
import psycopg2

setup_logging(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'logging.conf'))  # important to do this first

# lower case name as used by convention in most Flask apps
jwt = JwtManager()  # pylint: disable=invalid-name


def create_app(run_mode=os.getenv('FLASK_ENV', 'production')):
    """Return a configured Flask App using the Factory method."""
    app = Flask(__name__)
    app.config.from_object(config.CONFIGURATION[run_mode])

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
                          f'{filing_type}', json={'filing': filing['filing']})
        if not r or r.status_code != 201:
            app.logger.error(f'Filing {filing_id} not created in colin {filing["filing"]["business"]["identifier"]}.')
            raise Exception
        # if it's an AR containing multiple filings we match it with the colin id of the AR only
        return r.json()['filing'][filing_type]['eventId']


def update_colin_id(app: Flask = None, filing_id: str = None, colin_id: str = None):
    """Update the colin_id in the filings table."""
    r = requests.patch(f'{app.config["LEGAL_URL"]}/internal/filings/{filing_id}', json={'colinId': colin_id})
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
            # filing_params = check_completed_filings()
            # for params in filing_params:
            filings = get_filings(app=application)
            if not filings:
                application.logger.debug(f'No completed filings to send to colin.')
            for filing in filings:
                filing_id = filing["filing"]["header"]["filingId"]
                colin_id = send_filing(app=application, filing=filing)
                update = update_colin_id(app=application, filing_id=filing_id, colin_id=colin_id)
                if update:
                    application.logger.error(f'Successfully updated filing {filing_id}')
                else:
                    application.logger.error(f'Failed to update filing {filing_id}')
        except Exception as err:
            application.logger.error(err)


if __name__ == "__main__":
    run()
