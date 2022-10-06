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
"""This module wraps the calls to external services used by the API."""
import uuid

from flask import current_app
from sentry_sdk import capture_message

from legal_api.models import Business
from legal_api.utils.datetime import datetime

from .authz import (
    BASIC_USER,
    COLIN_SVC_ROLE,
    STAFF_ROLE,
    SYSTEM_ROLE,
    authorized,
    get_account_by_affiliated_identifier,
    has_roles,
)
from .bootstrap import AccountService, RegistrationBootstrapService
from .business_details_version import VersionedBusinessDetailsService
from .digital_credentials import DigitalCredentialsService
from .document_meta import DocumentMetaService
from .flags import Flags
from .minio import MinioService
from .naics import NaicsService
from .namex import NameXService
from .pdf_service import PdfService
from .queue import QueueService
from .warnings.business import check_business
from .warnings.warning import check_warnings


flags = Flags()  # pylint: disable=invalid-name; shared variables are lower case by Flask convention.
queue = QueueService()  # pylint: disable=invalid-name; shared variables are lower case by Flask convention.
namex = NameXService()  # pylint: disable=invalid-name; shared variables are lower case by Flask convention.
digital_credentials = DigitalCredentialsService()


def publish_event(business: Business, event_type: str, data: dict, subject: str, message_id: str = None):
    """Publish the event message onto the given NATS subject."""
    try:
        payload = {
            'specversion': '1.x-wip',
            'type': event_type,
            'source': ''.join([current_app.config.get('LEGAL_API_BASE_URL'), '/', business.identifier]),
            'id': message_id or str(uuid.uuid4()),
            'time': datetime.utcnow().isoformat(),
            'datacontenttype': 'application/json',
            'identifier': business.identifier,
            'data': data
        }
        queue.publish_json(payload, subject)
    except Exception as err:  # pylint: disable=broad-except; # noqa: B902
        capture_message(f'Legal-api queue publish {subject} error: business.id=' + str(business.id) + str(err),
                        level='error')
        current_app.logger.error('Queue Publish %s Error: business.id=%s', subject, business.id, exc_info=True)
