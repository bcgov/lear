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

from gcp_queue import GcpQueue

# Import Flags class first
from .flags import Flags

# Create flags instance BEFORE importing modules that depend on it
# This prevents circular import issues with authz and bootstrap
flags = Flags()

# Now import modules that may reference the flags instance
from .authz import (
    ACCOUNT_IDENTITY,
    BASIC_USER,
    COLIN_SVC_ROLE,
    STAFF_ROLE,
    SYSTEM_ROLE,
    authorized,
    has_roles,
)
from .bootstrap import AccountService, RegistrationBootstrapService
from .business_details_version import VersionedBusinessDetailsService
from .colin import ColinService
from .digital_credentials import DigitalCredentialsService
from .digital_credentials_rules import DigitalCredentialsRulesService
from .furnishing_documents_service import FurnishingDocumentsService
from .involuntary_dissolution import InvoluntaryDissolutionService
from .minio import MinioService
from .mras_service import MrasService
from .naics import NaicsService
from .namex import NameXService
from .pdf_service import PdfService
from .warnings.business import check_business
from .warnings.warning import check_warnings

# Create other service instances
gcp_queue = GcpQueue()
namex = NameXService()
colin = ColinService()
digital_credentials = DigitalCredentialsService()

__all__ = [  # noqa: RUF022
    # Authorization
    "ACCOUNT_IDENTITY",
    "BASIC_USER",
    "COLIN_SVC_ROLE",
    "STAFF_ROLE",
    "SYSTEM_ROLE",
    "authorized",
    "has_roles",
    # Services
    "AccountService",
    "RegistrationBootstrapService",
    "VersionedBusinessDetailsService",
    "ColinService",
    "DigitalCredentialsService",
    "DigitalCredentialsRulesService",
    "Flags",
    "FurnishingDocumentsService",
    "InvoluntaryDissolutionService",
    "MinioService",
    "MrasService",
    "NaicsService",
    "NameXService",
    "PdfService",
    "check_business",
    "check_warnings",
    # Service instances (not modules)
    "flags",
    "gcp_queue",
    "namex",
    "colin",
    "digital_credentials",
]
