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
    ADDRESS_TYPES = [MAILING, DELIVERY]

    __versioned__ = {}
    __tablename__ = 'addresses'

    id = db.Column(db.Integer, primary_key=True)
    address_type = db.Column('address_type', db.String(4096), index=True)
    street = db.Column('street', db.String(4096), index=True)
    street_additional = db.Column('street_additional', db.String(4096))
    city = db.Column('city', db.String(4096))
    region = db.Column('region', db.String(4096))
    country = db.Column('country', db.String(2))
    postal_code = db.Column('postal_code', db.String(10))
    delivery_instructions = db.Column('delivery_instructions', db.String(4096))

    # parent keys
    business_id = db.Column('business_id', db.Integer, db.ForeignKey('businesses.id'), index=True)

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
            'streetAddress': self.street,
            'streetAddressAdditional': self.street_additional,
            'addressType': self.address_type,
            'addressCity': self.city,
            'addressRegion': self.region,
            'addressCountry': self.country,
            'postalCode': self.postal_code,
            'deliveryInstructions': self.delivery_instructions
        }
