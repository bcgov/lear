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
"""File processing rules and actions for the restoration on filing."""

from contextlib import suppress

import dpath
from business_model.models import Business, Filing, PartyRole

from business_filer.common.datetime import datetime, timezone
from business_filer.common.legislation_datetime import LegislationDatetime
from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors.filing_components import business_info, filings
from business_filer.filing_processors.filing_components.aliases import update_aliases
from business_filer.filing_processors.filing_components.offices import update_offices
from business_filer.filing_processors.filing_components.parties import update_parties


def process(business: Business, filing: dict, filing_rec: Filing, filing_meta: FilingMeta):
    """Process restoration filing."""
    restoration_filing = filing.get("restoration")
    filing_meta.restoration = {}

    from_legal_name = business.legal_name

    if name_request_json := restoration_filing.get("nameRequest"):
        business_info.set_legal_name(business.identifier, business, name_request_json)
        if nr_number := name_request_json.get("nrNumber", None):
            filing_meta.restoration = {
                **filing_meta.restoration,
                "nrNumber": nr_number
            }

    filing_meta.restoration = {
        **filing_meta.restoration,
        "fromLegalName": from_legal_name,
        "toLegalName": business.legal_name
        # if restoration is from a numbered to numbered, fromLegalName and toLegalName will be same
        # adding this intentionally for now to refer in ledger (filing-ui)
    }

    if expiry := restoration_filing.get("expiry"):  # limitedRestoration, limitedRestorationExtension
        business.restoration_expiry_date = LegislationDatetime.as_utc_timezone_from_legislation_date_str(expiry)
        filing_meta.restoration = {
            **filing_meta.restoration,
            "expiry": expiry
        }
    else:  # fullRestoration, limitedRestorationToFull
        business.restoration_expiry_date = None

    business.state = Business.State.ACTIVE
    business.dissolution_date = None
    business.state_filing_id = filing_rec.id

    if name_translations := restoration_filing.get("nameTranslations"):
        update_aliases(business, name_translations)

    update_offices(business, restoration_filing["offices"])

    cease_custodian(business)
    update_parties(business,
                   restoration_filing["parties"],
                   filing_rec,
                   False)

    filing_rec.approval_type = restoration_filing.get("approvalType")
    if filing_rec.approval_type == "courtOrder":
        with suppress(IndexError, KeyError, TypeError):
            court_order_json = dpath.get(restoration_filing, "/courtOrder")
            filings.update_filing_court_order(filing_rec, court_order_json)
    elif filing_rec.approval_type == "registrar":
        application_date = restoration_filing.get("applicationDate")
        notice_date = restoration_filing.get("noticeDate")
        if application_date and notice_date:
            filing_rec.application_date = \
                LegislationDatetime.as_utc_timezone_from_legislation_date_str(application_date)
            filing_rec.notice_date = LegislationDatetime.as_utc_timezone_from_legislation_date_str(notice_date)


def cease_custodian(business: Business):
    """Cease custodian if exist."""
    end_date_time = datetime.now(timezone.utc)
    custodian_party_roles = PartyRole.get_party_roles(business.id,
                                                      end_date_time.date(),
                                                      PartyRole.RoleTypes.CUSTODIAN.value)
    for party_role in custodian_party_roles:
        party_role.cessation_date = end_date_time
        business.party_roles.append(party_role)
