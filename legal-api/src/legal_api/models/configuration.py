# Copyright © 2024 Province of British Columbia
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
"""This module holds data for configurations."""
from __future__ import annotations

from typing import List

from croniter import croniter
from sqlalchemy import event

from .db import db


class Configuration(db.Model):  # pylint: disable=too-many-instance-attributes
    """This class manages the configurations."""

    __tablename__ = 'configurations'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column('name', db.String(100), unique=True, nullable=False)
    val = db.Column('val', db.String(100), nullable=False)
    short_description = db.Column('short_description', db.String(150), nullable=True)
    full_description = db.Column('full_description', db.String(1000), nullable=True)

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    @property
    def json(self):
        """Return a dict of this object, with keys in JSON format."""
        configuration = {
            'name': self.name,
            'value': self.val,
            'shortDescription': self.short_description,
            'fullDescription': self.full_description
        }
        return configuration

    @classmethod
    def all(cls) -> List[Configuration]:
        """Return the configuration matching the id."""
        return cls.query.all()

    @classmethod
    def find_by_id(cls, config_id: int) -> Configuration:
        """Return the configuration matching the id."""
        configuration = None
        if config_id:
            configuration = cls.query.filter_by(id=config_id).one_or_none()
        return configuration

    @classmethod
    def find_by_name(cls, config_name: str) -> Configuration:
        """Return the configuration matching the name."""
        configuration = None
        if config_name:
            configuration = cls.query.filter_by(name=config_name).one_or_none()
        return configuration

    def validate_value(self):
        """Ensure the value is the correct type before insert or update."""
        # Define keys that should have specific value types
        int_names = {'NUM_DISSOLUTIONS_ALLOWED', 'MAX_DISSOLUTIONS_ALLOWED'}
        bool_names = {'DISSOLUTIONS_ON_HOLD'}
        cron_names = {'NEW_DISSOLUTIONS_SCHEDULE'}

        if self.name in int_names:
            try:
                int(self.val)
            except ValueError as exc:
                raise ValueError(f'Value for key {self.name} must be an integer') from exc
            num_dissolutions_allowed = self.val if self.name == 'NUM_DISSOLUTIONS_ALLOWED'\
                else Configuration.find_by_name('NUM_DISSOLUTIONS_ALLOWED').val
            max_dissolutions_allowed = self.val if self.name == 'MAX_DISSOLUTIONS_ALLOWED'\
                else Configuration.find_by_name('MAX_DISSOLUTIONS_ALLOWED').val
            if int(num_dissolutions_allowed) > int(max_dissolutions_allowed):
                raise ValueError('NUM_DISSOLUTIONS_ALLOWED cannot be greater than MAX_DISSOLUTIONS_ALLOWED.')
        elif self.name in bool_names:
            if self.val not in {'True', 'False'}:
                raise ValueError(f'Value for key {self.name} must be a boolean')
        elif self.name in cron_names:
            if not croniter.is_valid(self.val):
                raise ValueError(f'Value for key {self.name} must be a cron string')


# Listen to 'before_insert' and 'before_update' events
@event.listens_for(Configuration, 'before_insert')
@event.listens_for(Configuration, 'before_update')
def receive_before_insert(mapper, connection, target):
    """Validate the value before it gets inserted/updated."""
    target.validate_value()
