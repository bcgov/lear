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
from gcp_queue import GcpQueue
from sentry_sdk import capture_message
from simple_cloudevent import SimpleCloudEvent, to_queue_message

from legal_api.models import Business
from legal_api.utils.datetime import datetime

from .bootstrap import AccountService, RegistrationBootstrapService
from .business_details_version import VersionedBusinessDetailsService
from .colin import ColinService
from .digital_credentials import DigitalCredentialsService
from .digital_credentials_rules import DigitalCredentialsRulesService
from .document_meta import DocumentMetaService
from .flags import Flags
from .furnishing_documents_service import FurnishingDocumentsService
from .involuntary_dissolution import InvoluntaryDissolutionService
from .minio import MinioService
from .mras_service import MrasService
from .naics import NaicsService
from .namex import NameXService
from .pdf_service import PdfService
from .queue import QueueService
from .warnings.business import check_business
from .warnings.warning import check_warnings


from .authz import (  # noqa: I001; noqa: I001;
    ACCOUNT_IDENTITY,
    BASIC_USER,
    COLIN_SVC_ROLE,
    STAFF_ROLE,
    SYSTEM_ROLE,
    authorized,
    has_roles,
)


flags = Flags()  # pylint: disable=invalid-name; shared variables are lower case by Flask convention.
gcp_queue = GcpQueue()  # pylint: disable=invalid-name; shared variables are lower case by Flask convention.
queue = QueueService()  # pylint: disable=invalid-name; shared variables are lower case by Flask convention.
namex = NameXService()  # pylint: disable=invalid-name; shared variables are lower case by Flask convention.
colin = ColinService()  # pylint: disable=invalid-name; shared variables are lower case by Flask convention.
digital_credentials = DigitalCredentialsService()


def publish_event(business: Business, event_type: str, data: dict, subject: str, message_id: str = None):
    """Publish the event message onto the given NATS subject or GCP topic."""
    try:
        source = ''.join([current_app.config.get('LEGAL_API_BASE_URL'), '/', business.identifier])
        time = datetime.utcnow().isoformat()

        if current_app.config['DEPLOYMENT_PLATFORM'] == 'GCP':
            nats_to_gcp_topic = {
                current_app.config['NATS_FILER_SUBJECT']: current_app.config['BUSINESS_FILER_TOPIC'],
                current_app.config['NATS_ENTITY_EVENT_SUBJECT']: current_app.config['BUSINESS_EVENTS_TOPIC'],
                current_app.config['NATS_EMAILER_SUBJECT']: current_app.config['BUSINESS_EMAILER_TOPIC'],
            }
            topic = nats_to_gcp_topic[subject]
            ce = SimpleCloudEvent(id=str(uuid.uuid4()),
                                  source=source,
                                  subject=business.identifier,
                                  time=time,
                                  type=event_type,
                                  data = {'identifier': business.identifier, **data})
            gcp_queue.publish(topic, to_queue_message(ce))
        else:
            payload = {
                'specversion': '1.x-wip',
                'type': event_type,
                'source': source,
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
