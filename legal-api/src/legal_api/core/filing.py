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
from typing import Dict, Final, List, Optional

from flask import current_app, url_for
from flask_jwt_oidc import JwtManager
from sqlalchemy import desc

from legal_api.core.meta import FilingMeta
from legal_api.models import Business, Document, DocumentType
from legal_api.models import Filing as FilingStorage  # noqa: I001
from legal_api.models import UserRoles
from legal_api.services import VersionedBusinessDetailsService  # noqa: I005
from legal_api.services.authz import has_roles, is_competent_authority  # noqa: I005
from legal_api.utils.datetime import date, datetime  # noqa: I005

from .constants import REDACTED_STAFF_SUBMITTER


# @dataclass(init=False, repr=False)
class Filing:  # pylint: disable=too-many-public-methods
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
        WITHDRAWN = 'WITHDRAWN'

        # filings with staff review
        APPROVED = 'APPROVED'
        AWAITING_REVIEW = 'AWAITING_REVIEW'
        CHANGE_REQUESTED = 'CHANGE_REQUESTED'
        REJECTED = 'REJECTED'

    class FilingTypes(str, Enum):
        """Render an Enum of all Filing Types."""

        ADMIN_FREEZE = 'adminFreeze'
        AGMEXTENSION = 'agmExtension'
        AGMLOCATIONCHANGE = 'agmLocationChange'
        ALTERATION = 'alteration'
        AMALGAMATIONAPPLICATION = 'amalgamationApplication'
        AMALGAMATIONOUT = 'amalgamationOut'
        AMENDEDAGM = 'amendedAGM'
        AMENDEDANNUALREPORT = 'amendedAnnualReport'
        AMENDEDCHANGEOFDIRECTORS = 'amendedChangeOfDirectors'
        ANNUALREPORT = 'annualReport'
        APPOINTRECEIVER = 'appointReceiver'
        CEASERECEIVER = 'ceaseReceiver'
        CHANGEOFADDRESS = 'changeOfAddress'
        CHANGEOFDIRECTORS = 'changeOfDirectors'
        CHANGEOFNAME = 'changeOfName'
        CHANGEOFREGISTRATION = 'changeOfRegistration'
        CONSENTAMALGAMATIONOUT = 'consentAmalgamationOut'
        CONSENTCONTINUATIONOUT = 'consentContinuationOut'
        CONTINUATIONIN = 'continuationIn'
        CONTINUATIONOUT = 'continuationOut'
        CONTINUEDOUT = 'continuedOut'
        CONVERSION = 'conversion'
        CORRECTION = 'correction'
        COURTORDER = 'courtOrder'
        DISSOLUTION = 'dissolution'
        DISSOLVED = 'dissolved'
        INCORPORATIONAPPLICATION = 'incorporationApplication'
        NOTICEOFWITHDRAWAL = 'noticeOfWithdrawal'
        PUTBACKOFF = 'putBackOff'
        PUTBACKON = 'putBackOn'
        REGISTRARSNOTATION = 'registrarsNotation'
        REGISTRARSORDER = 'registrarsOrder'
        REGISTRATION = 'registration'
        RESTORATION = 'restoration'
        RESTORATIONAPPLICATION = 'restorationApplication'
        SPECIALRESOLUTION = 'specialResolution'
        TRANSITION = 'transition'
        TRANSPARENCY_REGISTER = 'transparencyRegister'

    class FilingTypesCompact(str, Enum):
        """Render enum for filing types with sub-types."""

        DISSOLUTION_VOLUNTARY = 'dissolution.voluntary'
        DISSOLUTION_ADMINISTRATIVE = 'dissolution.administrative'
        RESTORATION_FULL_RESTORATION = 'restoration.fullRestoration'
        RESTORATION_LIMITED_RESTORATION = 'restoration.limitedRestoration'
        RESTORATION_LIMITED_RESTORATION_EXT = 'restoration.limitedRestorationExtension'
        RESTORATION_LIMITED_RESTORATION_TO_FULL = 'restoration.limitedRestorationToFull'
        AMALGAMATION_APPLICATION_REGULAR = 'amalgamationApplication.regular'
        AMALGAMATION_APPLICATION_VERTICAL = 'amalgamationApplication.vertical'
        AMALGAMATION_APPLICATION_HORIZONTAL = 'amalgamationApplication.horizontal'
        TRANSPARENCY_REGISTER_ANNUAL = 'transparencyRegister.annual'
        TRANSPARENCY_REGISTER_CHANGE = 'transparencyRegister.change'
        TRANSPARENCY_REGISTER_INITIAL = 'transparencyRegister.initial'

    NEW_BUSINESS_FILING_TYPES: Final = [
        FilingTypes.AMALGAMATIONAPPLICATION,
        FilingTypes.CONTINUATIONIN,
        FilingTypes.INCORPORATIONAPPLICATION,
        FilingTypes.REGISTRATION,
    ]

    def __init__(self):
        """Create the Filing."""
        self._storage: Optional[FilingStorage] = None
        self._id: str = ''
        self._raw: Optional[Dict] = None
        self._completion_date: datetime
        self._filing_date: datetime
        self._filing_type: Optional[str] = None
        self._effective_date: Optional[datetime] = None
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
        if (self._storage
            and (submitter_roles := self._storage.submitter_roles)
                and self.redact_submitter(submitter_roles, jwt)):
            filing['filing']['header']['submitter'] = REDACTED_STAFF_SUBMITTER

        return filing

    @property
    def is_future_effective(self) -> bool:
        """Return True if the effective date is in the future."""
        with suppress(AttributeError, TypeError):
            if self._storage.effective_date > self._storage.payment_completion_date:
                return True
        return False

    # json is returned as a property defined after this method
    def get_json(self) -> Optional[Dict]:
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
        elif self._storage.status in [Filing.Status.PAID.value,
                                      Filing.Status.PENDING.value]:
            if self._storage.tech_correction_json:
                filing = self._storage.tech_correction_json
            else:
                filing = self.raw

            filing_json = filing

        else:  # Filing.Status.COMPLETED.value
            filing_json = VersionedBusinessDetailsService.get_revision(self.id, self._storage.business_id)

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

    @staticmethod
    def validate():
        """Validate the filing."""
        raise NotImplementedError

    @staticmethod
    def get(identifier, filing_id=None) -> Optional[Filing]:
        """Return a Filing domain by the id."""
        if identifier.startswith('T'):
            storage = FilingStorage.get_temp_reg_filing(identifier, filing_id)
        else:
            storage = Business.get_filing_by_id(identifier, filing_id)

        if storage:
            filing = Filing()
            filing._storage = storage  # pylint: disable=protected-access
            return filing

        return None

    @staticmethod
    def get_by_withdrawn_filing_id(filing_id, withdrawn_filing_id, filing_type: str = None) -> Optional[Filing]:
        """Return a Filing domain by the id, withdrawn_filing_id and filing_type."""
        storage = FilingStorage.get_temp_reg_filing_by_withdrawn_filing(filing_id, withdrawn_filing_id, filing_type)

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
    def get_filings_by_status(business_id: int, status: list, after_date: date = None):
        """Return the filings with statuses in the status array input."""
        storages = FilingStorage.get_filings_by_status(business_id, status, after_date)
        filings = []
        for storage in storages:
            filing = Filing()
            filing.storage = storage
            filings.append(filing)

        return filings

    @staticmethod
    def get_most_recent_filing_json(business_id: str, filing_type: str = None, jwt: JwtManager = None):
        """Return the most recent filing json."""
        if storage := FilingStorage.get_most_recent_filing(business_id, filing_type):
            submitter_displayname = REDACTED_STAFF_SUBMITTER
            if (submitter := storage.filing_submitter) \
                and submitter.username and jwt \
                    and not Filing.redact_submitter(storage.submitter_roles, jwt):
                submitter_displayname = submitter.username

            filing_json = storage.json
            filing_json['filing']['header']['submitter'] = submitter_displayname
            return filing_json
        return None

    def legal_filings(self) -> Optional[List]:
        """Return a list of the filings extracted from this filing submission.

        Returns: {
            List: or None of the Legal Filing JSON segments.
            }
        """
        if not (filing := self.get_json()):
            return None

        legal_filings = []
        for k in filing['filing'].keys():  # pylint: disable=unsubscriptable-object
            if FilingStorage.FILINGS.get(k, None):
                legal_filings.append(
                    {k: copy.deepcopy(filing['filing'].get(k))})  # pylint: disable=unsubscriptable-object

        return legal_filings

    @staticmethod
    def redact_submitter(submitter_roles: list, jwt: JwtManager) -> Optional[bool]:
        """Redact the submitter of the filing."""
        if not (submitter_roles or jwt):
            return None

        with suppress(KeyError, TypeError):
            if (UserRoles.staff in submitter_roles
                or UserRoles.system in submitter_roles) \
                    and not has_roles(jwt, [UserRoles.staff, ]):
                return True
        return False

    @staticmethod
    def ledger(business_id: int,  # pylint: disable=too-many-arguments
               jwt: JwtManager = None,
               statuses: List(str) = None,
               start: int = None,
               size: int = None,
               effective_date=None,
               **kwargs) \
            -> list:
        """Return the ledger list by directly querying the storage objects.

        Note: Sort of breaks the "core" style, but searches are always interesting ducks.
        """
        base_url = current_app.config.get('LEGAL_API_BASE_URL')

        business = Business.find_by_internal_id(business_id)

        query = FilingStorage.query.filter(FilingStorage.business_id == business_id)

        if effective_date:
            query = query.filter(FilingStorage.effective_date <= effective_date)
        if statuses and isinstance(statuses, List):
            query = query.filter(FilingStorage._status.in_(statuses))  # pylint: disable=protected-access;required by SA

        if start:
            query = query.offset(start)
        if size:
            query = query.limit(size)

        query = query.order_by(desc(FilingStorage.filing_date))

        ledger = []
        for filing in query.all():

            submitter_displayname = REDACTED_STAFF_SUBMITTER
            if (submitter := filing.filing_submitter) \
                and submitter.username and jwt \
                    and not Filing.redact_submitter(filing.submitter_roles, jwt):
                submitter_displayname = submitter.display_name or submitter.username

            ledger_filing = {
                'availableOnPaperOnly': filing.paper_only,
                'businessIdentifier': business.identifier,
                'displayName': FilingMeta.display_name(business, filing=filing),
                'effectiveDate': filing.effective_date,
                'filingId': filing.id,
                'name': filing.filing_type,
                'paymentStatusCode': filing.payment_status_code,
                'status': filing.status,
                'submitter': submitter_displayname,
                'submittedDate': filing._filing_date,  # pylint: disable=protected-access

                **Filing.common_ledger_items(business.identifier, filing),
            }
            if filing.filing_sub_type:
                ledger_filing['filingSubType'] = filing.filing_sub_type

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
    def common_ledger_items(business_identifier: str, filing_storage: FilingStorage) -> dict:
        """Return attributes and links that also get included in T-business filings."""
        no_output_filing_types = ['Involuntary Dissolution', 'conversion']
        base_url = current_app.config.get('LEGAL_API_BASE_URL')
        filing = Filing()
        filing._storage = filing_storage  # pylint: disable=protected-access
        return {
            'displayLedger': not filing_storage.hide_in_ledger,
            'commentsCount': filing_storage.comments_count,
            'commentsLink': f'{base_url}/{business_identifier}/filings/{filing_storage.id}/comments',
            'documentsLink': f'{base_url}/{business_identifier}/filings/{filing_storage.id}/documents' if
            filing_storage.filing_type not in no_output_filing_types else None,
            'filingLink': f'{base_url}/{business_identifier}/filings/{filing_storage.id}',
            'isFutureEffective': filing.is_future_effective,
            'withdrawalPending': filing_storage.withdrawal_pending
        }

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
    def get_document_list(business,  # pylint: disable=too-many-locals disable=too-many-branches
                          filing,
                          jwt: JwtManager) -> Optional[dict]:
        """Return a list of documents for a particular filing."""
        no_output_filings = [
            Filing.FilingTypes.CONVERSION.value,
            Filing.FilingTypes.PUTBACKOFF.value,
            Filing.FilingTypes.PUTBACKON.value,
            Filing.FilingTypes.REGISTRARSNOTATION.value,
            Filing.FilingTypes.REGISTRARSORDER.value,
        ]

        if not filing \
            or filing.status in (
                Filing.Status.PAPER_ONLY,
                Filing.Status.DRAFT,
                Filing.Status.PENDING,
                Filing.Status.AWAITING_REVIEW,
                Filing.Status.CHANGE_REQUESTED,
                Filing.Status.APPROVED,
                Filing.Status.REJECTED,
            ):  # noqa: E125; lint conflicts on the indenting
            return None

        base_url = current_app.config.get('LEGAL_API_BASE_URL')
        base_url = base_url[:base_url.find('/api')]
        identifier = business.identifier if business else filing.storage.temp_reg
        if not identifier and filing.storage.withdrawn_filing_id:
            withdrawn_filing = Filing.find_by_id(filing.storage.withdrawn_filing_id)
            identifier = withdrawn_filing.storage.temp_reg

        doc_url = url_for('API2.get_documents', **{'identifier': identifier,
                                                   'filing_id': filing.id,
                                                   'legal_filing_name': None})

        documents = {'documents': {}}
        # for paper_only filings return and empty documents list
        if filing.storage and filing.storage.paper_only:
            return documents

        if filing.storage and filing.storage.filing_type in no_output_filings:
            return documents

        user_is_ca = is_competent_authority(jwt)

        # return a receipt for filings completed in our system (but not for ca users
        # see https://github.com/bcgov/entity/issues/21881
        if filing.storage and filing.storage.payment_completion_date:
            if filing.filing_type == 'courtOrder' and \
                    (filing.storage.documents.filter(
                        Document.type == DocumentType.COURT_ORDER.value).one_or_none()):
                documents['documents']['uploadedCourtOrder'] = f'{base_url}{doc_url}/uploadedCourtOrder'
            documents['documents']['receipt'] = f'{base_url}{doc_url}/receipt'

        no_legal_filings_in_paid_withdrawn_status = [
            Filing.FilingTypes.AMALGAMATIONOUT.value,
            Filing.FilingTypes.REGISTRATION.value,
            Filing.FilingTypes.CONSENTAMALGAMATIONOUT.value,
            Filing.FilingTypes.CONSENTCONTINUATIONOUT.value,
            Filing.FilingTypes.COURTORDER.value,
            Filing.FilingTypes.CONTINUATIONOUT.value,
            Filing.FilingTypes.AGMEXTENSION.value,
            Filing.FilingTypes.AGMLOCATIONCHANGE.value,
            Filing.FilingTypes.TRANSPARENCY_REGISTER.value,
        ]
        if (filing.status in (Filing.Status.PAID, Filing.Status.WITHDRAWN) or
                (filing.status == Filing.Status.COMPLETED and
                    filing.filing_type == Filing.FilingTypes.NOTICEOFWITHDRAWAL.value)) and \
            not (filing.filing_type in no_legal_filings_in_paid_withdrawn_status
                 or (filing.filing_type == Filing.FilingTypes.DISSOLUTION.value and
                     business.legal_type in [
                         Business.LegalTypes.SOLE_PROP.value,
                         Business.LegalTypes.PARTNERSHIP.value])
                 ):
            documents['documents']['legalFilings'] = \
                [{filing.filing_type: f'{base_url}{doc_url}/{filing.filing_type}'}, ]
            if user_is_ca:
                del documents['documents']['receipt']
            return documents

        if filing.status in (
            Filing.Status.COMPLETED,
            Filing.Status.CORRECTED,
        ) and filing.storage.meta_data:
            if legal_filings := filing.storage.meta_data.get('legalFilings'):
                legal_filings_copy = copy.deepcopy(legal_filings)
                if (filing.filing_type == Filing.FilingTypes.SPECIALRESOLUTION.value and
                        business.legal_type == Business.LegalTypes.COOP.value):
                    # add special resolution application output
                    documents['documents']['specialResolutionApplication'] = \
                        f'{base_url}{doc_url}/specialResolutionApplication'
                    if Filing.FilingTypes.CHANGEOFNAME.value in legal_filings:
                        # suppress change of name output for MVP since the design is outdated.
                        legal_filings_copy.remove(Filing.FilingTypes.CHANGEOFNAME.value)
                    if Filing.FilingTypes.ALTERATION.value in legal_filings:
                        # suppress alteration output for MVP since the design is outdated.
                        legal_filings_copy.remove(Filing.FilingTypes.ALTERATION.value)

                no_legal_filings = [
                    Filing.FilingTypes.AMALGAMATIONOUT.value,
                    Filing.FilingTypes.CONSENTAMALGAMATIONOUT.value,
                    Filing.FilingTypes.CONSENTCONTINUATIONOUT.value,
                    Filing.FilingTypes.CONTINUATIONOUT.value,
                    Filing.FilingTypes.COURTORDER.value,
                    Filing.FilingTypes.AGMEXTENSION.value,
                    Filing.FilingTypes.AGMLOCATIONCHANGE.value,
                    Filing.FilingTypes.TRANSPARENCY_REGISTER.value,
                ]
                if filing.filing_type not in no_legal_filings:
                    documents['documents']['legalFilings'] = \
                        [{doc: f'{base_url}{doc_url}/{doc}'} for doc in legal_filings_copy]

                # get extra outputs
                if filing.storage.transaction_id and \
                        (bus_rev_temp := VersionedBusinessDetailsService.get_business_revision_obj(
                        filing.storage, business.id)):
                    business = bus_rev_temp

                adds = [FilingMeta.get_all_outputs(business.legal_type, doc) for doc in legal_filings]
                additional = set([item for sublist in adds for item in sublist])

                FilingMeta.alter_outputs(filing.storage, business, additional)
                for doc in additional:
                    documents['documents'][doc] = f'{base_url}{doc_url}/{doc}'

                if has_roles(jwt, [UserRoles.staff]):
                    if static_docs := FilingMeta.get_static_documents(filing.storage, f'{base_url}{doc_url}/static'):
                        documents['documents']['staticDocuments'] = static_docs

        if user_is_ca:
            del documents['documents']['receipt']
        return documents
