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
from .authz import BASIC_USER, COLIN_SVC_ROLE, STAFF_ROLE, SYSTEM_ROLE, authorized
from .bootstrap import RegistrationBootstrapService
from .business_details_version import VersionedBusinessDetailsService
from .document_meta import DocumentMetaService
from .flags import Flags
from .minio import MinioService
from .naics import NaicsService
from .namex import NameXService
from .pdf_service import PdfService
from .queue import QueueService


flags = Flags()  # pylint: disable=invalid-name; shared variables are lower case by Flask convention.

queue = QueueService()  # pylint: disable=invalid-name; shared variables are lower case by Flask convention.

namex = NameXService()  # pylint: disable=invalid-name; shared variables are lower case by Flask convention.

#  document_meta = DocumentMetaService()  # pylint: disable=invalid-name;
