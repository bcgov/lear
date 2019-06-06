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
from datetime import datetime
from http import HTTPStatus

from sqlalchemy import event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property

from legal_api.exceptions import BusinessException
from legal_api.schemas import rsbc_schemas

from .db import db


class Filing(db.Model):
    """Immutable filing record.

    Manages the filing ledger for the associated business.
    """

    __tablename__ = 'filings'

    id = db.Column(db.Integer, primary_key=True)
    filing_date = db.Column('filing_date', db.DateTime(timezone=True), default=datetime.utcnow)
    _filing_type = db.Column('filing_type', db.String(30))
    _filing_json = db.Column('filing_json', JSONB)
    _payment_token = db.Column('payment_id', db.String(4096))

    # relationships
    transaction_id = db.Column('transaction_id', db.BigInteger,
                               db.ForeignKey('transaction.id'))
    business_id = db.Column('business_id', db.Integer,
                            db.ForeignKey('businesses.id'))
    submitter = db.Column('submitter_id', db.Integer,
                          db.ForeignKey('users.id'))

    # properties
    @hybrid_property
    def filing_type(self):
        """Property containing the main filing type, as extracted from the filing."""
        return self._filing_type

    @hybrid_property
    def payment_token(self):
        """Property containing the payment token, as extracted from the filing."""
        return self._payment_token

    @hybrid_property
    def filing_json(self):
        """Property containing the filings data."""
        return self._filing_json

    @filing_json.setter
    def filing_json(self, json_data: dict):
        """Property containing the filings data."""
        if self.payment_token:
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
        self._payment_token = json_data.get('filing').get('header').get('paymentToken')

        if self.payment_token:
            valid, err = rsbc_schemas.validate(json_data, 'filing')
            if not valid:
                self._filing_type = None
                self._payment_token = None
                raise BusinessException(
                    error=f'Invalid filing: {err}',
                    status_code=HTTPStatus.UNPROCESSABLE_ENTITY
                )
        self._filing_json = json_data

    # json serializer
    def json(self):
        """Return a json representation of this object."""
        d = {'filingDate': self.filing_date.isoformat(),
             'filingType': self.filing_type,
             'jsonSubmission': self.filing_json}
        if self.payment_token:
            d['paymentToken'] = self.payment_token
        if self.submitter:
            d['submitter'] = self.submitter
        return d

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


@event.listens_for(Filing, 'before_delete')
def block_filing_delete_listener_function(*arg):  # pylint: disable=unused-argument
    """Raise an error when a delete is attempted on a Filing."""
    raise BusinessException(
        error='Deletion not allowed.',
        status_code=HTTPStatus.FORBIDDEN
    )
