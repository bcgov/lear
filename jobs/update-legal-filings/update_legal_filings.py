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
import uuid

import requests
import sentry_sdk  # noqa: I001, E501; pylint: disable=ungrouped-imports; conflicts with Flake8
from colin_api.models.business import Business
from colin_api.models.filing import Filing
from flask import Flask
from legal_api.services.bootstrap import AccountService
from legal_api.services.queue import QueueService
from legal_api.utils.datetime import datetime
from sentry_sdk.integrations.logging import LoggingIntegration  # noqa: I001

import config  # pylint: disable=import-error
from utils.logging import setup_logging  # pylint: disable=import-error

# noqa: I003

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
    # pylint: disable=redefined-outer-name, disable=too-many-branches
    """Check for colin filings in oracle."""
    id_list = []
    colin_events = None
    legal_url = application.config['LEGAL_URL']
    colin_url = application.config['COLIN_URL']
    corp_types = [Business.TypeCodes.COOP.value, Business.TypeCodes.BC_COMP.value,
                  Business.TypeCodes.ULC_COMP.value, Business.TypeCodes.CCC_COMP.value]
    no_corp_num_prefix_in_colin = [Business.TypeCodes.BC_COMP.value, Business.TypeCodes.ULC_COMP.value,
                                   Business.TypeCodes.CCC_COMP.value]

    # get max colin event_id from legal
    response = requests.get(f'{legal_url}/internal/filings/colin_id')
    if response.status_code not in [200, 404]:
        application.logger.error(f'Error getting last updated colin id from \
            legal: {response.status_code} {response.json()}')
    else:
        if response.status_code == 404:
            last_event_id = 'earliest'
        else:
            last_event_id = dict(response.json())['maxId']
        if last_event_id:
            last_event_id = str(last_event_id)
            # get all event_ids greater than above
            try:
                for corp_type in corp_types:
                    # call colin api for ids + filing types list
                    response = requests.get(f'{colin_url}/event/{corp_type}/{last_event_id}')
                    event_info = dict(response.json())
                    events = event_info.get('events')
                    if corp_type in no_corp_num_prefix_in_colin:
                        append_corp_num_prefixes(events, 'BC')
                    if colin_events:
                        colin_events.get('events').extend(events)
                    else:
                        colin_events = event_info

            except Exception as err:
                application.logger.error('Error getting event_ids from colin')
                raise err

            # for bringing in a specific filing
            # global SET_EVENTS_MANUALLY
            # SET_EVENTS_MANUALLY = True
            # colin_events = {
            #     'events': [
            #           {'corp_num': 'CP0001489', 'event_id': 102127109, 'filing_typ_cd': 'OTCGM'}
            #           {'corp_num': 'BC0702216', 'event_id': 6580760, 'filing_typ_cd': 'ANNBC'},
            #       ]
            # }

            # for each event_id: if not in legal db table then add event_id to list
            for info in colin_events['events']:
                # check that event is associated with one of the coops loaded into legal db
                response = requests.get(
                    f'{legal_url}/{info["corp_num"]}',
                    headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
                )
                if response.status_code == 200:
                    # check legal table
                    response = requests.get(f'{legal_url}/internal/filings/colin_id/{info["event_id"]}')
                    if response.status_code == 404:
                        id_list.append(info)
                    elif response.status_code != 200:
                        application.logger.error(f'Error checking for colin id {info["event_id"]} in legal')
                else:
                    application.logger.error('No ids returned from colin_last_update table in legal db.')

    return id_list


def append_corp_num_prefixes(events, corp_num_prefix):
    """Append corp num prefix to Colin corp num to make Lear compatible."""
    for event in events:
        event['corp_num'] = corp_num_prefix + event['corp_num']


def get_filing(event_info: dict = None, application: Flask = None):  # pylint: disable=redefined-outer-name
    """Get filing created by previous event."""
    # call the colin api for the filing
    legal_type = event_info['corp_num'][:2]
    filing_typ_cd = event_info['filing_typ_cd']
    filing_types = Filing.FILING_TYPES.keys()
    filing_type = \
        next((x for x in filing_types if filing_typ_cd in Filing.FILING_TYPES.get(x).get('type_code_list')), None)

    if not filing_type:
        application.logger.error('Error unknown filing type: {} for event id: {}'.format(
            event_info['filing_type'], event_info['event_id']))

    identifier = event_info['corp_num']
    event_id = event_info['event_id']
    response = requests.get(
        f'{application.config["COLIN_URL"]}/{legal_type}/{identifier}/filings/{filing_type}?eventId={event_id}'
    )
    filing = dict(response.json())
    return filing


def update_filings(application):  # pylint: disable=redefined-outer-name, too-many-branches
    """Get filings in colin that are not in lear and send them to lear."""
    successful_filings = 0
    failed_filing_events = []
    corps_with_failed_filing = []
    skipped_filings = []
    first_failed_id = None
    try:  # pylint: disable=too-many-nested-blocks
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
                    application.logger.debug(f'sending filing with event info: {event_info} to legal api.')
                    response = requests.post(
                        f'{application.config["LEGAL_URL"]}/{event_info["corp_num"]}/filings',
                        json=filing,
                        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
                    )
                    if response.status_code != 201:
                        if not first_failed_id:
                            first_failed_id = event_info['event_id']
                        failed_filing_events.append(event_info)
                        corps_with_failed_filing.append(event_info['corp_num'])
                        application.logger.error(f'Legal failed to create filing for {event_info["corp_num"]}')
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
            response = requests.post(
                f'{application.config["LEGAL_URL"]}/internal/filings/colin_id/{max_event_id}',
                headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
            )
            if response.status_code != 201:
                application.logger.error(
                    f'Error adding {max_event_id} colin_last_update table in legal db {response.status_code}'
                )
            else:
                if dict(response.json())['maxId'] != max_event_id:
                    application.logger.error('Updated colin id is not max colin id in legal db.')
                else:
                    application.logger.debug('Successfully updated colin id in legal db.')

        else:
            application.logger.debug('colin_last_update not updated in legal db.')

    except Exception as err:
        application.logger.error('Update-legal-filings: unhandled error %s', err)


async def publish_queue_events(tax_ids: dict, application: Flask):  # pylint: disable=redefined-outer-name
    """Publish events for all businesses with new tax ids (for email + entity listeners)."""
    for identifier in tax_ids.keys():
        try:
            subject = application.config['NATS_EMAILER_SUBJECT']
            payload = {'email': {'filingId': None, 'type': 'businessNumber', 'option': 'bn', 'identifier': identifier}}
            await qsm.publish_json_to_subject(payload, subject)
        except Exception as err:  # pylint: disable=broad-except, unused-variable # noqa F841;
            # mark any failure for human review
            application.logger.debug(err)
            # NB: error log will trigger sentry message
            application.logger.error('Update-legal-filings: Failed to publish bn email event for %s.', identifier)
        try:
            subject = application.config['NATS_ENTITY_EVENTS_SUBJECT']
            payload = {
                'specversion': '1.0.1',
                'type': 'bc.registry.business.bn',
                'source': 'update-legal-filings.publish_queue_events',
                'id': str(uuid.uuid4()),
                'time': datetime.utcnow().isoformat(),
                'datacontenttype': 'application/json',
                'identifier': identifier
            }
            await qsm.publish_json_to_subject(payload, subject)
        except Exception as err:  # pylint: disable=broad-except, unused-variable # noqa F841;
            # mark any failure for human review
            application.logger.debug(err)
            # NB: error log will trigger sentry message
            application.logger.error('Update-legal-filings: Failed to publish bn entity event for %s.', identifier)


async def update_business_nos(application):  # pylint: disable=redefined-outer-name
    """Update the tax_ids for corps with new bn_15s."""
    try:
        # get updater-job token
        token = AccountService.get_bearer_token()

        # get identifiers with outstanding tax_ids
        application.logger.debug('Getting businesses with outstanding tax ids from legal api...')
        response = requests.get(
            application.config['LEGAL_URL'] + '/internal/tax_ids',
            headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
        )
        if response.status_code != 200:
            application.logger.error('legal-updater failed to get identifiers from legal-api.')
            raise Exception
        identifiers = response.json()

        if identifiers['identifiers']:
            # get tax ids that exist for above entities
            application.logger.debug(f'Getting tax ids for {identifiers["identifiers"]} from colin api...')
            response = requests.get(
                application.config['COLIN_URL'] + '/internal/tax_ids',
                json=identifiers,
                headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
            )
            if response.status_code != 200:
                application.logger.error('legal-updater failed to get tax_ids from colin-api.')
                raise Exception
            tax_ids = response.json()
            if tax_ids.keys():
                # update lear with new tax ids from colin
                application.logger.debug(f'Updating tax ids for {tax_ids.keys()} in lear...')
                response = requests.post(
                    application.config['LEGAL_URL'] + '/internal/tax_ids',
                    json=tax_ids,
                    headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
                )
                if response.status_code != 201:
                    application.logger.error('legal-updater failed to update tax_ids in lear.')
                    raise Exception

                await publish_queue_events(tax_ids, application)

                application.logger.debug('Successfully updated tax ids in lear.')
            else:
                application.logger.debug('No tax ids in colin to update in lear.')
        else:
            application.logger.debug('No businesses in lear with outstanding tax ids.')

    except Exception as err:
        application.logger.error(err)


if __name__ == '__main__':
    application = create_app()
    with application.app_context():
        update_filings(application)
        event_loop = asyncio.get_event_loop()
        qsm = QueueService(app=application, loop=event_loop)
        event_loop.run_until_complete(update_business_nos(application))
