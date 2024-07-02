# Copyright © 2024 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the "License");
# you may not use this file except in compliance with the License.
# The template for the license can be found here
#    https://opensource.org/license/bsd-3-clause/
#
# Redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
"""Limited filings coverage

Just enough filings to mark as paid.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Optional

from sqlalchemy import text

from business_pay.database.db import db


@dataclass
class Filing(db.Model):
    """Minimal Filing class."""

    class Status(str, Enum):
        """Render an Enum of the Filing Statuses."""

        COMPLETED = "COMPLETED"
        CORRECTED = "CORRECTED"
        DRAFT = "DRAFT"
        EPOCH = "EPOCH"
        ERROR = "ERROR"
        PAID = "PAID"
        PENDING = "PENDING"
        PENDING_CORRECTION = "PENDING_CORRECTION"

    __tablename__ = "filings"
    __mapper_args__ = {
        "include_properties": [
            "id",
            "effective_date",
            "filing_type",
            "filing_sub_type",
            "payment_completion_date",
            "payment_status_code",
            "payment_token",
            "status",
            "payment_account",
        ]
    }
    id: int
    effective_date: Optional[datetime]
    filing_type: str
    filing_sub_type: Optional[str]
    payment_completion_date: Optional[datetime]
    payment_status_code: Optional[str]
    payment_token: Optional[str]
    status: Status
    payment_account: Optional[str]

    id = db.Column(db.Integer, primary_key=True)
    effective_date = db.Column(
        "effective_date", db.DateTime(timezone=True), default=datetime.now(timezone.utc)
    )
    filing_type = db.Column("filing_type", db.String(30))
    filing_sub_type = db.Column("filing_sub_type", db.String(30))
    payment_completion_date = db.Column(
        "payment_completion_date", db.DateTime(timezone=True)
    )
    payment_status_code = db.Column("payment_status_code", db.String(50))
    payment_token = db.Column("payment_id", db.String(4096))
    status = db.Column("status", db.String(20), default=Status.DRAFT)
    payment_account = db.Column("payment_account", db.String(30))

    @staticmethod
    def get_filing_by_payment_token(pay_token: str) -> Optional[Filing]:
        """Get the redacted filing based on the payment token."""
        try:
            stmt = text(
                """SELECT f.id, f.effective_date,
                        f.filing_type, f.filing_sub_type,
                        f.payment_completion_date, f.payment_status_code,
                        f.payment_id, f.status, f.payment_account
                        FROM filings f 
                        WHERE f.payment_id = :pay_token
            """
            )
            stmt = stmt.bindparams(pay_token=pay_token)

            filing = Filing.query.from_statement(stmt).one_or_none()

            return filing
        except Exception as e:
            print(e)
        return None

    def save(self):
        """Save the filing to the datbase."""
        db.session.add(self)
        db.session.commit()
