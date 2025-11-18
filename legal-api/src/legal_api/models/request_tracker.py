# Copyright © 2022 Province of British Columbia
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
"""This module holds data for request tracker."""
from __future__ import annotations

from enum import auto
from typing import List

from legal_api.utils.base import BaseEnum
from legal_api.utils.datetime import datetime
from legal_api.utils.legislation_datetime import LegislationDatetime

from .db import db


class RequestTracker(db.Model):  # pylint: disable=too-many-instance-attributes
    """This class manages the request tracker."""

    class ServiceName(BaseEnum):
        """Render an Enum of the service name."""

        BN_HUB = auto()

    class RequestType(BaseEnum):
        """Render an Enum of the service name."""

        INFORM_CRA = auto()
        GET_BN = auto()
        CHANGE_DELIVERY_ADDRESS = auto()
        CHANGE_MAILING_ADDRESS = auto()
        CHANGE_NAME = auto()
        CHANGE_STATUS = auto()
        CHANGE_PARTY = auto()

    __tablename__ = "request_tracker"

    id = db.Column(db.Integer, primary_key=True)
    request_type = db.Column("request_type", db.Enum(RequestType), nullable=False)
    is_processed = db.Column("is_processed", db.Boolean, default=False)
    request_object = db.Column(db.Text)
    response_object = db.Column(db.Text)
    retry_number = db.Column("retry_number", db.Integer, default=0, nullable=False)
    service_name = db.Column("service_name", db.Enum(ServiceName), nullable=False)
    creation_date = db.Column("creation_date", db.DateTime(timezone=True), default=datetime.utcnow)
    last_modified = db.Column("last_modified", db.DateTime(timezone=True), default=datetime.utcnow)
    is_admin = db.Column("is_admin", db.Boolean, default=False)
    message_id = db.Column("message_id", db.String(60))

    # parent keys
    business_id = db.Column("business_id", db.Integer, db.ForeignKey("businesses.id"), index=True)
    filing_id = db.Column("filing_id", db.Integer, db.ForeignKey("filings.id"), index=True)

    @property
    def json(self) -> dict:
        """Return the request tracker as a json object."""
        return {
            "id": self.id,
            "requestType": self.request_type.name,
            "isProcessed": self.is_processed,
            "serviceName": self.service_name.name,
            "isAdmin": self.is_admin,
            "creationDate": LegislationDatetime.as_legislation_timezone(self.creation_date).isoformat()
        }

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    @classmethod
    def find_by_id(cls, request_tracker_id: int) -> RequestTracker:
        """Return the request tracker matching the id."""
        request_tracker = None
        if request_tracker_id:
            request_tracker = cls.query.filter_by(id=request_tracker_id).one_or_none()
        return request_tracker

    @classmethod
    def find_by(cls,  # pylint: disable=too-many-arguments
                business_id: int,
                service_name: ServiceName,
                request_type: RequestType = None,
                filing_id: int = None,
                is_admin: bool = None,
                message_id: str = None) -> List[RequestTracker]:
        """Return the request tracker matching."""
        query = db.session.query(RequestTracker). \
            filter(RequestTracker.business_id == business_id). \
            filter(RequestTracker.service_name == service_name)

        if request_type:
            query = query.filter(RequestTracker.request_type == request_type)

        if filing_id:
            query = query.filter(RequestTracker.filing_id == filing_id)

        if is_admin:
            query = query.filter(RequestTracker.is_admin == is_admin)

        if message_id:
            query = query.filter(RequestTracker.message_id == message_id)

        request_trackers = query.order_by(RequestTracker.id).all()
        return request_trackers
