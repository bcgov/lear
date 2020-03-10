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
"""This module holds data for people related to a party role for a business."""
from .db import db


from .address import Address  # noqa: F401 pylint: disable=unused-import; needed by the SQLAlchemy relationship


class PartyMember(db.Model):  # pylint: disable=too-many-instance-attributes
    """This class manages all of the people with a party role."""

    __versioned__ = {}
    __tablename__ = 'party_members'

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column('first_name', db.String(1000), index=True)
    middle_initial = db.Column('middle_initial', db.String(1000), index=True)
    last_name = db.Column('last_name', db.String(1000))
    title = db.Column('title', db.String(1000))

    # parent keys
    address_id = db.Column('address_id', db.Integer, db.ForeignKey('addresses.id'))
    mailing_address_id = db.Column('mailing_address_id', db.Integer, db.ForeignKey('addresses.id'))

    # Relationships - Address
    delivery_address = db.relationship('Address', foreign_keys=[address_id])
    mailing_address = db.relationship('Address', foreign_keys=[mailing_address_id])

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    @property
    def json(self):
        """Return the party member as a json object."""
        member = {
            'officer': {'firstName': self.first_name, 'lastName': self.last_name}
        }
        if self.delivery_address:
            member_address = self.delivery_address.json
            if 'addressType' in member_address:
                del member_address['addressType']
            member['deliveryAddress'] = member_address
        if self.mailing_address:
            member_mailing_address = self.mailing_address.json
            if 'addressType' in member_mailing_address:
                del member_mailing_address['addressType']
            member['mailingAddress'] = member_mailing_address
        else:
            if self.delivery_address:
                member['mailingAddress'] = member['deliveryAddress']
        if self.title:
            member['title'] = self.title
        if self.middle_initial:
            member['officer']['middleInitial'] = self.middle_initial

        return member
