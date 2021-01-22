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
from __future__ import annotations

# from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional

from legal_api.core.utils import diff_dict, diff_list
from legal_api.models import Business, Filing as FilingStorage  # noqa: I001
from legal_api.services import VersionedBusinessDetailsService
from legal_api.utils.datetime import date, datetime


# @dataclass(init=False, repr=False)
class Filing:
    """Domain class for Filings."""

    class Status(Enum):
        """Render an Enum of the Filing Statuses."""

        COMPLETED = 'COMPLETED'
        DRAFT = 'DRAFT'
        EPOCH = 'EPOCH'
        ERROR = 'ERROR'
        PAID = 'PAID'
        PENDING = 'PENDING'
        PAPER_ONLY = 'PAPER_ONLY'
        PENDING_CORRECTION = 'PENDING_CORRECTION'

    class FilingTypes(Enum):
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
        DISSOLVED = 'dissolved'
        INCORPORATIONAPPLICATION = 'incorporationApplication'
        RESTORATIONAPPLICATION = 'restorationApplication'
        SPECIALRESOLUTION = 'specialResolution'
        TRANSITION = 'transition'
        VOLUNTARYDISSOLUTION = 'voluntaryDissolution'
        VOLUNTARYLIQUIDATION = 'voluntaryLiquidation'

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
        self._paper_only: bool
        self._payment_account: Optional[str] = None

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

    @property
    def json(self) -> Optional[Dict]:
        """Return a dict representing the filing json."""
        if not self._storage or (self._storage and self._storage.status not in [Filing.Status.COMPLETED.value,
                                                                                Filing.Status.PAID.value,
                                                                                Filing.Status.PENDING.value,
                                                                                ]):
            return self.raw

        # this will return the raw filing instead of the versioned filing until
        # payment and processing are complete.
        # This ASSUMES that the JSONSchemas remain valid for that period of time
        # which fits with the N-1 approach to versioning, and
        # that handling of filings stuck in PENDING are handled appropriately.
        if self._storage.status in [Filing.Status.PAID.value,
                                    Filing.Status.PENDING.value,
                                    ]:
            filing_json = self.raw
        else:  # Filing.Status.COMPLETED.value
            filing_json = VersionedBusinessDetailsService.get_revision(self.id, self._storage.business_id)

        if self.filing_type == Filing.FilingTypes.CORRECTION.value:
            if correction_id := filing_json.get('filing', {}).get('correction', {}).get('correctedFilingId'):
                if diff := self._diff(filing_json, correction_id):
                    filing_json['filing']['correction']['diff'] = diff

        return filing_json

    @ json.setter
    def json(self, filing_submission):
        """Add the raw json to the filing."""
        self._raw = filing_submission

    @ property
    def storage(self) -> Optional[FilingStorage]:
        """
        (Deprecated) Return filing model.

        Model is exposed to generate pdf. Used in GET api `/<string:identifier>/filings/<int:filing_id>`
        """
        if not self._storage:
            self._storage = FilingStorage()
        return self._storage

    @ storage.setter
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
