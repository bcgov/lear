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
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
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
"""Services for BN retry job."""

from http import HTTPStatus

import requests
from flask import current_app
from gcp_queue import GcpQueue

gcp_queue = GcpQueue()


def get_bearer_token(timeout):
    """Get a valid Bearer token for the service to use.

    Args:
        timeout: Request timeout in seconds

    Returns:
        str: Bearer token or None if failed
    """
    token_url = current_app.config.get("ACCOUNT_SVC_AUTH_URL")
    client_id = current_app.config.get("ACCOUNT_SVC_CLIENT_ID")
    client_secret = current_app.config.get("ACCOUNT_SVC_CLIENT_SECRET")

    data = "grant_type=client_credentials"

    # get service account token
    res = requests.post(
        url=token_url,
        data=data,
        headers={"content-type": "application/x-www-form-urlencoded"},
        auth=(client_id, client_secret),
        timeout=timeout,
    )

    try:
        return res.json().get("access_token")
    except Exception:  # pylint: disable=broad-exception-caught;
        return None


def check_bn15_status_batch(identifiers: list[str]) -> list[dict[str, str]]:
    """Check BN15 status for a batch of identifiers.

    Args:
        identifiers: List of business identifiers

    Returns:
        list[dict[str, str]]: List of BN15s for found matches
    Examples:
        >>> check_bn15_status_batch(["FM123", "FM456"])
        [{"FM123": "123456789BC0001", "FM456": "123456789BC0002"}]
    """
    if not identifiers:
        return []

    timeout = int(current_app.config.get("COLIN_API_TIMEOUT"))
    token = get_bearer_token(timeout)

    if not token:
        current_app.logger.error("Failed to get bearer token for Colin API")
        return []

    colin_api_url = current_app.config.get("COLIN_API_URL")
    colin_api_version = current_app.config.get("COLIN_API_VERSION")
    url = f"{colin_api_url}{colin_api_version}/programAccount/check-bn15s"

    try:
        response = requests.post(
            url,
            json={"identifiers": identifiers},
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
            timeout=timeout,
        )

        if response.status_code != HTTPStatus.OK:
            current_app.logger.error(f"Colin API error for batch check: {response.status_code} - {response.text}")
            return []

        data = response.json()
        results = data.get("bn15s", [])
        current_app.logger.debug(f"Batch check found {len(results)} matches for {len(identifiers)} identifiers")
        return results

    except Exception as err:
        current_app.logger.error(f"Error checking BN15 batch status: {err}")
        return []
