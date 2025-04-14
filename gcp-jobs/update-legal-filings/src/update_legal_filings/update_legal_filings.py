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
import os
import uuid
from http import HTTPStatus

import requests
import simple_cloudevent
from business_account.AccountService import AccountService
from colin_api.models.business import Business
from colin_api.models.filing import Filing
from dotenv import find_dotenv, load_dotenv
from flask import Flask, current_app
from legal_api.utils.datetime import datetime
from simple_cloudevent import to_queue_message

from gcp_queue import GcpQueue
from structured_logging import StructuredLogging
from update_legal_filings import get_named_config

SET_EVENTS_MANUALLY = False
CONTENT_TYPE_JSON = "application/json"
DEFAULT_CONNECT_TIMEOUT = 2
STATUS_OK = 200
gcp_queue = GcpQueue()

# this will load all the envars from a .env file located in the project root
load_dotenv(find_dotenv())
run_mode = os.getenv("FLASK_ENV", "production")

def create_app(run_mode=run_mode):
    """Return a configured Flask App using the Factory method."""
    app = Flask(__name__)
    app.config.from_object(get_named_config(run_mode))
    gcp_queue.init_app(app)
    app.logger = StructuredLogging(app).get_logger()

    # todo: do we need this ?
    # register_shellcontext(application)

    # Static class load the variables while importing the class for the first time,
    # By then config is not loaded, so it never get the config value
    AccountService.timeout = int(app.config.get("ACCOUNT_SVC_TIMEOUT"))

    return app


# todo: do we need this ?
# def register_shellcontext(application):
#     """Register shell context objects."""
#     def shell_context():
#         """Shell context objects."""
#         return {'app': application}
#
#     application.shell_context_processor(shell_context)


def _get_ce(data):
    """Return a SimpleCloudEvent object."""
    return simple_cloudevent.SimpleCloudEvent(
        id=str(uuid.uuid4()),
        type="bc.registry.business.bn",
        source="update-legal-filings.update_business_nos",
        subject="bn-update-identifier",
        time=datetime.utcnow().isoformat(),
        data=data
    )

def check_for_manual_filings(application: Flask = None, token: dict = None):
    # pylint: disable=redefined-outer-name, disable=too-many-branches, disable=too-many-locals
    """Check for colin filings in oracle."""
    id_list = []
    colin_events = None
    legal_url = application.config["LEGAL_API_URL"] + "/businesses"
    colin_url = application.config["COLIN_URL"]
    corp_types = [Business.TypeCodes.COOP.value]

    # get max colin event_id from legal
    response = requests.get(f"{legal_url}/internal/filings/colin_id",
                            headers={"Content-Type": CONTENT_TYPE_JSON, "Authorization": f"Bearer {token}"},
                            timeout=AccountService.timeout)
    if response.status_code not in [HTTPStatus.OK, HTTPStatus.NOT_FOUND]:
        application.logger.error(f"Error getting last updated colin id from \
            legal: {response.status_code} {response.json()}")
    else:
        if response.status_code == 404:
            last_event_id = "earliest"
        else:
            last_event_id = dict(response.json())["maxId"]
        application.logger.debug(f"last_event_id: {last_event_id}")
        if last_event_id:
            last_event_id = str(last_event_id)
            # get all event_ids greater than above
            try:
                for corp_type in corp_types:
                    application.logger.debug(f"corp_type: {corp_type}")
                    url = f"{colin_url}/event/{corp_type}/{last_event_id}"
                    application.logger.debug(f"url: {url}")
                    # call colin api for ids + filing types list
                    response = requests.get(url,
                                            headers={**AccountService.CONTENT_TYPE_JSON,
                                                     "Authorization": AccountService.BEARER + token},
                                            timeout=AccountService.timeout)
                    event_info = dict(response.json())
                    events = event_info.get("events")
                    if colin_events:
                        colin_events.get("events").extend(events)
                    else:
                        colin_events = event_info

            except Exception as err:
                application.logger.error("Error getting event_ids from colin: %s", repr(err), exc_info=True)
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
            for info in colin_events["events"]:
                # check that event is associated with one of the coops loaded into legal db
                response = requests.get(
                    f'{legal_url}/{info["corp_num"]}',
                    headers={"Content-Type": CONTENT_TYPE_JSON, "Authorization": f"Bearer {token}"},
                    timeout=AccountService.timeout
                )
                if response.status_code == 200:
                    # check legal table
                    response = requests.get(
                        f'{legal_url}/internal/filings/colin_id/{info["event_id"]}',
                        headers={"Content-Type": CONTENT_TYPE_JSON, "Authorization": f"Bearer {token}"},
                        timeout=AccountService.timeout)
                    if response.status_code == 404:
                        id_list.append(info)
                    elif response.status_code != 200:
                        application.logger.error(f'Error checking for colin id {info["event_id"]} in legal')
                else:
                    application.logger.error("No ids returned from colin_last_update table in legal db.")

    return id_list


def get_filing(event_info: dict = None, application: Flask = None, token: dict = None) -> dict:
    """Get filing created by previous event."""
    # call the colin api for the filing
    legal_type = event_info["corp_num"][:2]
    filing_typ_cd = event_info["filing_typ_cd"]
    filing_types = Filing.FILING_TYPES.keys()
    filing_type = \
        next((x for x in filing_types if filing_typ_cd in Filing.FILING_TYPES.get(x).get("type_code_list")), None)

    if not filing_type:
        # pylint: disable=consider-using-f-string
        application.logger.error("Error unknown filing type: {} for event id: {}".format(
            event_info["filing_type"], event_info["event_id"]))

    identifier = event_info["corp_num"]
    event_id = event_info["event_id"]
    response = requests.get(
        f'{application.config["COLIN_URL"]}/{legal_type}/{identifier}/filings/{filing_type}?eventId={event_id}',
        headers={**AccountService.CONTENT_TYPE_JSON,
                 "Authorization": AccountService.BEARER + token},
        timeout=AccountService.timeout
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
                if event_info["corp_num"] not in corps_with_failed_filing:
                    filing = get_filing(event_info, application, token)

                    # call legal api with filing
                    application.logger.debug(f"sending filing with event info: {event_info} to legal api.")
                    response = requests.post(
                        f'{application.config["LEGAL_API_URL"]}/businesses/{event_info["corp_num"]}/filings',
                        json=filing,
                        headers={"Content-Type": CONTENT_TYPE_JSON, "Authorization": f"Bearer {token}"},
                        timeout=AccountService.timeout
                    )
                    if response.status_code != 201:
                        if not first_failed_id:
                            first_failed_id = event_info["event_id"]
                        failed_filing_events.append(event_info)
                        corps_with_failed_filing.append(event_info["corp_num"])
                        application.logger.error(f'Legal failed to create filing for {event_info["corp_num"]}')
                    else:
                        # update max_event_id entered
                        successful_filings += 1
                        max_event_id = max(max_event_id, int(event_info["event_id"]))
                else:
                    skipped_filings.append(event_info)
        else:
            application.logger.debug("0 filings updated in legal db.")

        application.logger.debug(f"successful filings: {successful_filings}")
        application.logger.debug(f"skipped filings due to related erred filings: {len(skipped_filings)}")
        application.logger.debug(f"failed filings: {len(failed_filing_events)}")
        application.logger.debug(f"failed filings event info: {failed_filing_events}")

        # if manually bringing across filings, set to first id so you don't skip any filings on the next run
        if SET_EVENTS_MANUALLY:
            first_failed_id = 102125621

        # if one of the events failed then save that id minus one so that the next run will try it again
        # this way failed filings wont get buried/forgotten after multiple runs
        if first_failed_id:
            max_event_id = first_failed_id - 1
        if max_event_id > 0:
            # update max_event_id in legal_db
            application.logger.debug(f"setting last_event_id in legal_db to {max_event_id}")
            response = requests.post(
                f'{application.config["LEGAL_API_URL"]}/businesses/internal/filings/colin_id/{max_event_id}',
                headers={"Content-Type": CONTENT_TYPE_JSON, "Authorization": f"Bearer {token}"},
                timeout=AccountService.timeout
            )
            if response.status_code != 201:
                application.logger.error(
                    f"Error adding {max_event_id} colin_last_update table in legal db {response.status_code}"
                )
            elif dict(response.json())["maxId"] != max_event_id:
                application.logger.error("Updated colin id is not max colin id in legal db.")
            else:
                application.logger.debug("Successfully updated colin id in legal db.")

        else:
            application.logger.debug("colin_last_update not updated in legal db.")

    except Exception as err:
        application.logger.error("Update-legal-filings: unhandled error %s", err)


async def publish_queue_events(tax_ids: dict, application: Flask):  # pylint: disable=redefined-outer-name
    """Publish events for all businesses with new tax ids (for email + entity listeners)."""
    for identifier in tax_ids:
        try:
            emailer_topic = application.config["BUSINESS_EMAILER_TOPIC"]
            payload = {"email": {"filingId": None, "type": "businessNumber", "option": "bn", "identifier": identifier}}

            mailer_ce = _get_ce(payload)

            gcp_queue.publish(emailer_topic, to_queue_message(mailer_ce))
        except Exception as err:  # pylint: disable=broad-except, unused-variable
            # mark any failure for human review
            application.logger.debug(err)
            # NB: error log will trigger sentry message
            application.logger.error("Update-legal-filings: Failed to publish bn email event for %s.", identifier)
        try:
            data={
                "identifier": identifier
            }

            ce = _get_ce(data)

            business_event_topic = current_app.config.get("BUSINESS_EVENTS_TOPIC")
            gcp_queue.publish(business_event_topic, to_queue_message(ce))
        except Exception as err:  # pylint: disable=broad-except, unused-variable
            # mark any failure for human review
            application.logger.debug(err)
            # NB: error log will trigger sentry message
            application.logger.error("Update-legal-filings: Failed to publish bn entity event for %s.", identifier)


async def update_business_nos(application):  # pylint: disable=redefined-outer-name
    """Update the tax_ids for corps with new bn_15s."""
    try:
        # get updater-job token
        token = AccountService.get_bearer_token()

        # get identifiers with outstanding tax_ids
        application.logger.debug("Getting businesses with outstanding tax ids from legal api...")
        response = requests.get(
            application.config["LEGAL_API_URL"] + "/businesses/internal/tax_ids",
            headers={"Content-Type": CONTENT_TYPE_JSON, "Authorization": f"Bearer {token}"},
            timeout=AccountService.timeout
        )
        if response.status_code != 200:
            application.logger.error("legal-updater failed to get identifiers from legal-api.")
            raise Exception  # pylint: disable=broad-exception-raised
        business_identifiers = response.json()

        if business_identifiers["identifiers"]:
            start = 0
            end = 20
            # make a colin-api call with 20 identifiers at a time
            while identifiers := business_identifiers["identifiers"][start:end]:
                start = end
                end += 20
                # get tax ids that exist for above entities
                application.logger.debug(f"Getting tax ids for {identifiers} from colin api...")
                response = requests.get(
                    application.config["COLIN_URL"] + "/internal/tax_ids",
                    json={"identifiers": identifiers},
                    headers={"Content-Type": CONTENT_TYPE_JSON, "Authorization": f"Bearer {token}"},
                    timeout=AccountService.timeout
                )
                if response.status_code != 200:
                    application.logger.error("legal-updater failed to get tax_ids from colin-api.")
                    raise Exception  # pylint: disable=broad-exception-raised
                tax_ids = response.json()
                if tax_ids.keys():
                    # update lear with new tax ids from colin
                    application.logger.debug(f"Updating tax ids for {tax_ids.keys()} in lear...")
                    response = requests.post(
                        application.config["LEGAL_API_URL"] + "/businesses/internal/tax_ids",
                        json=tax_ids,
                        headers={"Content-Type": CONTENT_TYPE_JSON, "Authorization": f"Bearer {token}"},
                        timeout=AccountService.timeout
                    )
                    if response.status_code != 201:
                        application.logger.error("legal-updater failed to update tax_ids in lear.")
                        raise Exception  # pylint: disable=broad-exception-raised

                    await publish_queue_events(tax_ids, application)

                    application.logger.debug("Successfully updated tax ids in lear.")
                else:
                    application.logger.debug("No tax ids in colin to update in lear.")
        else:
            application.logger.debug("No businesses in lear with outstanding tax ids.")

    except Exception as err:
        application.logger.error(err)


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        update_filings(app)
        event_loop = asyncio.get_event_loop()
        event_loop.run_until_complete(update_business_nos(app))
