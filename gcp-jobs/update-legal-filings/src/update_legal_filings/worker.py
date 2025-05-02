# Copyright © 2025 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the "License");
# you may not use this file except in compliance with the License.
# The template for the license can be found here
#    https://opensource.org/license/bsd-3-clause/
#
# Redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
"""This Module is main module for the legal updater."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from http import HTTPStatus

import requests
import simple_cloudevent
from flask import Flask, current_app
from simple_cloudevent import to_queue_message

from business_account.AccountService import AccountService
from update_legal_filings import gcp_queue
from update_legal_filings.colin_helper import COLIN_FILING_TYPES, ColinApiTypeCodes

SET_EVENTS_MANUALLY = False
CONTENT_TYPE_JSON = "application/json"
DEFAULT_CONNECT_TIMEOUT = 2
STATUS_OK = 200



def _get_ce(data):
    """Return a SimpleCloudEvent object."""
    return simple_cloudevent.SimpleCloudEvent(
        id=str(uuid.uuid4()),
        type="bc.registry.business.bn",
        source="update-legal-filings.update_business_nos",
        subject="bn-update-identifier",
        time=datetime.now(tz=UTC).isoformat(),
        data=data
    )

def check_for_manual_filings(token: dict | None = None):
    """Check for colin filings in oracle."""
    id_list = []
    colin_events = None
    legal_url = current_app.config["LEAR_SVC_URL"] + "/businesses"
    colin_url = current_app.config["COLIN_SVC_URL"]
    corp_types = [ColinApiTypeCodes.COOP.value]

    # get max colin event_id from legal
    response = requests.get(f"{legal_url}/internal/filings/colin_id",
                            headers={"Content-Type": CONTENT_TYPE_JSON, "Authorization": f"Bearer {token}"},
                            timeout=AccountService.timeout)
    if response.status_code not in [HTTPStatus.OK, HTTPStatus.NOT_FOUND]:
        current_app.logger.error(f"Error getting last updated colin id from \
            legal: {response.status_code} {response.json()}")
    else:
        last_event_id = (
            "earliest" if response.status_code == HTTPStatus.NOT_FOUND else str(response.json().get("maxId"))
        )

        current_app.logger.debug(f"last_event_id: {last_event_id}")
        if last_event_id:
            last_event_id = str(last_event_id)
            # get all event_ids greater than above
            try:
                for corp_type in corp_types:
                    current_app.logger.debug(f"corp_type: {corp_type}")
                    url = f"{colin_url}/event/{corp_type}/{last_event_id}"
                    current_app.logger.debug(f"url: {url}")
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
                current_app.logger.error("Error getting event_ids from colin: %s", repr(err), exc_info=True)
                raise err

            # for each event_id: if not in legal db table then add event_id to list
            for info in colin_events["events"]:
                # check that event is associated with one of the coops loaded into legal db
                response = requests.get(
                    f'{legal_url}/{info["corp_num"]}',
                    headers={"Content-Type": CONTENT_TYPE_JSON, "Authorization": f"Bearer {token}"},
                    timeout=AccountService.timeout
                )
                if response.status_code == HTTPStatus.OK:
                    # check legal table
                    response = requests.get(
                        f'{legal_url}/internal/filings/colin_id/{info["event_id"]}',
                        headers={"Content-Type": CONTENT_TYPE_JSON, "Authorization": f"Bearer {token}"},
                        timeout=AccountService.timeout)
                    if response.status_code == HTTPStatus.NOT_FOUND:
                        id_list.append(info)
                    elif response.status_code != HTTPStatus.OK:
                        current_app.logger.error(f'Error checking for colin id {info["event_id"]} in legal')
                else:
                    current_app.logger.error("No ids returned from colin_last_update table in legal db.")

    return id_list


def get_filing(event_info: dict | None = None, application: Flask | None = None, token: dict | None = None) -> dict:
    """Get filing created by previous event."""
    # call the colin api for the filing
    legal_type = event_info["corp_num"][:2]
    filing_typ_cd = event_info["filing_typ_cd"]
    filing_types = COLIN_FILING_TYPES.keys()
    filing_type = \
        next((x for x in filing_types if filing_typ_cd in COLIN_FILING_TYPES.get(x).get("type_code_list")), None)

    if not filing_type:
        # pylint: disable=consider-using-f-string
        application.logger.error("Error unknown filing type: {} for event id: {}".format(
            event_info["filing_type"], event_info["event_id"]))

    identifier = event_info["corp_num"]
    event_id = event_info["event_id"]
    response = requests.get(
        f'{application.config["COLIN_SVC_URL"]}/{legal_type}/{identifier}/filings/{filing_type}?eventId={event_id}',
        headers={**AccountService.CONTENT_TYPE_JSON,
                 "Authorization": AccountService.BEARER + token},
        timeout=AccountService.timeout
    )
    filing = dict(response.json())
    return filing


def update_filings():  # noqa: PLR0912
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
        manual_filings_info = check_for_manual_filings(token)
        max_event_id = 0

        if len(manual_filings_info) > 0:
            for event_info in manual_filings_info:
                # Make sure this coop has no outstanding filings that failed to be applied.
                # This ensures we don't apply filings out of order when one fails.
                if event_info["corp_num"] not in corps_with_failed_filing:
                    filing = get_filing(event_info, token)

                    # call legal api with filing
                    current_app.logger.debug(f"sending filing with event info: {event_info} to legal api.")
                    response = requests.post(
                        f'{current_app.config["LEAR_SVC_URL"]}/businesses/{event_info["corp_num"]}/filings',
                        json=filing,
                        headers={"Content-Type": CONTENT_TYPE_JSON, "Authorization": f"Bearer {token}"},
                        timeout=AccountService.timeout
                    )
                    if response.status_code != HTTPStatus.CREATED:
                        if not first_failed_id:
                            first_failed_id = event_info["event_id"]
                        failed_filing_events.append(event_info)
                        corps_with_failed_filing.append(event_info["corp_num"])
                        current_app.logger.error(f'Legal failed to create filing for {event_info["corp_num"]}')
                    else:
                        # update max_event_id entered
                        successful_filings += 1
                        max_event_id = max(max_event_id, int(event_info["event_id"]))
                else:
                    skipped_filings.append(event_info)
        else:
            current_app.logger.debug("0 filings updated in legal db.")

        current_app.logger.debug(f"successful filings: {successful_filings}")
        current_app.logger.debug(f"skipped filings due to related erred filings: {len(skipped_filings)}")
        current_app.logger.debug(f"failed filings: {len(failed_filing_events)}")
        current_app.logger.debug(f"failed filings event info: {failed_filing_events}")

        # if manually bringing across filings, set to first id so you don't skip any filings on the next run
        if SET_EVENTS_MANUALLY:
            first_failed_id = 102125621

        # if one of the events failed then save that id minus one so that the next run will try it again
        # this way failed filings wont get buried/forgotten after multiple runs
        if first_failed_id:
            max_event_id = first_failed_id - 1
        if max_event_id > 0:
            # update max_event_id in legal_db
            current_app.logger.debug(f"setting last_event_id in legal_db to {max_event_id}")
            response = requests.post(
                f'{current_app.config["LEAR_SVC_URL"]}/businesses/internal/filings/colin_id/{max_event_id}',
                headers={"Content-Type": CONTENT_TYPE_JSON, "Authorization": f"Bearer {token}"},
                timeout=AccountService.timeout
            )
            if response.status_code != HTTPStatus.CREATED:
                current_app.logger.error(
                    f"Error adding {max_event_id} colin_last_update table in legal db {response.status_code}"
                )
            elif dict(response.json())["maxId"] != max_event_id:
                current_app.logger.error("Updated colin id is not max colin id in legal db.")
            else:
                current_app.logger.debug("Successfully updated colin id in legal db.")

        else:
            current_app.logger.debug("colin_last_update not updated in legal db.")

    except Exception as err:
        current_app.logger.error("Update-legal-filings: unhandled error %s", err)


def publish_queue_events(tax_ids: dict):  # pylint: disable=redefined-outer-name
    """Publish events for all businesses with new tax ids (for email + entity listeners)."""
    for identifier in tax_ids:
        try:
            emailer_topic = current_app.config["BUSINESS_EMAILER_TOPIC"]
            payload = {"email": {"filingId": None, "type": "businessNumber", "option": "bn", "identifier": identifier}}

            mailer_ce = _get_ce(payload)

            gcp_queue.publish(emailer_topic, to_queue_message(mailer_ce))
        except Exception as err:  # pylint: disable=broad-except, unused-variable
            # mark any failure for human review
            current_app.logger.debug(err)
            # NB: error log will trigger sentry message
            current_app.logger.error("Update-legal-filings: Failed to publish bn email event for %s.", identifier)

        try:
            data={
                "identifier": identifier
            }

            ce = _get_ce(data)

            business_event_topic = current_app.config.get("BUSINESS_EVENTS_TOPIC")
            gcp_queue.publish(business_event_topic, to_queue_message(ce))
        except Exception as err:  # pylint: disable=broad-except, unused-variable
            # mark any failure for human review
            current_app.logger.debug(err)
            # NB: error log will trigger sentry message
            current_app.logger.error("Update-legal-filings: Failed to publish bn entity event for %s.", identifier)


def update_business_nos():  # pylint: disable=redefined-outer-name
    """Update the tax_ids for corps with new bn_15s."""
    try:
        # get updater-job token
        token = AccountService.get_bearer_token()

        # get identifiers with outstanding tax_ids
        current_app.logger.debug("Getting businesses with outstanding tax ids from legal api...")
        response = requests.get(
            current_app.config["LEAR_SVC_URL"] + "/businesses/internal/tax_ids",
            headers={"Content-Type": CONTENT_TYPE_JSON, "Authorization": f"Bearer {token}"},
            timeout=AccountService.timeout
        )
        if response.status_code != HTTPStatus.OK:
            current_app.logger.error("legal-updater failed to get identifiers from legal-api.")
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
                current_app.logger.debug(f"Getting tax ids for {identifiers} from colin api...")
                response = requests.get(
                    current_app.config["COLIN_SVC_URL"] + "/internal/tax_ids",
                    json={"identifiers": identifiers},
                    headers={"Content-Type": CONTENT_TYPE_JSON, "Authorization": f"Bearer {token}"},
                    timeout=AccountService.timeout
                )
                if response.status_code != HTTPStatus.OK:
                    current_app.logger.error("legal-updater failed to get tax_ids from colin-api.")
                    raise Exception  # pylint: disable=broad-exception-raised
                tax_ids = response.json()
                if tax_ids.keys():
                    # update lear with new tax ids from colin
                    current_app.logger.debug(f"Updating tax ids for {tax_ids.keys()} in lear...")
                    response = requests.post(
                        current_app.config["LEAR_SVC_URL"] + "/businesses/internal/tax_ids",
                        json=tax_ids,
                        headers={"Content-Type": CONTENT_TYPE_JSON, "Authorization": f"Bearer {token}"},
                        timeout=AccountService.timeout
                    )
                    if response.status_code != HTTPStatus.CREATED:
                        current_app.logger.error("legal-updater failed to update tax_ids in lear.")
                        raise Exception  # pylint: disable=broad-exception-raised

                    publish_queue_events(tax_ids)

                    current_app.logger.debug("Successfully updated tax ids in lear.")
                else:
                    current_app.logger.debug("No tax ids in colin to update in lear.")
        else:
            current_app.logger.debug("No businesses in lear with outstanding tax ids.")

    except Exception as err:
        current_app.logger.error(err)
