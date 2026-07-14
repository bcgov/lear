# Copyright (c) 2026, Province of British Columbia
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""This module contains the database model for a court order."""
from __future__ import annotations

from sql_versioning import Versioned

from business_model.models import db


class CourtOrder(db.Model, Versioned):
    __tablename__ = "court_orders"
    __versioned__ = {}
    __mapper_args__ = {
        "include_properties": [
          "id",
          "business_id",
          "effect_of_order",
          "file_number",
          "filing_id",
          "order_date",
          "order_details"
        ]
    }

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey("businesses.id"))
    filing_id = db.Column(db.Integer, db.ForeignKey("filings.id"), nullable=False)
    file_number = db.Column("file_number", db.String(20))
    effect_of_order = db.Column("effect_of_order", db.String(20))
    order_date = db.Column("order_date", db.DateTime(timezone=True), default=None)
    order_details = db.Column("order_details", db.String(2000))

    @property
    def json(self) -> dict:
        return {
            "id": self.id,
            "filingId": self.filing_id,
            "fileNumber": self.file_number,
            "orderDate": self.order_date,
            "effectOfOrder": self.effect_of_order,
            "orderDetails": self.order_details
        }
  
    def save(self):
        db.session.add(self)
        db.session.commit()

    @classmethod
    def get_by_id(cls, id) -> CourtOrder | None:
        """Get a court order by ID."""
        if not id:
          return None
        return cls.query.filter_by(id=id).one_or_none()

    @classmethod
    def get_by_filing_id(cls, filing_id) -> CourtOrder | None:
        """Get a court order by filing ID."""
        if not filing_id:
          return None
        return cls.query.filter_by(filing_id=filing_id).one_or_none()

    @classmethod
    def get_by_business_id(cls, business_id) -> list[CourtOrder]:
        """Get a court order by business ID."""
        if not business_id:
          return []
        return cls.query.filter_by(business_id=business_id).all()
