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


def check_for_manual_filings(cursor, application: Flask = None):
    id_list = []

    # get max colin event_id from legal_db
    try:
        cursor.execute(
            """
            select last_event_id from colin_last_update
            order by id desc 
            """
        )
        last_event_id = cursor.fetchone()

    except Exception as err:
        application.logger.error('Error getting max event id from legal db')
        raise err

    if last_event_id:
        last_event_id = str(last_event_id[0])
        # get all cp event_ids greater than above
        try:
            # call colin api for ids + filing types list
            r = requests.get(config.ProdConfig.COLIN_URL + '/event/CP/' + last_event_id)
            colin_events = dict(r.json())

        except Exception as err:
            application.logger.error('Error getting event_ids from colin')
            raise err

        # for each event_id: if not in legal db table then add event_id to list
        for info in colin_events['events']:
            # check legal table
            try:
                cursor.execute(
                    """
                    select colin_event_id
                    from filings
                    where colin_event_id={event_id}
                    """.format(event_id=info['event_id'])
                )
            except Exception as err:
                application.logger.error('Error checking colin_event_ids in legal db')
                raise err

            colin_event_id = cursor.fetchone()
            if not colin_event_id:
                id_list.append(info)

    else:
        application.logger.error('No ids returned from colin_last_update table in legal db.')

    return id_list


def get_filing(event_info: dict = None, application: Flask = None):
    # call the colin api for the filing
    if event_info['filing_typ_cd'] not in ['OTANN', 'OTADD', 'OTARG', 'OTCDR', 'OTADR']:
        application.logger.error('Error unknown filing type: {} for event id: {}'.format(
            event_info['filing_type'], event_info['event_id']))

    filing_type_dict = {'OTANN': 'annualReport',
                        'OTADD': 'changeOfAddress',
                        'OTARG': 'changeOfAddress',
                        'OTCDR': 'changeOfDirectors',
                        'OTADR': 'changeOfDirectors'
                        }
    r = requests.get(config.ProdConfig.COLIN_URL + '/{identifier}/filings/{filing_typ_cd}?eventId={event_id}'.format(
        identifier=event_info['corp_num'],
        filing_typ_cd=filing_type_dict[event_info['filing_typ_cd']],
        event_id=event_info['event_id']
    ))
    filing = dict(r.json())
    return filing


def run():
    application = create_app()

    try:
        pg_conn = psycopg2.connect(
            host=config.ProdConfig.DB_HOST,
            user=config.ProdConfig.DB_USER,
            password=config.ProdConfig.DB_PASSWORD,
            dbname=config.ProdConfig.DB_NAME
        )
        cursor = pg_conn.cursor()

        manual_filings_info = check_for_manual_filings(cursor, application)
        max_event_id = 0

        if len(manual_filings_info) > 0:
            for event_info in manual_filings_info:
                filing = get_filing(event_info, application)

                # validate schema
                is_valid, errors = validate(filing, 'filing', validate_schema=True)
                if errors:
                    for err in errors:
                        application.logger.error(err.message)

                else:
                    # call legal api with filing
                    application.logger.debug('sending filing with event info: {} to legal api.'.format(event_info))
                    with application.app_context():
                        r = requests.post(config.ProdConfig.LEGAL_URL +
                                          'api/v1/businesses/' + event_info['corp_num'] + '/filings',
                                          json=filing)
                        if r.status_code != 201:
                            application.logger.error('Legal failed to create filing with event_id {} for {}'.format(
                                event_info['corp_num'], event_info['event_id']))

                        else:
                            # update max_event_id entered
                            if int(event_info['event_id']) > max_event_id:
                                max_event_id = int(event_info['event_id'])
        else:
            application.logger.debug('0 filings updated in legal db.')

        if max_event_id > 0:
            # update max_event_id in legal_db
            application.logger.debug('setting last_event_id in legal_db to {}'.format(max_event_id))
            try:
                cursor.execute(
                    """
                    insert into colin_last_update (last_update, last_event_id)
                    values (current_timestamp, {max_event_id})
                    """.format(max_event_id=max_event_id)
                )
                pg_conn.commit()
            except Exception as err:
                application.logger.error('Error updating colin_last_update table in legal db')
                raise err

        else:
            application.logger.debug('Not updating colin_last_update in legal db.')

    except Exception as err:
        application.logger.error(err)


if __name__ == "__main__":
    run()
