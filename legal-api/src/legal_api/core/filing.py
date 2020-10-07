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

from legal_api.models import Business, Filing as FilingStorage, db
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

    def __init__(self):
        """Create the Filing."""
        self._storage: Optional[FilingStorage] = None
        self._id: str = ''
        self._raw: Optional[Dict] = None
        self._completion_date: datetime
        self._filing_date: datetime
        self._filing_type: str
        self._effective_date: datetime
        self._payment_status_code: str
        self._payment_token: str
        self._payment_completion_date: datetime
        self._status: str
        self._paper_only: bool

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
        if not self._raw:
            if self._storage:
                self._raw = self._storage.json
            else:
                return {}
        return self._raw

    @property
    def json(self) -> Optional[Dict]:
        """Return a dict representing the filing json."""
        if self._storage:
            if self._storage.status == Filing.Status.COMPLETED.value:
                return self.raw  # Implement versioned domain model
            else:
                return self.raw
        return {}

    @property
    def storage(self) -> Optional[FilingStorage]:
        """Return filing."""
        self._storage

    @json.setter
    def json(self, filing_submission):
        """Add the raw json to the filing."""
        self._raw = filing_submission

    def save(self):
        """Save the filing."""
        if not self._storage:
            self._storage = FilingStorage()
        self._storage.filing_json = self._raw
        self._storage.save()

    @staticmethod
    def validate():
        """Validate the filing."""
        raise NotImplementedError

    @staticmethod
    def get(identifier, filing_id=None) -> Optional[Filing]:
        """Return a Filing domain by the id."""
        filing = Filing()
        # filing._storage = FilingStorage.find_by_id(filing_id)
        if identifier.startswith('T'):
            filing._storage = FilingStorage.get_temp_reg_filing(identifier)
        else:
            filing._storage = Business.get_filing_by_id(identifier, filing_id)
        return filing

    @staticmethod
    def get_filings_by_status(business_id: int, status: [], after_date: date = None):
        """Return the filings with statuses in the status array input."""
        storages = FilingStorage.get_filings_by_status(business_id, status, after_date)
        filings = []
        for storage in storages:
            filing = Filing()
            filing._storage = storage
            filings.append(filing)

        return filings
