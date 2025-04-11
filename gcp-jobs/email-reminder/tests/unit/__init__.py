# Copyright © 2025 Province of British Columbia
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
"""The Test-Suite used to ensure that the Email Reminder Job is working correctly."""
import base64
import uuid
from datetime import UTC, datetime

from freezegun import freeze_time

from business_model.models import Address, Batch, BatchProcessing, Business, Filing, Furnishing, db
from business_model.models.colin_event_id import ColinEventId
from business_model.models.db import VersioningProxy

EPOCH_DATETIME = datetime.utcfromtimestamp(0).replace(tzinfo=UTC)
FROZEN_DATETIME = datetime(2001, 8, 5, 7, 7, 58, 272362).replace(tzinfo=UTC)


def factory_business(identifier,
                     founding_date=EPOCH_DATETIME,
                     last_ar_date=None,
                     entity_type=Business.LegalTypes.COMP.value,
                     state=Business.State.ACTIVE,
                     admin_freeze=False,
                     no_dissolution=False,
                     last_ar_reminder_year=None,
                     restoration_expiry_date=None):
    """Create a business."""
    last_ar_year = None
    if last_ar_date:
        last_ar_year = last_ar_date.year
    business = Business(legal_name=f"legal_name-{identifier}",
                        founding_date=founding_date,
                        last_ar_date=last_ar_date,
                        last_ar_year=last_ar_year,
                        identifier=identifier,
                        legal_type=entity_type,
                        state=state,
                        admin_freeze=admin_freeze,
                        no_dissolution=no_dissolution,
                        last_ar_reminder_year=last_ar_reminder_year,
                        restoration_expiry_date=restoration_expiry_date)
    business.save()
    return business


def factory_completed_filing(business,
                             data_dict,
                             filing_date=FROZEN_DATETIME,
                             payment_token=None,
                             colin_id=None,
                             filing_type=None,
                             filing_sub_type=None):
    """Create a completed filing."""
    if not payment_token:
        payment_token = str(base64.urlsafe_b64encode(uuid.uuid4().bytes)).replace("=", "")

    with freeze_time(filing_date):

        filing = Filing()
        filing.business_id = business.id
        filing.filing_date = filing_date
        filing.filing_json = data_dict
        if filing_type:
            filing._filing_type = filing_type
        if filing_sub_type:
            filing._filing_sub_type = filing_sub_type
        filing.save()

        transaction_id = VersioningProxy.get_transaction_id(db.session())
        filing.transaction_id = transaction_id
        filing.payment_token = payment_token
        filing.effective_date = filing_date
        filing.payment_completion_date = filing_date
        if colin_id:
            colin_event = ColinEventId()
            colin_event.colin_event_id = colin_id
            colin_event.filing_id = filing.id
            colin_event.save()
        filing.save()
    return filing
