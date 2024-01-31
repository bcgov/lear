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
import asyncio
import logging
import os
from datetime import datetime, timezone

import requests
import sentry_sdk  # noqa: I001; pylint: disable=ungrouped-imports; conflicts with Flake8
from dateutil.parser import parse
from dotenv import find_dotenv, load_dotenv
from flask import Flask, current_app, request
from sentry_sdk.integrations.logging import LoggingIntegration  # noqa: I001
from simple_cloudevent import SimpleCloudEvent

import config  # pylint: disable=import-error
from services import queue  # pylint: disable=import-error
from services.logging import structured_log  # pylint: disable=import-error
from utils.logging import setup_logging  # pylint: disable=import-error

setup_logging(os.path.join(os.path.abspath(os.path.dirname(__file__)), "logging.conf"))  # important to do this first

# this will load all the envars from a .env file located in the project root
load_dotenv(find_dotenv())

SENTRY_LOGGING = LoggingIntegration(event_level=logging.ERROR)  # send errors as events


def create_app(run_mode=os.getenv("FLASK_ENV", "production")):
    """Return a configured Flask App using the Factory method."""
    app = Flask(__name__)
    app.config.from_object(config.CONFIGURATION[run_mode])
    # Configure Sentry
    if app.config.get("SENTRY_DSN", None):
        sentry_sdk.init(dsn=app.config.get("SENTRY_DSN"), integrations=[SENTRY_LOGGING])

    return app


def get_filings(app: Flask = None):
    """Get a filing with filing_id."""
    response = requests.get(f'{app.config["LEGAL_URL"]}/internal/filings/PAID')
    if not response or response.status_code != 200:
        app.logger.error(
            f"Failed to collect filings from legal-api. \
            {response} {response.json()} {response.status_code}"
        )
        raise Exception  # pylint: disable=broad-exception-raised
    return response.json()


async def run(loop, application: Flask = None):  # pylint: disable=redefined-outer-name
    """Run the methods for applying future effective filings."""
    if application is None:
        application = create_app()

    with application.app_context():
        try:
            filings = get_filings(app=application)
            if not filings:
                application.logger.debug("No PAID filings found to apply.")
            for filing in filings:
                filing_id = filing["filing"]["header"]["filingId"]
                effective_date = filing["filing"]["header"]["effectiveDate"]
                filing_type = "filing"
                try:
                    filing_type = filing["filing"]["business"]["legalType"]
                except KeyError:
                    filing_type = filing["filing"]["registration"]["nameRequest"]["legalType"]
                cloud_event = SimpleCloudEvent(
                    source=__name__[: __name__.find(".")],
                    subject="filing",
                    type="Filing",
                    data={
                        "filingId": filing_id,
                        "filingType": filing_type,
                        "filingEffectiveDate": effective_date,
                    },
                )
                # NB: effective_date and now are both UTC
                now = datetime.utcnow().replace(tzinfo=timezone.utc)
                valid = effective_date and parse(effective_date) <= now
                if valid:
                    # Publish to new GCP Filer Q
                    filer_topic = current_app.config.get("ENTITY_FILER_TOPIC", "filer")
                    queue.publish(topic=filer_topic, payload=queue.to_queue_message(cloud_event))
                    structured_log(request, "INFO", f"publish to filer for id: {filing_id}")
                    application.logger.debug("Successfully put filing %s on the queue.", filing_id)
        except Exception as error:  # pylint: disable=broad-except
            application.logger.error(error)


if __name__ == "__main__":
    application = create_app()
    try:
        event_loop = asyncio.get_event_loop()
        event_loop.run_until_complete(run(event_loop, application))
    except Exception as err:  # pylint: disable=broad-except; Catching all errors from the frameworks
        application.logger.error(err)  # pylint: disable=no-member
        raise err
