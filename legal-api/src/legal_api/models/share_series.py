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
"""This module holds data for share series."""

from http import HTTPStatus

from sql_versioning import Versioned
from sqlalchemy import event

from legal_api.exceptions import BusinessException

from .db import db


class ShareSeries(db.Model, Versioned):  # pylint: disable=too-many-instance-attributes
    """This class manages the share series."""

    __versioned__ = {}
    __tablename__ = "share_series"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column("name", db.String(1000), index=True)
    priority = db.Column("priority", db.Integer, nullable=True)
    max_share_flag = db.Column("max_share_flag", db.Boolean, unique=False, default=False)
    max_shares = db.Column("max_shares", db.Numeric(20), nullable=True)
    special_rights_flag = db.Column("special_rights_flag", db.Boolean, unique=False, default=False)

    # parent keys
    share_class_id = db.Column("share_class_id", db.Integer, db.ForeignKey("share_classes.id"))

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    @property
    def json(self):
        """Return a dict of this object, with keys in JSON format."""
        share_series = {
            "id": self.id,
            "name": self.name,
            "priority": self.priority,
            "hasMaximumShares": self.max_share_flag,
            "maxNumberOfShares": int(self.max_shares) if self.max_shares else None,
            "hasRightsOrRestrictions": self.special_rights_flag
        }
        return share_series


@event.listens_for(ShareSeries, "before_insert")
@event.listens_for(ShareSeries, "before_update")
def receive_before_change(mapper, connection, target):  # pylint: disable=unused-argument; SQLAlchemy callback signature
    """Run checks/updates before adding/changing the share series."""
    share_series = target

    # skip this status updater if the flag is set
    # Scenario: used for COLIN corp data migration as there is data that do not pass the following checks
    if hasattr(share_series, "skip_share_series_listener") and share_series.skip_share_series_listener:
        return

    if share_series.max_share_flag:
        if not share_series.max_shares:
            raise BusinessException(
                error=f"The share series {share_series.name} must specify maximum number of share.",
                status_code=HTTPStatus.BAD_REQUEST
            )
        if (
            share_series.share_class.max_share_flag and
            int(share_series.max_shares) > int(share_series.share_class.max_shares)
        ):
            raise BusinessException(
                error=f"The max share quantity of {share_series.name} must be <= that of share class quantity.",
                status_code=HTTPStatus.BAD_REQUEST
            )
    else:
        share_series.max_shares = None
