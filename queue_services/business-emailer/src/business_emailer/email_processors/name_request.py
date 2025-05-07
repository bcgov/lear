# Copyright © 2020 Province of British Columbia
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
"""Email processing rules and actions for Name Request Payment Completion."""
from __future__ import annotations

import base64
from http import HTTPStatus
from pathlib import Path

import requests
from flask import current_app
from jinja2 import Template

from business_emailer.email_processors import substitute_template_parts
from business_emailer.services.namex import NameXService


def process(email_info: dict) -> dict:
    """Build the email for Name Request notification."""
    current_app.logger.debug("NR_notification: %s", email_info)
    nr_number = email_info["identifier"]
    payment_token = email_info.get("request", {}).get("paymentToken", "")
    template = Path(f'{current_app.config.get("TEMPLATE_PATH")}/NR-PAID.html').read_text()
    filled_template = substitute_template_parts(template)
    # render template with vars
    mail_template = Template(filled_template, autoescape=True)
    html_out = mail_template.render(
        identifier=nr_number
    )

    # get nr data
    nr_response = NameXService.query_nr_number(nr_number)
    if nr_response.status_code != HTTPStatus.OK:
        current_app.logger.error("Failed to get nr info for name request: %s", nr_number)
        return {}
    nr_data = nr_response.json()

    # get attachments
    pdfs = _get_pdfs(nr_data["id"], payment_token)
    if not pdfs:
        return {}

    # get recipients
    recipients = nr_data["applicants"]["emailAddress"]
    if not recipients:
        return {}

    subject = f"{nr_number} - Receipt from Corporate Registry"

    return {
        "recipients": recipients,
        "requestBy": "BCRegistries@gov.bc.ca",
        "content": {
            "subject": subject,
            "body": f"{html_out}",
            "attachments": pdfs
        }
    }


def _get_pdfs(nr_id: str, payment_token: str) -> list:
    """Get the receipt for the name request application."""
    pdfs = []
    token = get_nr_bearer_token()
    if not token or not nr_id or not payment_token:
        return []

    # get nr payments
    nr_payments = requests.get(
        f'{current_app.config.get("NAMEX_SVC_URL")}payments/{nr_id}',
        json={},
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}"
        }
    )
    if nr_payments.status_code != HTTPStatus.OK:
        current_app.logger.error("Failed to get payment info for name request id: %s", nr_id)
        return []

    # find specific payment corresponding to payment token
    payment_id = ""
    for payment in nr_payments.json():
        if payment_token == payment["token"]:
            payment_id = payment["id"]
    if not payment_id:
        current_app.logger.error("No matching payment info found for name request id: %s, payment token: %s", nr_id, payment_token)
        return []

    # get receipt
    receipt = requests.post(
        f'{current_app.config.get("NAMEX_SVC_URL")}payments/{payment_id}/receipt',
        json={},
        headers={
            "Accept": "application/pdf",
            "Authorization": f"Bearer {token}"
        }
    )
    if receipt.status_code != HTTPStatus.OK:
        current_app.logger.error("Failed to get receipt pdf for name request id: %s", nr_id)
        return []

    # add receipt to pdfs
    receipt_encoded = base64.b64encode(receipt.content)
    pdfs.append(
        {
            "fileName": "Receipt.pdf",
            "fileBytes": receipt_encoded.decode("utf-8"),
            "fileUrl": "",
            "attachOrder": "1"
        }
    )
    return pdfs


def get_nr_bearer_token():
    """Get a valid Bearer token for the Name Request Service."""
    token_url = current_app.config.get("NAMEX_AUTH_SVC_URL")
    client_id = current_app.config.get("NAMEX_SERVICE_CLIENT_USERNAME")
    client_secret = current_app.config.get("NAMEX_SERVICE_CLIENT_SECRET")

    data = "grant_type=client_credentials"
    # get service account token
    res = requests.post(url=token_url,
                        data=data,
                        headers={"content-type": "application/x-www-form-urlencoded"},
                        auth=(client_id, client_secret))
    try:
        return res.json().get("access_token")
    except Exception:
        current_app.logger.error("Failed to get nr token")
        return None
