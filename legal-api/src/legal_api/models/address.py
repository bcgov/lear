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
import pycountry

from .db import db


class Address(db.Model):  # pylint: disable=too-many-instance-attributes
    """This class manages all of the business addresses.

    Every business is required to have 2 addresses on record, DELIVERY and MAILING.
    These are identified by the constants:
    - Mailing
    - Delivery
    and are in the ADDRESS_TYPES List for ease of checking.
    """

    MAILING = 'mailing'
    DELIVERY = 'delivery'
    FURNISHING = 'furnishing'
    ADDRESS_TYPES = [MAILING, DELIVERY, FURNISHING]
    JSON_MAILING = 'mailingAddress'
    JSON_DELIVERY = 'deliveryAddress'
    JSON_ADDRESS_TYPES = [JSON_MAILING, JSON_DELIVERY]

    __versioned__ = {}
    __tablename__ = 'addresses'

    id = db.Column(db.Integer, primary_key=True)
    address_type = db.Column('address_type', db.String(4096), index=True)
    street = db.Column('street', db.String(4096), index=True)
    street_additional = db.Column('street_additional', db.String(4096))
    city = db.Column('city', db.String(4096))
    region = db.Column('region', db.String(4096))
    country = db.Column('country', db.String(2))
    postal_code = db.Column('postal_code', db.String(15))
    delivery_instructions = db.Column('delivery_instructions', db.String(4096))

    # parent keys
    business_id = db.Column('business_id', db.Integer, db.ForeignKey('businesses.id'), index=True)
    furnishings_id = db.Column('furnishings_id', db.Integer, db.ForeignKey('furnishings.id'), nullable=True)
    office_id = db.Column('office_id', db.Integer, db.ForeignKey('offices.id', ondelete='CASCADE'), nullable=True)
    # Relationships - Users
    # business_mailing_address = db.relationship('Business',
    #                                            backref=backref('business_mailing_address', uselist=False),
    #                                            foreign_keys=[business_id])

    def save(self):
        """Render a Business to the local cache."""
        db.session.add(self)
        db.session.commit()

    @property
    def json(self):
        """Return a dict of this object, with keys in JSON format."""
        return {
            'id': self.id,
            'streetAddress': self.street,
            'streetAddressAdditional': self.street_additional,
            'addressType': self.address_type,
            'addressCity': self.city,
            'addressRegion': self.region,
            'addressCountry': self.country,
            'postalCode': self.postal_code,
            'deliveryInstructions': self.delivery_instructions
        }

    @staticmethod
    def create_address(new_info: dict):
        """Create an address object from dict/json."""
        address = Address()

        address.street = new_info.get('streetAddress')
        address.street_additional = new_info.get('streetAddressAdditional')
        address.city = new_info.get('addressCity')
        address.region = new_info.get('addressRegion')
        address.country = pycountry.countries.search_fuzzy(new_info.get('addressCountry'))[0].alpha_2
        address.postal_code = new_info.get('postalCode')
        address.delivery_instructions = new_info.get('deliveryInstructions')

        return address

    @classmethod
    def find_by_id(cls, internal_id: int = None):
        """Return the address by the internal id."""
        address = None
        if internal_id:
            address = cls.query.filter_by(id=internal_id).one_or_none()
        return address

    @classmethod
    def find_by(cls,
                business_id: int = None,
                furnishings_id: int = None,
                office_id: int = None) -> dict:
        """Return the address matching."""
        query = db.session.query(Address)
        addresses = []

        if business_id:
            query = query.filter(Address.business_id == business_id)

        if furnishings_id:
            query = query.filter(Address.furnishings_id == furnishings_id)

        if office_id:
            query = query.filter(Address.office_id == office_id)

        addresses = query.order_by(Address.id).all()
        return addresses
