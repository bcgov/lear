# Copyright © 2024 Province of British Columbia
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
"""This module holds the data about jurisdiction."""
from __future__ import annotations

from sql_versioning import Versioned
from sqlalchemy import and_, or_

from .db import db
from .filing import Filing


class Jurisdiction(db.Model, Versioned):  # pylint: disable=too-many-instance-attributes
    """This class manages the jurisdiction."""

    __versioned__ = {}
    __tablename__ = "jurisdictions"

    id = db.Column(db.Integer, primary_key=True)
    country = db.Column("country", db.String(10))
    region = db.Column("region", db.String(10))
    identifier = db.Column("identifier", db.String(50))
    legal_name = db.Column("legal_name", db.String(1000))
    tax_id = db.Column("tax_id", db.String(15))
    incorporation_date = db.Column("incorporation_date", db.DateTime(timezone=True))
    expro_identifier = db.Column("expro_identifier", db.String(10))
    expro_legal_name = db.Column("expro_legal_name", db.String(1000))

    # parent keys
    business_id = db.Column("business_id", db.Integer, db.ForeignKey("businesses.id"), nullable=False, index=True)
    filing_id = db.Column("filing_id", db.Integer, db.ForeignKey("filings.id"), nullable=False, index=True)

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    @classmethod
    def find_by_id(cls, jurisdiction_id) -> Jurisdiction:
        """Return jurisdiction by the id."""
        jurisdiction = None
        if jurisdiction_id:
            jurisdiction = cls.query.filter_by(id=jurisdiction_id).one_or_none()
        return jurisdiction

    @classmethod
    def get_continuation_in_jurisdiction(cls, business_id) -> Jurisdiction:
        """Return continuation in jurisdiction by the business id."""
        jurisdiction = None
        if business_id:
            # pylint: disable=protected-access
            jurisdiction = (db.session.query(Jurisdiction).join(Filing).
                            filter(Jurisdiction.business_id == business_id).
                            filter(
                                or_(
                                    Filing._filing_type == "continuationIn",
                                    and_(
                                        Filing._filing_type == "conversion",
                                        Filing._meta_data.op("->")("conversion").
                                        op("->>")("convFilingType") == "continuationIn"
                                    )
                                )
                            ).
                            one_or_none())
        return jurisdiction
