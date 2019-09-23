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


class Office (db.Model):
    """This is the object mapping for the Office entity.

    An office is associated with one business, and 0...n addresses
    """

    __versioned__ = {}
    __tablename__ = 'offices'

    id = db.Column(db.Integer, primary_key=True)
    office_type = db.Column('office_type', db.String(75))
    business_id = db.Column('business_id', db.Integer, db.ForeignKey('businesses.id'), index=True)
    addresses = db.relationship('Address')
    deactivated_date = db.Column('deactivated_date', db.DateTime(timezone=True), default=None)

    # relationships
    business_id = db.Column('business_id', db.Integer, db.ForeignKey('businesses.id'), index=True)
