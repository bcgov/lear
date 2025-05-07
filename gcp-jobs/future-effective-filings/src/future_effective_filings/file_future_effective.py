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
"""The Future Effective Date service.

This module script is for putting filings with future effective dates on the entity filer queue.
"""
import os
import uuid
from datetime import UTC, datetime

import requests
from dotenv import find_dotenv, load_dotenv
from flask import Flask
from simple_cloudevent import SimpleCloudEvent, to_queue_message

from future_effective_filings.config import get_named_config
from gcp_queue import GcpQueue
from structured_logging import StructuredLogging

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

    return app


def get_bearer_token(app: Flask, timeout):
    """Get a valid Bearer token for the service to use."""
    token_url = app.config.get("ACCOUNT_SVC_AUTH_URL")
    client_id = app.config.get("ACCOUNT_SVC_CLIENT_ID")
    client_secret = app.config.get("ACCOUNT_SVC_CLIENT_SECRET")

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


def get_filing_ids(app: Flask):
    """Get filing id to process."""
    timeout = app.config["LEAR_SVC_TIMEOUT"]
    token = get_bearer_token(app, timeout)
    app.logger.debug("Fetching from lear")
    response = requests.get(
        f'{app.config["LEAR_SVC_URL"]}/internal/filings/future_effective',
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + token},
        timeout=timeout)
    if not response or response.status_code != STATUS_OK:
        app.logger.error(f"Failed to collect filings from legal-api. \
            {response} {response.json()} {response.status_code}")
        raise Exception  # pylint: disable=broad-exception-raised;
    app.logger.debug("Successfully fetched from lear")
    return response.json()


def run(application: Flask):  # pylint: disable=redefined-outer-name
    """Run the methods for applying future effective filings."""
    
    with application.app_context():
        subject = application.config["BUSINESS_FILER_TOPIC"]
        try:
            if not (filing_ids := get_filing_ids(application)):
                application.logger.debug("No filings found to apply.")
            for filing_id in filing_ids:
                application.logger.debug(f"Attempting to place filing on Filer Queue with id {filing_id}")
                msg = {"filingMessage": {"filingIdentifier": filing_id}}
                ce = SimpleCloudEvent(
                    id=str(uuid.uuid4()),
                    source=application.config.get("CLIENT_NAME"),
                    subject=subject,
                    time=datetime.now(UTC),
                    type="filingMessage",
                    data = msg
                )
                gcp_queue.publish(subject, to_queue_message(ce))
                application.logger.debug(f"Successfully put filing {filing_id} on the queue.")
        except Exception as err:  # pylint: disable=broad-except;
            application.logger.error(err)

if __name__ == "__main__":
    application = create_app()
    try:
        run(application)
    except Exception as err:
        application.logger.error(err)
        raise err
