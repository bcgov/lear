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
import logging
import os

import requests
import sentry_sdk  # noqa: I001; pylint: disable=ungrouped-imports; conflicts with Flake8
from colin_api.models.filing import Filing
from legal_api.services.bootstrap import AccountService
from legal_api.services.queue import QueueService
from sentry_sdk import capture_message
from sentry_sdk.integrations.logging import LoggingIntegration  # noqa: I001
from flask import Flask

import config
from utils.logging import setup_logging

setup_logging(
    os.path.join(os.path.abspath(os.path.dirname(__file__)), 'logging.conf'))

SENTRY_LOGGING = LoggingIntegration(
    event_level=logging.ERROR  # send errors as events
)
SET_EVENTS_MANUALLY = False


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


def check_for_manual_filings(application: Flask = None, token: dict = None):
    """Check for colin filings in oracle."""
    id_list = []

    # get max colin event_id from legal
    r = requests.get(f'{application.config["LEGAL_URL"]}/internal/filings/colin_id')
    if r.status_code not in [200, 404]:
        application.logger.error(f'Error getting last updated colin id from legal: {r.status_code} {r.json()}')
    else:
        if r.status_code == 404:
            last_event_id = 'earliest'
        else:
            last_event_id = dict(r.json())['maxId']
        if last_event_id:
            last_event_id = str(last_event_id)
            # get all cp event_ids greater than above
            try:
                # call colin api for ids + filing types list
                r = requests.get(f'{application.config["COLIN_URL"]}/event/CP/{last_event_id}')
                colin_events = dict(r.json())

                # for bringing in a specific filing
                # global SET_EVENTS_MANUALLY
                # SET_EVENTS_MANUALLY = True
                # colin_events = {
                #     'events': [{'corp_num': 'CP0001489', 'event_id': 102127109, 'filing_typ_cd': 'OTCGM'}]
                # }

            except Exception as err:
                application.logger.error('Error getting event_ids from colin')
                raise err

            # for each event_id: if not in legal db table then add event_id to list
            for info in colin_events['events']:
                # check that event is associated with one of the coops loaded into legal db
                r = requests.get(
                    f'{application.config["LEGAL_URL"]}/{info["corp_num"]}',
                    headers={'Content-Type': 'application/json','Authorization': f'Bearer {token}'}
                )
                if r.status_code == 200:
                    # check legal table
                    r = requests.get(f'{application.config["LEGAL_URL"]}/internal/filings/colin_id/{info["event_id"]}')
                    if r.status_code == 404:
                        id_list.append(info)
                    elif r.status_code != 200:
                        application.logger.error(f'Error checking for colin id {info["event_id"]} in legal')

        else:
            application.logger.error('No ids returned from colin_last_update table in legal db.')

    return id_list


def get_filing(event_info: dict = None, application: Flask = None):
    # call the colin api for the filing
    legal_type = event_info['corp_num'][:2]
    if event_info['filing_typ_cd'] not in Filing.FILING_TYPES[legal_type].keys():
        application.logger.error('Error unknown filing type: {} for event id: {}'.format(
            event_info['filing_type'], event_info['event_id']))

    r = requests.get(f'{application.config["COLIN_URL"]}/{event_info["corp_num"]}/filings/'
                     f'{Filing.FILING_TYPES[legal_type][event_info["filing_typ_cd"]]}?eventId={event_info["event_id"]}')
    filing = dict(r.json())
    return filing


def update_filings(application):
    successful_filings = 0
    failed_filing_events = []
    corps_with_failed_filing = []
    skipped_filings = []
    first_failed_id = None
    try:
        # get updater-job token
        token = AccountService.get_bearer_token()

        # check if there are filings to send to legal
        manual_filings_info = check_for_manual_filings(application, token)
        max_event_id = 0

        if len(manual_filings_info) > 0:
            for event_info in manual_filings_info:
                # Make sure this coop has no outstanding filings that failed to be applied.
                # This ensures we don't apply filings out of order when one fails.
                if event_info['corp_num'] not in corps_with_failed_filing:
                    filing = get_filing(event_info, application)

                    # call legal api with filing
                    application.logger.debug('sending filing with event info: {} to legal api.'.format(event_info))
                    r = requests.post(application.config['LEGAL_URL'] + '/' + event_info['corp_num'] + '/filings',
                                        json=filing, headers={'Content-Type': 'application/json',
                                                            'Authorization': f'Bearer {token}'})
                    if r.status_code != 201:
                        if not first_failed_id:
                            first_failed_id = event_info['event_id']
                        failed_filing_events.append(event_info)
                        corps_with_failed_filing.append(event_info['corp_num'])
                        application.logger.error(f'{r.json()} {r.status_code}')
                        application.logger.error(f'Legal failed to create filing with event_id '
                                                    f'{event_info["event_id"]} for {event_info["corp_num"]}')
                    else:
                        # update max_event_id entered
                        successful_filings += 1
                        if int(event_info['event_id']) > max_event_id:
                            max_event_id = int(event_info['event_id'])
                else:
                    skipped_filings.append(event_info)
        else:
            application.logger.debug('0 filings updated in legal db.')

        application.logger.debug(f'successful filings: {successful_filings}')
        application.logger.debug(f'skipped filings due to related erred filings: {len(skipped_filings)}')
        application.logger.debug(f'failed filings: {len(failed_filing_events)}')
        application.logger.debug(f'failed filings event info: {failed_filing_events}')

        # if manually bringing across filings, set to first id so you don't skip any filings on the next run
        if SET_EVENTS_MANUALLY:
            first_failed_id = 102125621

        # if one of the events failed then save that id minus one so that the next run will try it again
        # this way failed filings wont get buried/forgotten after multiple runs
        if first_failed_id:
            max_event_id = first_failed_id - 1
        if max_event_id > 0:
            # update max_event_id in legal_db
            application.logger.debug('setting last_event_id in legal_db to {}'.format(max_event_id))
            r = requests.post(f'{application.config["LEGAL_URL"]}/internal/filings/colin_id/{max_event_id}',
                                headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'})
            if r.status_code != 201:
                application.logger.error(f'Error adding {max_event_id} colin_last_update table in legal db '
                                            f'{r.status_code}')
            else:
                if dict(r.json())['maxId'] != max_event_id:
                    application.logger.error(f'Updated colin id is not max colin id in legal db.')
                else:
                    application.logger.debug(f'Successfully updated colin id in legal db.')

        else:
            application.logger.debug('colin_last_update not updated in legal db.')

    except Exception as err:
        application.logger.error(err)


async def send_emails(tax_ids: dict, application: Flask):
    """Put bn email messages on the queue for all businesses with new tax ids."""
    for identifier in tax_ids.keys():
        try:
            subject = application.config['EMAIL_PUBLISH_OPTIONS']['subject']
            payload = {'email': {'filingId': None, 'type': 'businessNumber', 'option': 'bn', 'identifier': identifier}}
            await qsm.publish_json_to_subject(payload, subject)
        except Exception as err:  # pylint: disable=broad-except, unused-variable # noqa F841;
            # mark any failure for human review
            capture_message(
                f'Queue Error: Failed to place bn email for {identifier}'
                f' on Queue with error:{err}',
                level='error'
            )


async def update_business_nos(application):
    """Update the tax_ids for corps with new bn_15s."""
    try:
        # get updater-job token
        token = AccountService.get_bearer_token()

        # get identifiers with outstanding tax_ids
        application.logger.debug('Getting businesses with outstanding tax ids from legal api...')
        r = requests.get(
            application.config['LEGAL_URL'] + '/internal/tax_ids',
            headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
        )
        if r.status_code != 200:
            application.logger.error(f'legal-updater failed to get identifiers from legal-api.')
            raise Exception
        identifiers = r.json()

        if identifiers['identifiers']:
            # get tax ids that exist for above entities
            application.logger.debug(f'Getting tax ids for {identifiers["identifiers"]} from colin api...')
            r = requests.get(
                application.config['COLIN_URL'] + '/internal/tax_ids',
                json=identifiers,
                headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
            )
            if r.status_code != 200:
                application.logger.error(f'legal-updater failed to get tax_ids from colin-api.')
                raise Exception
            tax_ids = r.json()
            if tax_ids.keys():
                # update lear with new tax ids from colin
                application.logger.debug(f'Updating tax ids for {tax_ids.keys()} in lear...')
                r = requests.post(
                    application.config['LEGAL_URL'] + '/internal/tax_ids',
                    json=tax_ids,
                    headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
                )
                if r.status_code != 201:
                    application.logger.error(f'legal-updater failed to update tax_ids in lear.')
                    raise Exception

                await send_emails(tax_ids, application)

                application.logger.debug(f'Successfully updated tax ids in lear.')
            else:
                application.logger.debug(f'No tax ids in colin to update in lear.')
        else:
            application.logger.debug(f'No businesses in lear with outstanding tax ids.')

    except Exception as err:
        application.logger.error(err)


if __name__ == '__main__':
    application = create_app()
    with application.app_context():
        update_filings(application)
        event_loop = asyncio.get_event_loop()
        qsm = QueueService(app=application, loop=event_loop)
        event_loop.run_until_complete(update_business_nos(application))
