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
from enum import auto
from ..utils.base import BaseEnum


class AmalgamatingBusiness(db.Model):  # pylint: disable=too-many-instance-attributes
    """
    This class manages the amalgamating businesses.

    """
    
    # pylint: disable=invalid-name
    class Role(BaseEnum):
        
        """Enum for the Role Values."""

        AMALGAMATING = auto()
        
        HOLDING = auto()
   
    __versioned__ = {}
    
    __tablename__ = 'amalgamating_business'

    id = db.Column(db.Integer, primary_key=True)
    
    role = db.Column('role', db.Enum(Role), nullable=False)
    
    foreign_jurisdiction = db.Column('foreign_jurisdiction', db.String(10))
    
    foreign_name = db.Column('foreign_name', db.String(100))
    
    foreign_corp_num = db.Column('foreign_corp_num', db.String(50))
    
    # parent keys
    business_id = db.Column('business_id', db.Integer, db.ForeignKey('businesses.id'), index=True)
    
    amalgamation_id = db.Column('amalgamation_id', db.Integer, db.ForeignKey('amalgamation.id', ondelete='CASCADE'), nullable=True)
    
    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()
   