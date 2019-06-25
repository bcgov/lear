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
"""This model manages the data store for the highest event id that was updated by colin.

The ColinLastUpdate class and Schema are held in this module.
"""
from datetime import datetime

from .db import db


class ColinLastUpdate(db.Model):  # pylint: disable=too-few-public-methods
    """Creates a record of the last event loaded from colin."""

    __tablename__ = 'colin_last_update'

    id = db.Column(db.Integer, primary_key=True)
    last_update = db.Column('last_update', db.DateTime(timezone=True), default=datetime.utcnow)
    last_event_id = db.Column('last_event_id', db.Integer, unique=True, nullable=False)
