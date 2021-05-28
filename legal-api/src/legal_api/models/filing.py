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

from flask import current_app
from sqlalchemy import desc, event, inspect, or_
from sqlalchemy.dialects.postgresql import JSONB, dialect
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import backref

from legal_api.exceptions import BusinessException
from legal_api.models.colin_event_id import ColinEventId
from legal_api.schemas import rsbc_schemas

from .db import db  # noqa: I001
from .comment import Comment  # noqa: I001,F401 pylint: disable=unused-import; needed by the SQLAlchemy relationship


class Filing(db.Model):  # pylint: disable=too-many-instance-attributes,too-many-public-methods
    # allowing the model to be deep.
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
        PENDING_CORRECTION = 'PENDING_CORRECTION'

    class Source(Enum):
        """Render an Enum of the Filing Sources."""

        COLIN = 'COLIN'
        LEAR = 'LEAR'

    # TODO: get legal types from defined class once table is made (getting it from Business causes circ import)
    FILINGS = {
        'alteration': {
            'name': 'alteration',
            'title': 'Notice of Alteration Filing',
            'codes': {
                'BC': 'ALTER',
                'BEN': 'ALTER'
            }
        },
        'annualReport': {
            'name': 'annualReport',
            'title': 'Annual Report Filing',
            'codes': {
                'CP': 'OTANN',
                'BEN': 'BCANN'
            }
        },
        'changeOfAddress': {
            'name': 'changeOfAddress',
            'title': 'Change of Address Filing',
            'codes': {
                'CP': 'OTADD',
                'BEN': 'BCADD'
            }
        },
        'changeOfDirectors': {
            'name': 'changeOfDirectors',
            'title': 'Change of Directors Filing',
            'codes': {
                'CP': 'OTCDR',
                'BEN': 'BCCDR'
            },
            'free': {
                'codes': {
                    'CP': 'OTFDR',
                    'BEN': 'BCFDR'
                }
            }
        },
        'changeOfName': {'name': 'changeOfName', 'title': 'Change of Name Filing'},
        'correction': {
            'name': 'correction',
            'title': 'Correction',
            'codes': {
                'BEN': 'CRCTN',
                'CP': 'CRCTN'
            }
        },
        'incorporationApplication': {
            'name': 'incorporationApplication',
            'title': 'Incorporation Application',
            'codes': {
                'BEN': 'BCINC'
            }
        },
        'specialResolution': {'name': 'specialResolution', 'title': 'Special Resolution',
                              'codes': {
                                  'CP': 'RES'}},
        'voluntaryDissolution': {'name': 'voluntaryDissolution', 'title': 'Voluntary Dissolution'},
        'transition': {
            'name': 'transition',
            'title': 'Transition',
            'codes': {
                'BC': 'TRANS',
                'BEN': 'TRANS'
            }
        }
    }

    __tablename__ = 'filings'
    # this mapper is used so that new and old versions of the service can be run simultaneously,
    # making rolling upgrades easier
    # This is used by SQLAlchemy to explicitly define which fields we're interested
    # so it doesn't freak out and say it can't map the structure if other fields are present.
    # This could occur from a failed deploy or during an upgrade.
    # The other option is to tell SQLAlchemy to ignore differences, but that is ambiguous
    # and can interfere with Alembic upgrades.
    __mapper_args__ = {
        'include_properties': [
            'id',
            '_completion_date',
            '_filing_date',
            '_filing_json',
            '_filing_type',
            '_payment_completion_date',
            '_payment_status_code',
            '_payment_token',
            '_source',
            '_status',
            'business_id',
            'court_order_date',
            'court_order_effect_of_order',
            'court_order_file_number',
            'effective_date',
            'paper_only',
            'colin_only',
            'parent_filing_id',
            'payment_account',
            'submitter_id',
            'tech_correction_json',
            'temp_reg',
            'transaction_id',
            'deletion_locked'
        ]
    }

    id = db.Column(db.Integer, primary_key=True)
    _completion_date = db.Column('completion_date', db.DateTime(timezone=True))
    _filing_date = db.Column('filing_date', db.DateTime(timezone=True), default=datetime.utcnow)
    _filing_type = db.Column('filing_type', db.String(30))
    _filing_json = db.Column('filing_json', JSONB)
    tech_correction_json = db.Column('tech_correction_json', JSONB)
    effective_date = db.Column('effective_date', db.DateTime(timezone=True), default=datetime.utcnow)
    _payment_status_code = db.Column('payment_status_code', db.String(50))
    _payment_token = db.Column('payment_id', db.String(4096))
    _payment_completion_date = db.Column('payment_completion_date', db.DateTime(timezone=True))
    _status = db.Column('status', db.String(20), default=Status.DRAFT)
    paper_only = db.Column('paper_only', db.Boolean, unique=False, default=False)
    colin_only = db.Column('colin_only', db.Boolean, unique=False, default=False)
    payment_account = db.Column('payment_account', db.String(30))
    _source = db.Column('source', db.String(15), default=Source.LEAR.value)
    court_order_file_number = db.Column('court_order_file_number', db.String(20))
    court_order_date = db.Column('court_order_date', db.DateTime(timezone=True), default=None)
    court_order_effect_of_order = db.Column('court_order_effect_of_order', db.String(500))
    deletion_locked = db.Column('deletion_locked', db.Boolean, unique=False, default=False)

    # # relationships
    transaction_id = db.Column('transaction_id', db.BigInteger,
                               db.ForeignKey('transaction.id'))
    business_id = db.Column('business_id', db.Integer,
                            db.ForeignKey('businesses.id'))
    temp_reg = db.Column('temp_reg', db.String(10),
                         db.ForeignKey('registration_bootstrap.identifier'))
    submitter_id = db.Column('submitter_id', db.Integer,
                             db.ForeignKey('users.id'))

    filing_submitter = db.relationship('User',
                                       backref=backref('filing_submitter', uselist=False),
                                       foreign_keys=[submitter_id])

    colin_event_ids = db.relationship('ColinEventId', lazy='select')

    comments = db.relationship('Comment', lazy='dynamic')

    parent_filing_id = db.Column(db.Integer, db.ForeignKey('filings.id'))
    parent_filing = db.relationship('Filing', remote_side=[id], backref=backref('children'))

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
    def payment_status_code(self):
        """Property containing the payment error type."""
        return self._payment_status_code

    @payment_status_code.setter
    def payment_status_code(self, error_type: str):
        if self.locked:
            self._raise_default_lock_exception()
        self._payment_status_code = error_type

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
    def source(self):
        """Property containing the filing source."""
        return self._source

    @source.setter
    def source(self, source: str):
        """Property containing the filing source."""
        if source not in [x.value for x in self.Source]:
            raise BusinessException(
                error='Tried to update the filing with an invalid source.',
                status_code=HTTPStatus.BAD_REQUEST
            )
        self._source = source

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
        except Exception as err:
            raise BusinessException(
                error='No filings found.',
                status_code=HTTPStatus.UNPROCESSABLE_ENTITY
            ) from err

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

    @property
    def locked(self):
        """Return the locked state of the filing.

        Once a filing, with valid json has an invoice attached, it can no longer be altered and is locked.
        Exception to this rule, payment_completion_date requires the filing to be locked.
        """
        insp = inspect(self)
        attr_state = insp.attrs._payment_token  # pylint: disable=protected-access;
        # inspect requires the member, and the hybrid decorator doesn't help us here
        if (self._payment_token and not attr_state.history.added) or self.colin_event_ids:
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

    @property
    def is_corrected(self):
        """Has this filing been corrected."""
        if (
                self.parent_filing and
                self.parent_filing.filing_type == Filing.FILINGS['correction'].get('name') and
                self.parent_filing.status == Filing.Status.COMPLETED.value
        ):
            return True
        return False

    @property
    def is_correction_pending(self):
        """Is there a pending correction for this filing."""
        if (
                self.parent_filing and
                self.parent_filing.filing_type == Filing.FILINGS['correction'].get('name') and
                self.parent_filing.status == Filing.Status.PENDING_CORRECTION.value
        ):
            return True
        return False

    # json serializer
    @property
    def json(self):
        """Return a json representation of this object."""
        try:
            json_submission = copy.deepcopy(self.filing_json)
            json_submission['filing']['header']['date'] = self._filing_date.isoformat()
            json_submission['filing']['header']['filingId'] = self.id
            json_submission['filing']['header']['name'] = self.filing_type
            json_submission['filing']['header']['status'] = self.status
            json_submission['filing']['header']['availableOnPaperOnly'] = self.paper_only
            json_submission['filing']['header']['inColinOnly'] = self.colin_only


            if self.effective_date:
                json_submission['filing']['header']['effectiveDate'] = self.effective_date.isoformat()
            if self._payment_status_code:
                json_submission['filing']['header']['paymentStatusCode'] = self.payment_status_code
            if self._payment_token:
                json_submission['filing']['header']['paymentToken'] = self.payment_token
            if self.submitter_id:
                json_submission['filing']['header']['submitter'] = self.filing_submitter.username
            if self.payment_account:
                json_submission['filing']['header']['paymentAccount'] = self.payment_account

            # add colin_event_ids
            json_submission['filing']['header']['colinIds'] = ColinEventId.get_by_filing_id(self.id)

            # add comments
            json_submission['filing']['header']['comments'] = [comment.json for comment in self.comments]

            # add affected filings list
            json_submission['filing']['header']['affectedFilings'] = [filing.id for filing in self.children]

            # add corrected flags
            json_submission['filing']['header']['isCorrected'] = self.is_corrected
            json_submission['filing']['header']['isCorrectionPending'] = self.is_correction_pending

            return json_submission
        except Exception as err:  # noqa: B901, E722
            raise KeyError from err

    @classmethod
    def find_by_id(cls, filing_id: str = None):
        """Return a Filing by the id."""
        filing = None
        if filing_id:
            filing = cls.query.filter_by(id=filing_id).one_or_none()
        return filing

    @staticmethod
    def get_temp_reg_filing(temp_reg_id: str, filing_id: str = None):
        """Return a Filing by it's payment token."""
        q = db.session.query(Filing).filter(Filing.temp_reg == temp_reg_id)

        if filing_id:
            q.filter(Filing.id == filing_id)

        filing = q.one_or_none()
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
            order_by(Filing._filing_date.desc(), Filing.effective_date.desc())  # pylint: disable=no-member;
        # member provided via SQLAlchemy

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
    def get_most_recent_legal_filing(business_id: str, filing_type: str):
        """Return the most recent filing containing the legal_filing type."""
        # Filing._filing_json.has_any(filing_type))).\

        expr = Filing._filing_json[('filing', filing_type)]
        max_filing = db.session.query(db.func.max(Filing._filing_date).label('last_filing_date')).\
            filter(Filing.business_id == business_id).\
            filter(or_(Filing._filing_type == filing_type,
                       expr.label('legal_filing_type').isnot(None))).\
            filter(Filing._status == Filing.Status.COMPLETED.value).\
            subquery()

        filing = Filing.query.join(max_filing, Filing._filing_date == max_filing.c.last_filing_date). \
            filter(Filing.business_id == business_id). \
            filter(Filing._status == Filing.Status.COMPLETED.value). \
            order_by(Filing.id.desc())

        # As the JSON query is new for most, leaving the debug stmnt
        # that dumps the query for easier debugging.
        current_app.logger.debug(
            str(filing.statement.compile(
                dialect=dialect(),
                compile_kwargs={'literal_binds': True}))
        )

        return filing.first()

    @staticmethod
    def get_completed_filings_for_colin():
        """Return the filings with statuses in the status array input."""
        filings = db.session.query(Filing). \
            filter(
                Filing.colin_event_ids == None,  # pylint: disable=singleton-comparison # noqa: E711;
                Filing._status == Filing.Status.COMPLETED.value,
                Filing.effective_date != None   # pylint: disable=singleton-comparison # noqa: E711;
            ).order_by(Filing.filing_date).all()
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

    def reset_filing_to_draft(self):
        """Reset Filing to draft and remove payment token."""
        self._status = Filing.Status.DRAFT.value
        self._payment_token = None
        self.save()

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
        for k in filing['filing'].keys():  # pylint: disable=unsubscriptable-object
            if Filing.FILINGS.get(k, None):
                legal_filings.append(
                    {k: copy.deepcopy(filing['filing'].get(k))})  # pylint: disable=unsubscriptable-object

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

    # skip this status updater if the flag is set
    # Scenario: if this is a correction filing, and would have been set to COMPLETE by the entity filer, leave it as is
    # because it's been set to PENDING_CORRECTION by the entity filer.
    if hasattr(filing, 'skip_status_listener') and filing.skip_status_listener:
        return

    # changes are part of the class and are not externalized
    if filing.filing_type == 'lear_epoch':
        filing._status = Filing.Status.EPOCH.value  # pylint: disable=protected-access

    elif filing.transaction_id:
        filing._status = Filing.Status.COMPLETED.value  # pylint: disable=protected-access

    elif filing.payment_completion_date or filing.source == Filing.Source.COLIN.value:
        filing._status = Filing.Status.PAID.value  # pylint: disable=protected-access

    elif filing.payment_token:
        filing._status = Filing.Status.PENDING.value  # pylint: disable=protected-access

    else:
        filing._status = Filing.Status.DRAFT.value  # pylint: disable=protected-access
