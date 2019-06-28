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
from datetime import datetime
from http import HTTPStatus
from typing import List

from sqlalchemy import event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import attributes, backref

from legal_api.exceptions import BusinessException
from legal_api.schemas import rsbc_schemas

from .db import db


class Filing(db.Model):  # pylint: disable=too-many-instance-attributes; allowing the model to be deep.
    """Immutable filing record.

    Manages the filing ledger for the associated business.
    """

    FILINGS = {'annualReport': {'name': 'annualReport', 'title': 'Annual Report Filing', 'code': 'OTANN'},
               'changeOfAddress': {'name': 'changeOfAddress', 'title': 'Change of Address Filing', 'code': 'OTADD'},
               }

    __tablename__ = 'filings'

    id = db.Column(db.Integer, primary_key=True)
    filing_date = db.Column('filing_date', db.DateTime(timezone=True), default=datetime.utcnow)
    _filing_type = db.Column('filing_type', db.String(30))
    _filing_json = db.Column('filing_json', JSONB)
    _payment_token = db.Column('payment_id', db.String(4096))
    colin_event_id = db.Column('colin_event_id', db.Integer)

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
    @hybrid_property
    def filing_type(self):
        """Property containing the main filing type, as extracted from the filing."""
        return self._filing_type

    @hybrid_property
    def payment_token(self):
        """Property containing the payment token, as extracted from the filing."""
        return self._payment_token

    @payment_token.setter
    def payment_token(self, token: int):
        old_payment_token = attributes.get_history(self, '_payment_token')
        if self._payment_token \
                and (old_payment_token.deleted or old_payment_token.unchanged):
            raise BusinessException(
                error='Filings cannot be changed after they are paid for and stored.',
                status_code=HTTPStatus.FORBIDDEN
            )
        self._payment_token = token

    @hybrid_property
    def filing_json(self):
        """Property containing the filings data."""
        return self._filing_json

    @filing_json.setter
    def filing_json(self, json_data: dict):
        """Property containing the filings data."""
        old_payment_token = attributes.get_history(self, '_payment_token')
        if self._payment_token \
                and (old_payment_token.deleted or old_payment_token.unchanged):
            raise BusinessException(
                error='Filings cannot be changed after they are paid for and stored.',
                status_code=HTTPStatus.FORBIDDEN
            )

        try:
            self._filing_type = json_data.get('filing').get('header').get('name')
            if not self._filing_type:
                raise Exception
        except Exception:
            raise BusinessException(
                error='No filings found.',
                status_code=HTTPStatus.UNPROCESSABLE_ENTITY
            )

        if self.payment_token:
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
        self._filing_json = json_data
        try:
            self.colin_event_id = int(json_data.get('filing').get('eventId'))
        except (AttributeError, TypeError):
            # eventId is from colin_api (will not be set until added in colin db)
            # todo: could make the post call for filing with json_data to colin api here and then set the colin_event_Id
            pass

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

            if self.payment_token:
                json_submission['filing']['header']['paymentToken'] = self.payment_token
            if self.submitter_id:
                json_submission['filing']['header']['submitter'] = self.filing_submitter.username
            return json_submission
        except Exception:  # noqa: B901, E722
            raise KeyError

    def save(self):
        """Save and commit immediately."""
        db.session.add(self)
        db.session.commit()

    def save_to_session(self):
        """Save toThe session, do not commit immediately."""
        db.session.add(self)

    @staticmethod
    def delete():
        """Raise an error if the filing is deleted."""
        raise BusinessException(
            error='Deletion not allowed.',
            status_code=HTTPStatus.FORBIDDEN
        )

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
def block_filing_delete_listener_function(*arg):  # pylint: disable=unused-argument
    """Raise an error when a delete is attempted on a Filing."""
    raise BusinessException(
        error='Deletion not allowed.',
        status_code=HTTPStatus.FORBIDDEN
    )
