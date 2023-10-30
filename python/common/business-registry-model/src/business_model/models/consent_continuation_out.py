# Copyright © 2023 Province of British Columbia
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
"""This model holds data for consent continuation out."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import backref

from .db import db


class ConsentContinuationOut(db.Model):  # pylint: disable=too-few-public-methods
    """This class manages the consent continuation out for businesses."""

    __tablename__ = "consent_continuation_outs"

    id = db.Column("id", db.Integer, unique=True, primary_key=True)
    foreign_jurisdiction = db.Column("foreign_jurisdiction", db.String(10))
    foreign_jurisdiction_region = db.Column(
        "foreign_jurisdiction_region", db.String(10)
    )
    expiry_date = db.Column("expiry_date", db.DateTime(timezone=True))

    filing_id = db.Column("filing_id", db.Integer, db.ForeignKey("filings.id"))
    legal_entity_id = db.Column(
        "legal_entity_id", db.Integer, db.ForeignKey("legal_entities.id")
    )

    # relationships
    filing = db.relationship(
        "Filing", backref=backref("filing", uselist=False), foreign_keys=[filing_id]
    )

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    @staticmethod
    def get_active_cco(
        legal_entity_id,
        expiry_date,
        foreign_jurisdiction=None,
        foreign_jurisdiction_region=None,
    ) -> list[ConsentContinuationOut]:
        """Get a list of active consent_continuation_outs linked to the given legal_entity_id."""
        query = (
            db.session.query(ConsentContinuationOut)
            .filter(ConsentContinuationOut.legal_entity_id == legal_entity_id)
            .filter(ConsentContinuationOut.expiry_date >= expiry_date)
        )

        if foreign_jurisdiction:
            query = query.filter(
                ConsentContinuationOut.foreign_jurisdiction
                == foreign_jurisdiction.upper()
            )

        if foreign_jurisdiction_region:
            query = query.filter(
                ConsentContinuationOut.foreign_jurisdiction_region
                == foreign_jurisdiction_region.upper()
            )

        return query.all()

    @staticmethod
    def get_by_filing_id(filing_id) -> Optional[ConsentContinuationOut]:
        """Get consent continuation out by filing_id."""
        return (
            db.session.query(ConsentContinuationOut)
            .filter(ConsentContinuationOut.filing_id == filing_id)
            .one_or_none()
        )
