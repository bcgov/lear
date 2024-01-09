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
"""This module holds data for colin entities."""
from __future__ import annotations

from sql_versioning import Versioned

from .db import db


class ColinEntity(Versioned, db.Model):
    """This class manages the colin entities."""

    __tablename__ = "colin_entities"
    __mapper_args__ = {
        "include_properties": [
            "id",
            "change_filing_id",
            "delivery_address_id",
            "email",
            "identifier",
            "organization_name",
            "mailing_address_id",
        ]
    }

    id = db.Column(db.Integer, primary_key=True)
    organization_name = db.Column("organization_name", db.String(150), index=True)
    identifier = db.Column("identifier", db.String(10), index=True)
    email = db.Column("email", db.String(254), index=True)

    # parent keys
    change_filing_id = db.Column("change_filing_id", db.Integer, db.ForeignKey("filings.id"), index=True)
    delivery_address_id = db.Column("delivery_address_id", db.Integer, db.ForeignKey("addresses.id"))
    mailing_address_id = db.Column("mailing_address_id", db.Integer, db.ForeignKey("addresses.id"))

    # relationships
    delivery_address = db.relationship("Address", foreign_keys=[delivery_address_id], cascade="all, delete")
    mailing_address = db.relationship("Address", foreign_keys=[mailing_address_id], cascade="all, delete")

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    @property
    def name(self) -> str:
        """Return the full name of the party for comparison."""
        return self.organization_name.strip().upper()

    @property
    def json(self) -> dict:
        """Return the colin entity as a json object."""
        member = {"officer": {"id": self.id, "organizationName": self.organization_name, "identifier": self.identifier}}
        member["officer"]["email"] = self.email
        if self.delivery_address:
            member_address = self.delivery_address.json
            if "addressType" in member_address:
                del member_address["addressType"]
            member["deliveryAddress"] = member_address
        if self.mailing_address:
            member_mailing_address = self.mailing_address.json
            if "addressType" in member_mailing_address:
                del member_mailing_address["addressType"]
            member["mailingAddress"] = member_mailing_address
        else:
            if self.delivery_address:
                member["mailingAddress"] = member["deliveryAddress"]

        return member
