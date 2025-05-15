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
import sys
import uuid

import dateutil
import pytz
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
CONTENT_TYPE_JSON = 'application/json'


def create_app(run_mode=os.getenv('FLASK_ENV', 'production')):
    """Return a configured Flask App using the Factory method."""
    application = Flask(__name__)
    application.config.from_object(config.CONFIGURATION[run_mode])
    # Configure Sentry
    if application.config.get('SENTRY_DSN', None):
        sentry_sdk.init(
            dsn=application.config.get('SENTRY_DSN'),
            integrations=[SENTRY_LOGGING]
        )

    register_shellcontext(application)

    # Static class load the variables while importing the class for the first time,
    # By then config is not loaded, so it never get the config value
    AccountService.timeout = int(application.config.get('ACCOUNT_SVC_TIMEOUT'))

    return application


def register_shellcontext(application):
    """Register shell context objects."""
    def shell_context():
        """Shell context objects."""
        return {'app': application}

    application.shell_context_processor(shell_context)


def check_for_manual_filings(application: Flask = None, token: dict = None):
    # pylint: disable=redefined-outer-name, disable=too-many-branches, disable=too-many-locals
    """Check for colin filings in oracle."""
    id_list = []
    colin_events = None
    legal_url = application.config['LEGAL_API_URL'] + '/businesses'
    colin_url = application.config['COLIN_URL']
    corp_types = [Business.TypeCodes.COOP.value]

    # get max colin event_id from legal
    response = requests.get(f'{legal_url}/internal/filings/colin_id',
                            headers={'Content-Type': CONTENT_TYPE_JSON, 'Authorization': f'Bearer {token}'},
                            timeout=AccountService.timeout)
    if response.status_code not in [200, 404]:
        application.logger.error(f'Error getting last updated colin id from \
            legal: {response.status_code} {response.json()}')
    else:
        if response.status_code == 404:
            last_event_id = 'earliest'
        else:
            last_event_id = dict(response.json())['maxId']
        application.logger.debug(f'last_event_id: {last_event_id}')
        if last_event_id:
            last_event_id = str(last_event_id)
            # get all event_ids greater than above
            try:
                for corp_type in corp_types:
                    application.logger.debug(f'corp_type: {corp_type}')
                    url = f'{colin_url}/event/{corp_type}/{last_event_id}'
                    application.logger.debug(f'url: {url}')
                    # call colin api for ids + filing types list
                    response = requests.get(url,
                                            headers={**AccountService.CONTENT_TYPE_JSON,
                                                     'Authorization': AccountService.BEARER + token},
                                            timeout=AccountService.timeout)
                    event_info = dict(response.json())
                    events = event_info.get('events')
                    if colin_events:
                        colin_events.get('events').extend(events)
                    else:
                        colin_events = event_info

            except Exception as err:  # noqa: B902
                application.logger.error('Error getting event_ids from colin: %s', repr(err), exc_info=True)
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
                    headers={'Content-Type': CONTENT_TYPE_JSON, 'Authorization': f'Bearer {token}'},
                    timeout=AccountService.timeout
                )
                if response.status_code == 200:
                    # check legal table
                    response = requests.get(
                        f'{legal_url}/internal/filings/colin_id/{info["event_id"]}',
                        headers={'Content-Type': CONTENT_TYPE_JSON, 'Authorization': f'Bearer {token}'},
                        timeout=AccountService.timeout)
                    if response.status_code == 404:
                        id_list.append(info)
                    elif response.status_code != 200:
                        application.logger.error(f'Error checking for colin id {info["event_id"]} in legal')
                else:
                    application.logger.error('No ids returned from colin_last_update table in legal db.')

    return id_list


def get_filing(event_info: dict = None, application: Flask = None, token: dict = None):
    """Get filing created by previous event."""
    # call the colin api for the filing
    legal_type = event_info['corp_num'][:2]
    filing_typ_cd = event_info['filing_typ_cd']
    filing_types = Filing.FILING_TYPES.keys()
    filing_type = \
        next((x for x in filing_types if filing_typ_cd in Filing.FILING_TYPES.get(x).get('type_code_list')), None)

    if not filing_type:
        # pylint: disable=consider-using-f-string
        application.logger.error('Error unknown filing type: {} for event id: {}'.format(
            event_info['filing_type'], event_info['event_id']))

    identifier = event_info['corp_num']
    event_id = event_info['event_id']
    response = requests.get(
        f'{application.config["COLIN_URL"]}/{legal_type}/{identifier}/filings/{filing_type}?eventId={event_id}',
        headers={**AccountService.CONTENT_TYPE_JSON,
                 'Authorization': AccountService.BEARER + token},
        timeout=AccountService.timeout
    )
    filing = dict(response.json())
    return filing


def _get_correction_filing(application, token, event_info):
    response = requests.get(
        application.config['LEGAL_API_URL'] + f'/businesses/{event_info["corp_num"]}/filings',
        headers={'Content-Type': CONTENT_TYPE_JSON, 'Authorization': f'Bearer {token}'},
        timeout=AccountService.timeout
    )
    if response.status_code != 200:
        application.logger.error('legal-updater failed to get filings from legal-api.')
        raise Exception  # pylint: disable=broad-exception-raised
    filings = response.json()

    if event_info['corp_num'] == 'BC1302455':
        filing = filings['filings'][-1]
    else:
        filing = filings['filings'][0]

    return filing['name'], filing['filingId']


def _format_filing(application, token, filing, event_info):  # pylint: disable=too-many-branches
    filing['filing']['business']['identifier'] = event_info['corp_num']
    filing['filing']['business']['adminFreeze'] = filing['filing']['business']['adminFreeze'] == 'True'
    del filing['filing']['business']['goodStanding']
    tz = pytz.timezone('America/Vancouver')
    if filing['filing']['header']['name'] == 'annualReport':
        for director in filing['filing']['annualReport']['directors']:
            if (appointment_date := director.get('appointmentDate', None)) and len(appointment_date) > 10:
                director['appointmentDate'] = dateutil.parser.parse(
                    director['appointmentDate']).astimezone(tz).date().isoformat()
            if (cessation_date := director.get('cessationDate', None)) and len(cessation_date) > 10:
                director['cessationDate'] = dateutil.parser.parse(
                    director['cessationDate']).astimezone(tz).date().isoformat()
    elif (filing['filing']['header']['name'] == 'alteration' and
            'shareStructure' in filing['filing']['alteration']):
        for share_class in filing['filing']['alteration']['shareStructure'].get('shareClasses', []):
            if not share_class.get('hasParValue', False):
                share_class['parValue'] = None
                share_class['currency'] = None
            if not share_class['hasMaximumShares']:
                share_class['maxNumberOfShares'] = None

            for series in share_class.get('series', []):
                if not series['hasMaximumShares']:
                    series['maxNumberOfShares'] = None
    elif filing['filing']['header']['name'] == 'correction':
        if 'parties' in filing['filing']['correction']:
            filing_type, filing_id = _get_correction_filing(application, token, event_info)
            filing['filing']['correction']['correctedFilingId'] = filing_id
            filing['filing']['correction']['correctedFilingType'] = filing_type
    # elif filing['filing']['header']['name'] == 'dissolution':
    #     filing['filing']['dissolution']['dissolutionDate'] = dateutil.parser.parse(
    #         filing['filing']['dissolution']['dissolutionDate']).astimezone(tz).date().isoformat()
    #     filing['filing']['dissolution']['dissolutionType'] = 'voluntary'
    #     del filing['filing']['dissolution']['parties'][0]
    #     for party in filing['filing']['dissolution']['parties']:
    #         for role in party['roles']:
    #             if (appointment_date := role.get('appointmentDate', None)) and len(appointment_date) > 10:
    #                 role['appointmentDate'] = dateutil.parser.parse(
    #                     role['appointmentDate']).astimezone(tz).date().isoformat()
    #         party['mailingAddress'] = filing['filing']['dissolution']['custodialOffice']['mailingAddress']
    #         party['deliveryAddress'] = filing['filing']['dissolution']['custodialOffice']['deliveryAddress']
    #         del filing['filing']['dissolution']['custodialOffice']


def _get_ben_to_bc_identifiers():
    """Get businesses altered from ben to bc before directed launch."""
    businesses = [
        'BC1451276', 'BC1442586', 'BC1439130', 'BC1438581', 'BC1434638', 'BC1432515', 'BC1431198', 'BC1431006',
        'BC1430801', 'BC0460007', 'BC1423066', 'BC1419940', 'BC1419778', 'BC1419580', 'BC1416696', 'BC1412435',
        'BC1411665', 'BC1409970', 'BC1409968', 'BC1409966', 'BC1403023', 'BC1402458', 'BC1402422', 'BC1396800',
        'BC1396795', 'BC1396177', 'BC1396133', 'BC1395749', 'BC1393563', 'BC1392185', 'BC1391097', 'BC1390906',
        'BC1255957', 'BC1387965', 'BC1387943', 'BC1387232', 'BC1386102', 'BC1385653', 'BC1385498', 'BC1385337',
        'BC1384652', 'BC1381964', 'BC1379279', 'BC1374932', 'BC1373942', 'BC1373092', 'BC1372867', 'BC1372240',
        'BC1371754', 'BC1371596', 'BC1363995', 'BC1357406', 'BC1354255', 'BC1349489', 'BC1349238', 'BC1347809',
        'BC1345597', 'BC1342762', 'BC1342086', 'BC1336861', 'BC1331964', 'BC1324998', 'BC1324894', 'BC1324889',
        'BC1324221', 'BC1321272', 'BC1314465', 'BC1313713', 'BC1313658', 'BC1313261', 'BC1310531', 'BC1310221',
        'BC1309930', 'BC1309597', 'BC1308329', 'BC1186381', 'BC1306000', 'BC1304018', 'BC1303233', 'BC1302541',
        'BC1302455', 'BC1294238', 'BC1294095', 'BC1292965', 'BC1291871', 'BC1280573', 'BC1278342', 'BC1268600',
        'BC1265645', 'BC1263326', 'BC1263195', 'BC1260267', 'BC1281607', 'BC1422277', 'BC1403939', 'BC1405285']
    return businesses


def check_ben_to_bc_filings(application, token):
    """Check for new filings in COLIN."""
    legal_url = application.config['LEGAL_API_URL'] + '/businesses'
    colin_url = application.config['COLIN_URL']
    colin_events = []
    businesses = _get_ben_to_bc_identifiers()
    for identifier in businesses:
        # Get the last colin event id for the identifier
        response = requests.get(
            f'{legal_url}/internal/last-event-id/{identifier}',
            headers={'Content-Type': CONTENT_TYPE_JSON, 'Authorization': f'Bearer {token}'},
            timeout=AccountService.timeout)
        last_event_id = response.json()['maxId']

        # check if there are filings to send to legal
        colin_identifier = identifier[2:]
        response = requests.get(
            f'{colin_url}/event/corp_num/{colin_identifier}/{last_event_id}',
            headers={'Content-Type': CONTENT_TYPE_JSON, 'Authorization': f'Bearer {token}'},
            timeout=AccountService.timeout
        )
        if response.status_code != 200:
            application.logger.error('legal-updater failed to get filings from colin-api.')
            raise Exception  # pylint: disable=broad-exception-raised
        event_info = dict(response.json())
        events = event_info.get('events')
        for event in events:
            # None filing_typ_cd found in 'BC1294238', 'BC1265645', 'BC1263326', 'BC1263195' without filings
            if event['filing_typ_cd'] not in ['COGS1', None]:
                event['corp_num'] = identifier
                colin_events.append(event)
    return colin_events


def update_ben_to_bc(application):  # pylint: disable=redefined-outer-name, too-many-branches
    """Get filings in colin that are not in lear and send them to lear."""
    successful_filings = 0
    failed_filing_events = []
    corps_with_failed_filing = []
    skipped_filings = []
    try:
        token = AccountService.get_bearer_token()
        manual_filings_info = check_ben_to_bc_filings(application, token)

        if len(manual_filings_info) > 0:
            for event_info in manual_filings_info:
                if event_info['corp_num'] not in corps_with_failed_filing:
                    filing = get_filing(event_info, application, token)
                    if (filing['filing']['header']['name'] == 'annualReport' and
                            'parties' in filing['filing']['annualReport']):
                        application.logger.debug(
                            f'{event_info["corp_num"]}: Officer party type is not implemented in legal-api yet.')
                        corps_with_failed_filing.append(event_info['corp_num'])
                        continue

                    _format_filing(application, token, filing, event_info)

                    # call legal api with filing
                    application.logger.debug(f'sending filing with event info: {event_info} to legal api.')
                    response = requests.post(
                        f'{application.config["LEGAL_API_URL"]}/businesses/{event_info["corp_num"]}/filings',
                        json=filing,
                        headers={'Content-Type': CONTENT_TYPE_JSON, 'Authorization': f'Bearer {token}'},
                        timeout=AccountService.timeout
                    )
                    if response.status_code != 201:
                        failed_filing_events.append(event_info)
                        corps_with_failed_filing.append(event_info['corp_num'])
                        application.logger.error(f'Legal failed to create filing for {event_info["corp_num"]}')
                    else:
                        successful_filings += 1
                else:
                    skipped_filings.append(event_info)

        application.logger.debug(f'successful filings: {successful_filings}')
        application.logger.debug(f'skipped filings due to related erred filings: {len(skipped_filings)}')
        application.logger.debug(f'failed filings: {len(failed_filing_events)}')
        application.logger.debug(f'failed filings event info: {failed_filing_events}')

    except Exception as err:  # noqa: B902
        application.logger.error('Update-legal-filings: unhandled error %s', err)


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
                    filing = get_filing(event_info, application, token)

                    # call legal api with filing
                    application.logger.debug(f'sending filing with event info: {event_info} to legal api.')
                    response = requests.post(
                        f'{application.config["LEGAL_API_URL"]}/businesses/{event_info["corp_num"]}/filings',
                        json=filing,
                        headers={'Content-Type': CONTENT_TYPE_JSON, 'Authorization': f'Bearer {token}'},
                        timeout=AccountService.timeout
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
                        max_event_id = max(max_event_id, int(event_info['event_id']))
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
            application.logger.debug(f'setting last_event_id in legal_db to {max_event_id}')
            response = requests.post(
                f'{application.config["LEGAL_API_URL"]}/businesses/internal/filings/colin_id/{max_event_id}',
                headers={'Content-Type': CONTENT_TYPE_JSON, 'Authorization': f'Bearer {token}'},
                timeout=AccountService.timeout
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

    except Exception as err:  # noqa: B902
        application.logger.error('Update-legal-filings: unhandled error %s', err)


async def publish_queue_events(qsm, tax_ids: dict, application: Flask):  # pylint: disable=redefined-outer-name
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
                'datacontenttype': CONTENT_TYPE_JSON,
                'identifier': identifier
            }
            await qsm.publish_json_to_subject(payload, subject)
        except Exception as err:  # pylint: disable=broad-except, unused-variable # noqa F841;
            # mark any failure for human review
            application.logger.debug(err)
            # NB: error log will trigger sentry message
            application.logger.error('Update-legal-filings: Failed to publish bn entity event for %s.', identifier)


async def update_business_nos(application, qsm):  # pylint: disable=redefined-outer-name
    """Update the tax_ids for corps with new bn_15s."""
    try:
        # get updater-job token
        token = AccountService.get_bearer_token()

        # get identifiers with outstanding tax_ids
        application.logger.debug('Getting businesses with outstanding tax ids from legal api...')
        response = requests.get(
            application.config['LEGAL_API_URL'] + '/businesses/internal/tax_ids',
            headers={'Content-Type': CONTENT_TYPE_JSON, 'Authorization': f'Bearer {token}'},
            timeout=AccountService.timeout
        )
        if response.status_code != 200:
            application.logger.error('legal-updater failed to get identifiers from legal-api.')
            raise Exception  # pylint: disable=broad-exception-raised
        business_identifiers = response.json()

        if business_identifiers['identifiers']:
            start = 0
            end = 20
            # make a colin-api call with 20 identifiers at a time
            while identifiers := business_identifiers['identifiers'][start:end]:
                start = end
                end += 20
                # get tax ids that exist for above entities
                application.logger.debug(f'Getting tax ids for {identifiers} from colin api...')
                response = requests.get(
                    application.config['COLIN_URL'] + '/internal/tax_ids',
                    json={'identifiers': identifiers},
                    headers={'Content-Type': CONTENT_TYPE_JSON, 'Authorization': f'Bearer {token}'},
                    timeout=AccountService.timeout
                )
                if response.status_code != 200:
                    application.logger.error('legal-updater failed to get tax_ids from colin-api.')
                    raise Exception  # pylint: disable=broad-exception-raised
                tax_ids = response.json()
                if tax_ids.keys():
                    # update lear with new tax ids from colin
                    application.logger.debug(f'Updating tax ids for {tax_ids.keys()} in lear...')
                    response = requests.post(
                        application.config['LEGAL_API_URL'] + '/businesses/internal/tax_ids',
                        json=tax_ids,
                        headers={'Content-Type': CONTENT_TYPE_JSON, 'Authorization': f'Bearer {token}'},
                        timeout=AccountService.timeout
                    )
                    if response.status_code != 201:
                        application.logger.error('legal-updater failed to update tax_ids in lear.')
                        raise Exception  # pylint: disable=broad-exception-raised

                    await publish_queue_events(qsm, tax_ids, application)

                    application.logger.debug('Successfully updated tax ids in lear.')
                else:
                    application.logger.debug('No tax ids in colin to update in lear.')
        else:
            application.logger.debug('No businesses in lear with outstanding tax ids.')

    except Exception as err:  # noqa: B902
        application.logger.error(err)


if __name__ == '__main__':
    is_bc_to_ben = sys.argv[1] == 'bc-to-ben' if sys.argv and len(sys.argv) > 1 else False
    app = create_app()
    with app.app_context():
        if is_bc_to_ben:
            update_ben_to_bc(app)
        else:
            update_filings(app)
            event_loop = asyncio.get_event_loop()
            qsm = QueueService(app=app, loop=event_loop)
            event_loop.run_until_complete(update_business_nos(app, qsm))
