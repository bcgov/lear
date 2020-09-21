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

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from legal_api.models import Filing as FilingStorage
from legal_api.utils.datetime import date, datetime


# @dataclass(init=False, repr=False)
class Filing:

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
    def id(self) -> str:
        if not self._id:
            if self._storage:
                self._id = self._storage.id
        return self._id

    @property
    def raw(self) -> Optional[Dict]:
        if not self._raw:
            return {}
        return self._raw

    @property
    def json(self) -> Optional[Dict]:
        return self._raw

    @json.setter
    def json(self, filing_submission) -> Optional[Dict]:
        self._raw = filing_submission
        return None

    def save(self):
        if not self._storage:
            self._storage = FilingStorage()
        self._storage.filing_json = self._raw
        self._storage.save()

    def validate(self):
        raise NotImplemented
