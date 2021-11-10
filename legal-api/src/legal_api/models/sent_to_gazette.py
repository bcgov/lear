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
"""This model manages the data store for sent to gazette colin event ids.

The sentToGazette class are held in this module.
"""

from .db import db


class sentToGazette(db.Model):  # pylint: disable=too-few-public-methods
    """This table maps sent_to_gazette to filing ids."""

    __tablename__ = 'sent_to_gazette'

    filing_id = db.Column('filing_id', db.Integer)  
    identifier = db.Column('identifier', db.String(10))  
    sent_to_gazette_date = db.Column('sent_to_gazette_date', db.DateTime(timezone=True), default=None)    

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()    