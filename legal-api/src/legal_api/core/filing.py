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
# limitations under the License
"""Filings are legal documents that alter the state of a business."""
# pylint: disable=unused-argument
from __future__ import annotations

# from dataclasses import dataclass, field
import copy
from contextlib import suppress
from enum import Enum
from typing import Dict, List, Optional

from flask import current_app
from flask_jwt_oidc import JwtManager
from sqlalchemy import desc

from legal_api.core.meta import FilingMeta
from legal_api.core.utils import diff_dict, diff_list
from legal_api.models import Business, Filing as FilingStorage, UserRoles  # noqa: I001
from legal_api.services import VersionedBusinessDetailsService  # noqa: I005
from legal_api.services.authz import has_roles  # noqa: I005
from legal_api.utils.datetime import date, datetime  # noqa: I005

from .constants import REDACTED_STAFF_SUBMITTER


# @dataclass(init=False, repr=False)
class Filing:
    """Domain class for Filings."""

    class Status(str, Enum):
        """Render an Enum of the Filing Statuses."""

        COMPLETED = 'COMPLETED'
        CORRECTED = 'CORRECTED'
        DRAFT = 'DRAFT'
        EPOCH = 'EPOCH'
        ERROR = 'ERROR'
        PAID = 'PAID'
        PENDING = 'PENDING'
        PAPER_ONLY = 'PAPER_ONLY'
        PENDING_CORRECTION = 'PENDING_CORRECTION'

    class FilingTypes(str, Enum):
        """Render an Enum of all Filing Types."""

        ALTERATION = 'alteration'
        AMALGAMATIONAPPLICATION = 'amalgamationApplication'
        AMENDEDAGM = 'amendedAGM'
        AMENDEDANNUALREPORT = 'amendedAnnualReport'
        AMENDEDCHANGEOFDIRECTORS = 'amendedChangeOfDirectors'
        ANNUALREPORT = 'annualReport'
        APPOINTRECEIVER = 'appointReceiver'
        CHANGEOFADDRESS = 'changeOfAddress'
        CHANGEOFDIRECTORS = 'changeOfDirectors'
        CHANGEOFNAME = 'changeOfName'
        CONTINUEDOUT = 'continuedOut'
        CONVERSION = 'conversion'
        CORRECTION = 'correction'
        DISSOLUTION = 'dissolution'
        DISSOLVED = 'dissolved'
        INCORPORATIONAPPLICATION = 'incorporationApplication'
        RESTORATIONAPPLICATION = 'restorationApplication'
        SPECIALRESOLUTION = 'specialResolution'
        TRANSITION = 'transition'

    def __init__(self):
        """Create the Filing."""
        self._storage: Optional[FilingStorage] = None
        self._id: str = ''
        self._raw: Optional[Dict] = None
        self._completion_date: datetime
        self._filing_date: datetime
        self._filing_type: Optional[str] = None
        self._effective_date: datetime
        self._payment_status_code: str
        self._payment_token: str
        self._payment_completion_date: datetime
        self._status: Optional[str] = None
        self._paper_only: bool = False
        self._payment_account: Optional[str] = None
        self._jwt: JwtManager = None

    @property
    def id(self) -> str:  # pylint: disable=invalid-name; defining the std ID
        """Return the ID of the filing."""
        if not self._id:
            if self._storage:
                self._id = self._storage.id
        return self._id

    @property
    def filing_type(self) -> str:
        """Property containing the filing type."""
        if not self._filing_type and self._storage:
            self._filing_type = self._storage.filing_type
        return self._filing_type

    @property
    def raw(self) -> Optional[Dict]:
        """Return the raw, submitted and unprocessed version on the filing."""
        if not self._raw and self._storage:
            self._raw = self._storage.json
        return self._raw

    @property
    def payment_account(self) -> Optional[str]:
        """Return the account identifier of this filings payer."""
        if not self._payment_account and self._storage:
            self._payment_account = self._storage.payment_account
        return self._payment_account

    @payment_account.setter
    def payment_account(self, account_identifier):
        """Set the account identifier of this filings payer."""
        self._payment_account = account_identifier
        self.storage.payment_account = self._payment_account

    @property
    def status(self) -> str:
        """Return the status of this Filing."""
        if not self._status and self._storage:
            self._status = self._storage.status
        return self._status

    def redacted(self, filing: dict, jwt: JwtManager):
        """Redact the filing based on stored roles and those in JWT."""
        with suppress(TypeError):
            if ((submitter_roles := self._storage.submitter_roles)
                and (UserRoles.STAFF.value in submitter_roles
                     or UserRoles.SYSTEM.value in submitter_roles)
                ) and (
                 filing.get('filing', {}).get('header', {}).get('submitter')
                 and not has_roles(jwt, [UserRoles.STAFF.value])
               ):
                filing['filing']['header']['submitter'] = REDACTED_STAFF_SUBMITTER

        return filing

    # json is returned as a property defined after this method
    def get_json(self, with_diff: bool = True) -> Optional[Dict]:
        """Return a dict representing the filing json."""
        if not self._storage or (self._storage and self._storage.status not in [Filing.Status.COMPLETED.value,
                                                                                Filing.Status.PAID.value,
                                                                                Filing.Status.PENDING.value,
                                                                                ]):
            filing_json = self.raw

        # this will return the raw filing instead of the versioned filing until
        # payment and processing are complete.
        # This ASSUMES that the JSONSchemas remain valid for that period of time
        # which fits with the N-1 approach to versioning, and
        # that handling of filings stuck in PENDING are handled appropriately.
        elif self._storage.status in [Filing.Status.PAID.value, Filing.Status.PENDING.value]:
            if self._storage.tech_correction_json:
                filing = self._storage.tech_correction_json
            else:
                filing = self.raw

            filing_json = filing

        else:  # Filing.Status.COMPLETED.value
            filing_json = VersionedBusinessDetailsService.get_revision(self.id, self._storage.business_id)

        if with_diff and self.filing_type == Filing.FilingTypes.CORRECTION.value:
            if correction_id := filing_json.get('filing', {}).get('correction', {}).get('correctedFilingId'):
                # filing_json = copy.deepcopy(filing)
                if diff := self._diff(filing_json, correction_id):
                    filing_json['filing']['correction']['diff'] = diff

        return filing_json
    json = property(get_json)

    @json.setter
    def json(self, filing_submission):
        """Add the raw json to the filing."""
        self._raw = filing_submission

    @property
    def storage(self) -> Optional[FilingStorage]:
        """Return filing model.

        (Deprecated)

        Model is exposed to generate pdf. Used in GET api `/<string:identifier>/filings/<int:filing_id>`
        """
        if not self._storage:
            self._storage = FilingStorage()
        return self._storage

    @storage.setter
    def storage(self, filing: FilingStorage):
        """Set filing storage."""
        self._storage = filing

    def save(self):
        """Save the filing.

        This needs to be changed to fully implement the filing save rules currently in the storage class.
        """
        if self.storage:
            self._storage.filing_json = self._raw
            # self._storage.completion_date = self._completion_date TBD
            # self._storage.filing_date = self._filing_date
            # self._storage.filing_type = self._filing_type
            # self._storage.effective_date = self._effective_date
            # self._storage.payment_status_code = self._payment_status_code
            # self._storage.payment_token = self._payment_token
            # self._storage.payment_completion_date = self._payment_completion_date
            # self._storage.status = self._status
            # self._storage.paper_only = self._paper_only
            self._storage.payment_account = self._payment_account
            self.storage.save()

    def _diff(self, filing_json, correction_id):
        """Return the diff block for the filing this one corrects, if any."""
        if filing_json and correction_id and self._storage and self.status in [Filing.Status.COMPLETED.value,
                                                                               Filing.Status.PAID.value,
                                                                               Filing.Status.PENDING.value,
                                                                               ]:
            if corrected_filing := Filing.find_by_id(correction_id):
                if diff_nodes := diff_dict(filing_json,
                                           corrected_filing.json,
                                           ignore_keys=['header', 'business', 'correction'],
                                           diff_list_callback=diff_list):
                    diff_json = [d.json for d in diff_nodes]
                    return diff_json
        return None

    @staticmethod
    def validate():
        """Validate the filing."""
        raise NotImplementedError

    @staticmethod
    def get(identifier, filing_id=None) -> Optional[Filing]:
        """Return a Filing domain by the id."""
        if identifier.startswith('T'):
            storage = FilingStorage.get_temp_reg_filing(identifier)
        else:
            storage = Business.get_filing_by_id(identifier, filing_id)

        if storage:
            filing = Filing()
            filing._storage = storage  # pylint: disable=protected-access
            return filing

        return None

    @staticmethod
    def find_by_id(filing_id) -> Optional[Filing]:
        """Return a Filing domain by the id."""
        # TODO sleuth out the decorator issue
        if storage := FilingStorage.find_by_id(filing_id):
            filing = Filing()
            filing._storage = storage  # pylint: disable=protected-access; setter/getter decorators issue
            return filing
        return None

    @staticmethod
    def get_filings_by_status(business_id: int, status: [], after_date: date = None):
        """Return the filings with statuses in the status array input."""
        storages = FilingStorage.get_filings_by_status(business_id, status, after_date)
        filings = []
        for storage in storages:
            filing = Filing()
            filing.storage = storage
            filings.append(filing)

        return filings

    def legal_filings(self, with_diff: bool = True) -> Optional[List]:
        """Return a list of the filings extracted from this filing submission.

        Returns: {
            List: or None of the Legal Filing JSON segments.
            }
        """
        if not (filing := self.get_json(with_diff)):
            return None

        legal_filings = []
        for k in filing['filing'].keys():  # pylint: disable=unsubscriptable-object
            if FilingStorage.FILINGS.get(k, None):
                legal_filings.append(
                    {k: copy.deepcopy(filing['filing'].get(k))})  # pylint: disable=unsubscriptable-object

        return legal_filings

    @staticmethod
    def ledger(business_id: int,
               jwt: JwtManager = None,
               statuses: List(str) = None,
               start: int = None,
               size: int = None,
               **kwargs) \
            -> list:
        """Return the ledger list by directly querying the storage objects.

        Note: Sort of breaks the "core" style, but searches are always interesting ducks.
        """
        base_url = current_app.config.get('LEGAL_API_BASE_URL')
        if jwt:
            redact_required = has_roles(jwt, [UserRoles.STAFF.value, UserRoles.SYSTEM.value])
        else:
            redact_required = True

        business = Business.find_by_internal_id(business_id)

        query = FilingStorage.query.filter(FilingStorage.business_id == business_id)
        if statuses and isinstance(statuses, List):
            query = query.filter(FilingStorage._status.in_(statuses))  # pylint: disable=protected-access;required by SA

        if start:
            query = query.offset(start)
        if size:
            query = query.limit(size)

        query = query.order_by(desc(FilingStorage.filing_date))

        ledger = []
        for filing in query.all():
            ledger_filing = {
                'availableOnPaperOnly': filing.paper_only,
                'businessIdentifier': business.identifier,
                'commentsCount': filing.comments_count,
                'displayName': FilingMeta.display_name(filing=filing),
                'effectiveDate': filing.effective_date,
                'filingId': filing.id,
                'isFutureEffective': (filing.effective_date
                                      and filing._filing_date  # pylint: disable=protected-access
                                      and (filing.effective_date > filing._filing_date)),  # pylint: disable=protected-access # noqa: E501
                'name': filing.filing_type,
                'paymentStatusCode': filing.payment_status_code,
                'status': filing.status,
                'submitter': REDACTED_STAFF_SUBMITTER if redact_required else filing.filing_submitter.username,
                'submittedDate': filing._filing_date,  # pylint: disable=protected-access

                'commentsLink': f'{base_url}/{business.identifier}/filings/{filing.id}/comments',
                'documentsLink': f'{base_url}/{business.identifier}/filings/{filing.id}/documents',
                'filingLink': f'{base_url}/{business.identifier}/filings/{filing.id}',
            }
            # correction
            if filing.parent_filing:
                ledger_filing['correctionFilingId'] = filing.parent_filing.id
                ledger_filing['correctionLink'] = f'{base_url}/{business.identifier}/filings/{filing.parent_filing.id}'
                ledger_filing['correctionFilingStatus'] = filing.parent_filing.status

            # add the collected meta_data
            if filing.meta_data:
                ledger_filing['data'] = filing.meta_data

            # orders
            if filing.court_order_file_number or filing.order_details:
                Filing._add_ledger_order(filing, ledger_filing)

            ledger.append(ledger_filing)

        return ledger

    @staticmethod
    def _add_ledger_order(filing: FilingStorage, ledger_filing: dict) -> dict:
        court_order_data = {'fileNumber': filing.court_order_file_number}
        if filing.court_order_date:
            court_order_data['orderDate'] = filing.court_order_date
        if filing.court_order_effect_of_order:
            court_order_data['effectOfOrder'] = filing.court_order_effect_of_order
        if filing.order_details:
            court_order_data['orderDetails'] = filing.order_details

        if not ledger_filing.get('data'):
            ledger_filing['data'] = {}
        ledger_filing['data']['order'] = court_order_data

    @staticmethod
    def get_document_list(business_identifier, filing, request) -> Optional[dict]:
        """Return a list of documents for a particular filing."""
        if not filing \
            or filing.status in (
                Filing.Status.PAPER_ONLY,
                Filing.Status.DRAFT,
                Filing.Status.PENDING,
            ):  # noqa: E125; lint conflicts on the indenting
            return None

        doc_url = request.url

        documents = {'documents': {
                     'primary': f'{doc_url}/{filing.filing_type}',
                     'receipt': f'{doc_url}/receipt'
                     }}

        if filing.status in (
            Filing.Status.PAID,
        ):
            return documents

        if filing.status in (
            Filing.Status.COMPLETED,
            Filing.Status.CORRECTED,
        ) and (
            legal_filings := filing.legal_filings(False)
        ) and (
            (f := [list(x.keys()) for x in legal_filings])
            and (legal_docs := [item for sublist in f for item in sublist])
        ):
            documents['documents']['legalFilings'] = \
                [{doc: f'{doc_url}/{doc}'} for doc in legal_docs]

        return documents
