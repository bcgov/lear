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
# limitations under the License
"""Filings are legal documents that alter the state of a business."""
import copy
from datetime import date, datetime
from enum import Enum
from http import HTTPStatus
from typing import List

from sqlalchemy import desc, event, inspect
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import backref

from legal_api.exceptions import BusinessException
from legal_api.schemas import rsbc_schemas

from .db import db


class Filing(db.Model):  # pylint: disable=too-many-instance-attributes; allowing the model to be deep.
    """Immutable filing record.

    Manages the filing ledger for the associated business.
    """

    class Status(Enum):
        """Render an Enum of the Filing Statuses."""

        COMPLETED = 'COMPLETED'
        DRAFT = 'DRAFT'
        EPOCH = 'EPOCH'
        ERROR = 'ERROR'
        PAID = 'PAID'
        PENDING = 'PENDING'

    FILINGS = {'annualReport': {'name': 'annualReport', 'title': 'Annual Report Filing', 'code': 'OTANN'},
               'changeOfAddress': {'name': 'changeOfAddress', 'title': 'Change of Address Filing', 'code': 'OTADD'},
               'changeOfDirectors': {'name': 'changeOfDirectors', 'title': 'Change of Directors Filing',
                                     'code': 'OTCDR'},
               'changeOfName': {'name': 'changeOfName', 'title': 'Change of Name Filing'},
               'specialResolution': {'name': 'specialResolution', 'title': 'Special Resolution'},
               'voluntaryDissolution': {'name': 'voluntaryDissolution', 'title': 'Voluntary Dissolution'}
               }

    __tablename__ = 'filings'

    id = db.Column(db.Integer, primary_key=True)
    _completion_date = db.Column('completion_date', db.DateTime(timezone=True))
    _filing_date = db.Column('filing_date', db.DateTime(timezone=True), default=datetime.utcnow)
    _filing_type = db.Column('filing_type', db.String(30))
    _filing_json = db.Column('filing_json', JSONB)
    effective_date = db.Column('effective_date', db.DateTime(timezone=True), default=datetime.utcnow)
    _payment_token = db.Column('payment_id', db.String(4096))
    _payment_completion_date = db.Column('payment_completion_date', db.DateTime(timezone=True))
    colin_event_id = db.Column('colin_event_id', db.Integer)
    _status = db.Column('status', db.String(10), default='DRAFT')
    paper_only = db.Column('paper_only', db.Boolean, unique=False, default=False)

    # relationships
    transaction_id = db.Column('transaction_id', db.BigInteger,
                               db.ForeignKey('transaction.id'))
    business_id = db.Column('business_id', db.Integer,
                            db.ForeignKey('businesses.id'))
    submitter_id = db.Column('submitter_id', db.Integer,
                             db.ForeignKey('users.id'))

    filing_submitter = db.relationship('User',
                                       backref=backref('filing_submitter', uselist=False),
                                       foreign_keys=[submitter_id])

    # properties
    @property
    def completion_date(self):
        """Property containing the filing type."""
        return self._completion_date

    @hybrid_property
    def filing_date(self):
        """Property containing the date a filing was submitted."""
        return self._filing_date

    @filing_date.setter
    def filing_date(self, value: datetime):
        if self.locked:
            self._raise_default_lock_exception()
        self._filing_date = value

    @property
    def filing_type(self):
        """Property containing the filing type."""
        return self._filing_type

    @hybrid_property
    def payment_token(self):
        """Property containing the payment token."""
        return self._payment_token

    @payment_token.setter
    def payment_token(self, token: int):
        if self.locked:
            self._raise_default_lock_exception()
        self._payment_token = token

    @hybrid_property
    def payment_completion_date(self):
        """Property containing the date the payment cleared."""
        return self._payment_completion_date

    @payment_completion_date.setter
    def payment_completion_date(self, value: datetime):

        if self.locked or \
                (self._payment_token and self._filing_json):
            self._payment_completion_date = value
            if self.effective_date is None or \
                self.effective_date <= self._payment_completion_date:
                self._status = Filing.Status.COMPLETED.value
        else:
            raise BusinessException(
                error="Payment Dates cannot set for unlocked filings unless the filing hasn't been saved yet.",
                status_code=HTTPStatus.FORBIDDEN
            )

    @property
    def status(self):
        """Property containing the filing status."""
        return self._status

    @hybrid_property
    def filing_json(self):
        """Property containing the filings data."""
        return self._filing_json

    @filing_json.setter
    def filing_json(self, json_data: dict):
        """Property containing the filings data."""
        if self.locked:
            self._raise_default_lock_exception()

        try:
            self._filing_type = json_data.get('filing').get('header').get('name')
            if not self._filing_type:
                raise Exception
        except Exception:
            raise BusinessException(
                error='No filings found.',
                status_code=HTTPStatus.UNPROCESSABLE_ENTITY
            )

        if self._payment_token:
            valid, err = rsbc_schemas.validate(json_data, 'filing')
            if not valid:
                self._filing_type = None
                self._payment_token = None
                errors = []
                for error in err:
                    errors.append({'path': '/'.join(error.path), 'error': error.message})
                raise BusinessException(
                    error=f'{errors}',
                    status_code=HTTPStatus.UNPROCESSABLE_ENTITY
                )

            self._status = Filing.Status.PENDING.value
        self._filing_json = json_data
        try:
            self.colin_event_id = int(json_data.get('filing').get('eventId'))
        except (AttributeError, TypeError):
            # eventId is from colin_api (will not be set until added in colin db)
            # todo: could make the post call for filing with json_data to colin api here and then set the colin_event_Id
            pass

    @property
    def locked(self):
        """Return the locked state of the filing.

        Once a filing, with valid json has an invoice attached, it can no longer be altered and is locked.
        Exception to this rule, payment_completion_date requires the filing to be locked.
        """
        insp = inspect(self)
        attr_state = insp.attrs._payment_token  # pylint: disable=protected-access;
        # inspect requires the member, and the hybrid decorator doesn't help us here

        if (self._payment_token and not attr_state.history.added) or self.colin_event_id:
            return True

        return False

    def set_processed(self):
        """Assign the completion date, unless it is already set."""
        if not self._completion_date:
            self._completion_date = datetime.utcnow()

    @staticmethod
    def _raise_default_lock_exception():
        raise BusinessException(
            error='Filings cannot be changed after the invoice is created.',
            status_code=HTTPStatus.FORBIDDEN
        )

    # json serializer
    @property
    def json(self):
        """Return a json representation of this object."""
        try:
            json_submission = copy.deepcopy(self.filing_json)
            json_submission['filing']['header']['date'] = datetime.date(self.filing_date).isoformat()
            json_submission['filing']['header']['filingId'] = self.id
            json_submission['filing']['header']['name'] = self.filing_type
            json_submission['filing']['header']['colinId'] = self.colin_event_id
            json_submission['filing']['header']['status'] = self.status

            # if availableOnPaper is not defined in filing json, use the flag on the filing record
            if json_submission['filing']['header'].get('availableOnPaperOnly', None) is None:
                json_submission['filing']['header']['availableOnPaperOnly'] = self.paper_only

            if self.effective_date:
                json_submission['filing']['header']['effectiveDate'] = self.effective_date
            if self._payment_token:
                json_submission['filing']['header']['paymentToken'] = self.payment_token
            if self.submitter_id:
                json_submission['filing']['header']['submitter'] = self.filing_submitter.username
            return json_submission
        except Exception:  # noqa: B901, E722
            raise KeyError

    @classmethod
    def find_by_id(cls, filing_id: str = None):
        """Return a Business by the id assigned by the Registrar."""
        filing = None
        if filing_id:
            filing = cls.query.filter_by(id=filing_id).one_or_none()
        return filing

    @staticmethod
    def get_filing_by_payment_token(token: str):
        """Return a Filing by it's payment token."""
        filing = db.session.query(Filing). \
            filter(Filing.payment_token == token). \
            one_or_none()
        return filing

    @staticmethod
    def get_filings_by_status(business_id: int, status: [], after_date: date = None):
        """Return the filings with statuses in the status array input."""
        query = db.session.query(Filing). \
            filter(Filing.business_id == business_id). \
            filter(Filing._status.in_(status)). \
            order_by(desc(Filing.filing_date))

        if after_date:
            query = query.filter(Filing._filing_date >= after_date)

        return query.all()

    @staticmethod
    def get_filings_by_type(business_id: int, filing_type: str):
        """Return the filings of a particular type."""
        filings = db.session.query(Filing). \
            filter(Filing.business_id == business_id). \
            filter(Filing._filing_type == filing_type). \
            filter(Filing._status != Filing.Status.COMPLETED.value). \
            order_by(desc(Filing.filing_date)). \
            all()
        return filings

    @staticmethod
    def get_a_businesses_most_recent_filing_of_a_type(business_id: int, filing_type: str):
        """Return the filings of a particular type."""
        max_filing = db.session.query(db.func.max(Filing._filing_date).label('last_filing_date')).\
            filter(Filing._filing_type == filing_type). \
            filter(Filing.business_id == business_id). \
            subquery()

        filing = Filing.query.join(max_filing, Filing._filing_date == max_filing.c.last_filing_date). \
            filter(Filing.business_id == business_id). \
            filter(Filing._filing_type == filing_type). \
            filter(Filing._status == Filing.Status.COMPLETED.value)

        return filing.one_or_none()

    @staticmethod
    def get_completed_filings_for_colin():
        """Return the filings with statuses in the status array input."""
        filings = db.session.query(Filing). \
            filter(Filing.colin_event_id == None,  # pylint: disable=singleton-comparison # noqa: E711;
                   Filing._status == Filing.Status.COMPLETED.value).all()
        return filings

    @staticmethod
    def get_all_filings_by_status(status):
        """Return all filings based on status."""
        filings = db.session.query(Filing). \
            filter(Filing._status == status).all()  # pylint: disable=singleton-comparison # noqa: E711;
        return filings

    def save(self):
        """Save and commit immediately."""
        db.session.add(self)
        db.session.commit()

    def save_to_session(self):
        """Save toThe session, do not commit immediately."""
        db.session.add(self)

    def delete(self):
        """Raise an error if the filing is locked."""
        if self.locked:
            raise BusinessException(
                error='Deletion not allowed.',
                status_code=HTTPStatus.FORBIDDEN
            )
        db.session.delete(self)
        db.session.commit()

    def legal_filings(self) -> List:
        """Return a list of the filings extracted from this filing submission.

        Returns: {
            List: or None of the Legal Filing JSON segments.
            }
        """
        if not self.filing_json:
            return None

        legal_filings = []
        filing = self.filing_json
        for k in filing['filing'].keys():
            if Filing.FILINGS.get(k, None):
                legal_filings.append({k: copy.deepcopy(filing['filing'].get(k))})

        return legal_filings


@event.listens_for(Filing, 'before_delete')
def block_filing_delete_listener_function(mapper, connection, target):  # pylint: disable=unused-argument
    """Raise an error when a delete is attempted on a Filing."""
    filing = target

    if filing.locked:
        raise BusinessException(
            error='Deletion not allowed.',
            status_code=HTTPStatus.FORBIDDEN
        )


@event.listens_for(Filing, 'before_insert')
@event.listens_for(Filing, 'before_update')
def receive_before_change(mapper, connection, target):  # pylint: disable=unused-argument; SQLAlchemy callback signature
    """Set the state of the filing, based upon column values."""
    filing = target
    # changes are part of the class and are not externalized

    if filing.filing_type == 'lear_epoch':
        filing._status = Filing.Status.EPOCH.value  # pylint: disable=protected-access

    elif filing.transaction_id:
        filing._status = Filing.Status.COMPLETED.value  # pylint: disable=protected-access

    elif filing.payment_completion_date:
        filing._status = Filing.Status.PAID.value  # pylint: disable=protected-access

    elif filing.payment_token or filing.colin_event_id:
        filing._status = Filing.Status.PENDING.value  # pylint: disable=protected-access

    else:
        filing._status = Filing.Status.DRAFT.value  # pylint: disable=protected-access
