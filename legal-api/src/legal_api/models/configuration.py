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

from enum import Enum
from typing import List

from croniter import croniter
from sqlalchemy import event

from .db import db


EMAIL_PATTERN = (
    r'^(([^<>()[\]\\.,;:\s@"]+(\.[^<>()[\]\\.,;:\s@"]+)*)|'
    r'(".+"))@'
    r"((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}])|"
    r"(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$"
)


class Configuration(db.Model):  # pylint: disable=too-many-instance-attributes
    """This class manages the configurations."""

    __tablename__ = "configurations"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column("name", db.String(100), unique=True, nullable=False)
    val = db.Column("val", db.String(100), nullable=False)
    short_description = db.Column("short_description", db.String(150), nullable=True)
    full_description = db.Column("full_description", db.String(1000), nullable=True)

    class Names(Enum):
        """Render an Enum of the name of configuration."""

        NUM_DISSOLUTIONS_ALLOWED = "NUM_DISSOLUTIONS_ALLOWED"
        MAX_DISSOLUTIONS_ALLOWED = "MAX_DISSOLUTIONS_ALLOWED"
        DISSOLUTIONS_STAGE_1_SCHEDULE = "DISSOLUTIONS_STAGE_1_SCHEDULE"
        DISSOLUTIONS_STAGE_2_SCHEDULE = "DISSOLUTIONS_STAGE_2_SCHEDULE"
        DISSOLUTIONS_STAGE_3_SCHEDULE = "DISSOLUTIONS_STAGE_3_SCHEDULE"

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    @property
    def json(self):
        """Return a dict of this object, with keys in JSON format."""
        configuration = {
            "name": self.name,
            "value": self.val,
            "shortDescription": self.short_description,
            "fullDescription": self.full_description,
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

    @classmethod
    def find_by_names(cls, config_names: List[str]) -> List[Configuration]:
        """Return the configurations matching the names."""
        return cls.query.filter(cls.name.in_(config_names)).all()

    def validate_value(self):
        """Ensure the value is the correct type before insert or update."""
        # Define keys that should have specific value types
        Configuration.validate_configuration_value(self.name, self.val)

    @staticmethod
    def validate_configuration_value(name: str, val: str):
        """Ensure the value is the correct type before insert or update."""
        if not isinstance(val, str):
            raise ValueError("Value type must be string.")

        int_names = {
            Configuration.Names.NUM_DISSOLUTIONS_ALLOWED.value,
            Configuration.Names.MAX_DISSOLUTIONS_ALLOWED.value,
        }
        bool_names = {}  # generic code, keeping it in case we need to validate bool items in the future
        cron_names = {
            Configuration.Names.DISSOLUTIONS_STAGE_1_SCHEDULE.value,
            Configuration.Names.DISSOLUTIONS_STAGE_2_SCHEDULE.value,
            Configuration.Names.DISSOLUTIONS_STAGE_3_SCHEDULE.value,
        }

        if name in int_names:
            try:
                if int(val) < 0:
                    raise ValueError(f"Value for key {name} must be a positive integer")
            except ValueError as exc:
                raise ValueError(f"Value for key {name} must be a positive integer") from exc
        elif name in bool_names:
            if val not in {"True", "False"}:
                raise ValueError(f"Value for key {name} must be a boolean")
        elif name in cron_names:
            if not croniter.is_valid(val):
                raise ValueError(f"Value for key {name} must be a cron string")


# Listen to 'before_insert' and 'before_update' events
@event.listens_for(Configuration, "before_insert")
@event.listens_for(Configuration, "before_update")
def receive_before_insert(mapper, connection, target):
    """Validate the value before it gets inserted/updated."""
    target.validate_value()
