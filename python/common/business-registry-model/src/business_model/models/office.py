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
# limitations under the License.
"""Meta information about the service.

Currently this only provides API versioning information
"""
from sql_versioning import Versioned

from .db import db


class Office(Versioned, db.Model):  # pylint: disable=too-few-public-methods
    """This is the object mapping for the Office entity.

    An office is associated with one business, and 0...n addresses
    """

    __tablename__ = "offices"
    __mapper_args__ = {
        "include_properties": [
            "id",
            "legal_entity_id",
            "change_filing_id",
            "deactivated_date",
            "office_type",
            "alternate_name_id",
        ]
    }

    id = db.Column(db.Integer, primary_key=True)
    office_type = db.Column("office_type", db.String(75), db.ForeignKey("office_types.identifier"))
    deactivated_date = db.Column("deactivated_date", db.DateTime(timezone=True), default=None)

    # Parent Keys
    change_filing_id = db.Column("change_filing_id", db.Integer, db.ForeignKey("filings.id"), index=True)
    legal_entity_id = db.Column("legal_entity_id", db.Integer, db.ForeignKey("legal_entities.id"), index=True)
    alternate_name_id = db.Column("alternate_name_id", db.Integer, db.ForeignKey("alternate_names.id"), nullable=True)

    # Relationships
    addresses = db.relationship("Address", lazy="dynamic", cascade="all, delete, delete-orphan")


class OfficeType(db.Model):  # pylint: disable=too-few-public-methods
    """Define the Office Types available for Legal Entities."""

    __tablename__ = "office_types"

    identifier = db.Column(db.String(50), primary_key=True)
    description = db.Column(db.String(50))

    # Office Types Constants
    REGISTERED = "registeredOffice"
    RECORDS = "recordsOffice"
    CUSTODIAL = "custodialOffice"
    BUSINESS = "businessOffice"
