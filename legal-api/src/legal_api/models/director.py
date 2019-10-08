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
from datetime import datetime

from sqlalchemy import Date, cast, or_

from .db import db


class Director(db.Model):  # pylint: disable=too-many-instance-attributes
    """This class manages all of the business directors."""

    __versioned__ = {}
    __tablename__ = 'directors'

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column('first_name', db.String(1000), index=True)
    middle_initial = db.Column('middle_initial', db.String(1000), index=True)
    last_name = db.Column('last_name', db.String(1000))
    title = db.Column('title', db.String(1000))
    appointment_date = db.Column('appointment_date', db.DateTime(timezone=True))
    cessation_date = db.Column('cessation_date', db.DateTime(timezone=True))

    # parent keys
    business_id = db.Column('business_id', db.Integer, db.ForeignKey('businesses.id'), index=True)
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
        """Return the director as a json object."""
        d = {
            'officer': {'firstName': self.first_name, 'lastName': self.last_name},
            'appointmentDate': datetime.date(self.appointment_date).isoformat(),
            'cessationDate': datetime.date(self.cessation_date).isoformat() if self.cessation_date else None
        }
        if self.delivery_address:
            director_address = self.delivery_address.json
            if 'addressType' in director_address:
                del director_address['addressType']
            d['deliveryAddress'] = director_address
        if self.mailing_address:
            director_mailing_address = self.mailing_address.json
            if 'addressType' in director_mailing_address:
                del director_mailing_address['addressType']
            d['mailingAddress'] = director_mailing_address
        else:
            if self.delivery_address:
                d['mailingAddress'] = d['deliveryAddress']
        if self.title:
            d['title'] = self.title
        if self.middle_initial:
            d['officer']['middleInitial'] = self.middle_initial

        return d

    @staticmethod
    def get_active_directors(business_id: int, end_date: datetime):
        """Return the active directors as of given date."""
        directors = db.session.query(Director). \
            filter(Director.business_id == business_id). \
            filter(or_(Director.cessation_date.is_(None), cast(Director.cessation_date, Date) > end_date)). \
            all()
        return directors
