# Copyright © 2025 Province of British Columbia
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
"""The Expired Limited Restoration service.

This module is being used to process businesses with expired limited restorations.
"""
from datetime import UTC, datetime
from http import HTTPStatus

import requests
from flask import current_app


def get_bearer_token(timeout):
    """Get a valid Bearer token for the service to use."""
    token_url = current_app.config.get("ACCOUNT_SVC_AUTH_URL")
    client_id = current_app.config.get("ACCOUNT_SVC_CLIENT_ID")
    client_secret = current_app.config.get("ACCOUNT_SVC_CLIENT_SECRET")

    data = "grant_type=client_credentials"

    # get service account token
    res = requests.post(url=token_url,
                        data=data,
                        headers={"content-type": "application/x-www-form-urlencoded"},
                        auth=(client_id, client_secret),
                        timeout=timeout)

    try:
        return res.json().get("access_token")
    except Exception:  # pylint: disable=broad-exception-caught;
        return None


def get_businesses_to_process():
    """Get list of business identifiers that need processing."""
    timeout = int(current_app.config.get("ACCOUNT_SVC_TIMEOUT"))
    token = get_bearer_token(timeout)

    response = requests.get(
        f'{current_app.config["LEAR_SVC_URL"]}/internal/expired_restoration',
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        },
        timeout=timeout
    )

    if not response or response.status_code != HTTPStatus.OK:
        current_app.logger.error(f"Failed to get businesses from legal-api.  \
            {response} {response.json()} {response.status_code}")
        raise Exception  # pylint: disable=broad-exception-raised;

    return response.json().get("businesses", [])


def create_put_back_off_filing(business: dict):
    """Create a putBackOff filing for the business."""
    timeout = int(current_app.config.get("ACCOUNT_SVC_TIMEOUT"))
    token = get_bearer_token(timeout)
    identifier = business["identifier"]
    legal_type = business["legalType"]
    filing_data = {
        "filing": {
            "header": {
                "date": datetime.now(tz=UTC).date().isoformat(),
                "name": "putBackOff",
                "certifiedBy": "system"
            },
            "business": {
                "identifier": identifier,
                "legalType": legal_type
            },
            "putBackOff": {
                "details": "Put back off filing due to expired limited restoration."
            }
        }
    }

    response = requests.post(
        f'{current_app.config["LEAR_SVC_URL"]}/businesses/{identifier}/filings',
        json=filing_data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "hide-in-ledger": "true"  # Add this header to hide from ledger
        },
        timeout=timeout
    )

    if not response or response.status_code != HTTPStatus.CREATED:
        current_app.logger.error(f"Failed to create filing from legal-api. \
            {response} {response.json()} {response.status_code}")
        raise Exception  # pylint: disable=broad-exception-raised;

    return response.json()


def run_job():  # pylint: disable=redefined-outer-name
    """Run the methods for processing expired limited restorations."""
    try:
        # 1. get businesses that need to be processed
        businesses = get_businesses_to_process()

        if not businesses:
            current_app.logger.debug("No businesses to process")
            return

        current_app.logger.debug(f"Processing {len(businesses)} businesses")

        # 2. create put back off filing for each business
        for business in businesses:
            try:
                # create putBackOff filing via API
                identifier = business["identifier"]
                filing = create_put_back_off_filing(business)
                filing_id = filing["filing"]["header"]["filingId"]
                current_app.logger.debug(
                    f"Successfully created put back off filing {filing_id} for {identifier}"
                )
            except Exception as err:  # pylint: disable=broad-except;
                current_app.logger.error(f"Error processing business {identifier}: {err}")
                continue
    except Exception as err:  # pylint: disable=broad-except;
        current_app.logger.error(f"Job failed: {err}")
