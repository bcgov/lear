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
"""Worker for the Update COLIN Filings service."""
from http import HTTPStatus

import requests
from flask import current_app

from business_account.AccountService import AccountService


def get_filings(token, limit, offset):
    """Get filings from LEAR that need syncing to COLIN."""
    req = requests.get(f'{current_app.config["LEAR_SVC_URL"]}/businesses/internal/filings?offset={offset}&limit={limit}',
                       headers={"Authorization": "Bearer " + token},
                       timeout=current_app.config["LEAR_SVC_TIMEOUT"])
    if not req or req.status_code != HTTPStatus.OK:
        current_app.logger.error(f"Failed to collect filings from legal-api. {req} {req.json()} {req.status_code}")
        raise Exception  # pylint: disable=broad-exception-raised
    return req.json().get("filings")


def send_filing(token: str, filing: dict, filing_id: str):
    """Post to colin-api with filing."""
    clean_none(filing)

    filing_type = filing["filing"]["header"].get("name", None)
    identifier = filing["filing"]["business"].get("identifier", None)
    legal_type = filing["filing"]["business"].get("legalType", None)

    response = None
    if legal_type and identifier and filing_type:
        response = requests.post(f'{current_app.config["COLIN_SVC_URL"]}/businesses/{legal_type}/{identifier}/filings/{filing_type}',
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + token},
                                 json=filing,
                                 timeout=current_app.config["COLIN_SVC_TIMEOUT"])

    if not response or response.status_code != HTTPStatus.CREATED:
        current_app.logger.error(f"Filing {filing_id} not created in colin {identifier}.")
        if response and (colin_error := response.json().get("error")):
            current_app.logger.error(f"colin-api: {colin_error}")
        return None
    # if it's an AR containing multiple filings it will have multiple colinIds
    return response.json()["filing"]["header"]["colinIds"]


def update_colin_id(token: dict, filing_id: str, colin_ids: list):
    """Update the colin_id in the filings table."""
    req = requests.patch(
        f'{current_app.config["LEAR_SVC_URL"]}/businesses/internal/filings/{filing_id}',
        headers={"Authorization": "Bearer " + token},
        json={"colinIds": colin_ids},
        timeout=current_app.config["LEAR_SVC_TIMEOUT"]
    )
    if not req or req.status_code != HTTPStatus.ACCEPTED:
        current_app.logger.error(f"Failed to update colin id in legal db for filing {filing_id} {req.status_code}")
        current_app.logger.error(
            f"""ATTENTION - MANUAL ACTION REQUIRED:
            Successfully created a filing in COLIN but failed to insert colin_event_ids in LEAR.
            update colin_event_ids table with, filing {filing_id} and colin ids {colin_ids}""")
        return False
    return True


def clean_none(dictionary: dict | None = None):
    """Replace all none values with empty string."""
    for key, value in dictionary.items():
        if value:
            if isinstance(value, dict):
                clean_none(value)
        elif value is None:
            dictionary[key] = ""


def process_filing(filing: dict, token: str, job_stats: dict):
    """Send the filing to COLIN and update LEAR."""
    filing_id = filing["filingId"]
    identifier = filing["filing"]["business"]["identifier"]
    if identifier in job_stats["corps_with_failed_filing"]:
        job_stats["skipped_sync"] += 1
        current_app.logger.debug(f'Skipping filing {filing_id} for'
                                    f' {filing["filing"]["business"]["identifier"]}.')
    else:
        colin_ids = send_filing(token, filing, filing_id)
        update = None
        if colin_ids:
            update = update_colin_id(token, filing_id, colin_ids)
        if update:
            current_app.logger.debug(f"Successfully updated filing {filing_id}")
            job_stats["success"] += 1
        else:
            job_stats["corps_with_failed_filing"].append(filing["filing"]["business"]["identifier"])
            current_app.logger.error(f"Failed to update filing {filing_id} with colin event id.")


def run():
    """Get filings that haven't been synced with colin and send them to the colin-api."""
    job_stats = {
        "corps_with_failed_filing": [],
        "skipped_sync": 0,
        "success": 0
    }
    total_limit = current_app.config["JOB_TOTAL_LIMIT"]
    limit = current_app.config["JOB_BATCH_LIMIT"]
    try:
        # get updater-job token
        token = AccountService.get_bearer_token()
        while filings := get_filings(token, limit, len(job_stats["corps_with_failed_filing"]) + job_stats["skipped_sync"]):
            total_processed = len(job_stats["corps_with_failed_filing"]) + job_stats["skipped_sync"] + job_stats["success"]
            if total_processed > total_limit:
                current_app.logger.warning("Job hit total filing limit for run. Ending job cycle.")
                break
            for filing in filings:
                process_filing(filing, token, job_stats)

        current_app.logger.debug("Success: %s, Failed: %s, Skipped: %s",
                                 job_stats["success"],
                                 len(job_stats["corps_with_failed_filing"]),
                                 job_stats["skipped_sync"])

    except Exception as err:
        current_app.logger.error(err)
