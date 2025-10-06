# Copyright (c) 2025, Province of British Columbia
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
"""This module holds data for business account settings."""
from __future__ import annotations

from .db import db


class BusinessAccountSettings(db.Model):
    """This class manages the business account settings."""

    __tablename__ = 'business_account_settings'

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False)
    # NOTE: account_id should map to the Org.id in auth, businesses without any affiliations will have a null entry
    account_id = db.Column(db.Integer, nullable=True)
    business_account_constraint = db.UniqueConstraint(business_id, account_id)
    # Contact
    email = db.Column("email", db.String(100))
    phone = db.Column("phone", db.String(15))
    phone_extension = db.Column("phone_extension", db.String(10))
    # Notification preferences
    ar_reminder = db.Column("ar_reminder", db.Boolean, default=True, nullable=False)

    business = db.relationship("Business", foreign_keys=[business_id])

    @property
    def json(self):
        return {
            'accountId': self.account_id,
            'businessIdentifier': self.business.identifier,
            'email': self.email,
            'phone': self.phone,
            'phoneExtension': self.phone_extension,
            'arReminder': self.ar_reminder
        }
        
    def save(self):
        """Save and commit the object to the database."""
        db.session.add(self)
        db.session.commit()

    @classmethod
    def find_by_id(cls, business_account_settings_id: int) -> BusinessAccountSettings:
        """Return the business account settings by the id."""
        return cls.query.filter_by(id=business_account_settings_id).one_or_none()

    @classmethod
    def find_by_business_account(cls, business_id: int, account_id: int) -> BusinessAccountSettings:
        """Return the business account settings by the business id and the account id."""
        return cls.query.filter_by(business_id=business_id, account_id=account_id).one_or_none()

    @classmethod
    def find_all(cls, business_id: int = None, account_id: int = None) -> list[BusinessAccountSettings]:
        """Return all the business account settings by the business id and/or the account id."""
        query = cls.query
        if business_id:
            query = query.filter_by(business_id=business_id)
        if account_id:
            query = query.filter_by(account_id=account_id)
        return query.all()
    
    @staticmethod
    def create_or_update(business_id: int, account_id: int, data: dict[str, dict[str, str | bool]]) -> BusinessAccountSettings:
        """Create or update the BusinessAccountSettings record for the business and account id."""
        if not (settings := BusinessAccountSettings.find_by_business_account(business_id, account_id)):
            settings = BusinessAccountSettings(business_id=business_id, account_id=account_id)

        settings.email = data.get('email', settings.email)
        settings.phone = data.get('phone', settings.phone)
        settings.phone_extension = data.get('phoneExtension', settings.phone_extension)
        settings.ar_reminder = data.get('arReminder', settings.ar_reminder)
        settings.save()

        return settings
