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
"""File processing rules and actions for the registration of a business."""
import copy

from business_model.models import Business, Filing

from business_filer.common.legislation_datetime import LegislationDatetime
from business_filer.exceptions import QueueException
from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors.filing_components import business_info, filings
from business_filer.filing_processors.filing_components.offices import update_offices
from business_filer.filing_processors.filing_components.parties import update_parties


def process(business: Business,  # pylint: disable=too-many-branches
            filing: dict,
            filing_rec: Filing,
            filing_meta: FilingMeta):  # pylint: disable=too-many-branches
    """Process the incoming registration filing."""
    # Extract the filing information for registration
    registration_filing = filing.get("filing", {}).get("registration")
    filing_meta.registration = {}

    if not registration_filing:
        raise QueueException(f"Registration legal_filing:registration missing from {filing_rec.id}")
    if business:
        raise QueueException(f"Business Already Exist: Registration legal_filing:registration {filing_rec.id}")

    business_info_obj = registration_filing.get("nameRequest")

    # Reserve the Corp Number for this entity
    corp_num = business_info.get_next_corp_num("FM")
    if not corp_num:
        raise QueueException(
            f"registration {filing_rec.id} unable to get a business registration number.")

    # Initial insert of the business record
    business = Business()
    business = business_info.update_business_info(corp_num, business, business_info_obj, filing_rec)
    business.start_date = \
        LegislationDatetime.as_utc_timezone_from_legislation_date_str(registration_filing.get("startDate"))

    business_obj = registration_filing.get("business", {})
    if (naics := business_obj.get("naics")) and naics.get("naicsCode"):
        business_info.update_naics_info(business, naics)
    business.tax_id = business_obj.get("taxId", None)
    business.state = Business.State.ACTIVE

    if nr_number := business_info_obj.get("nrNumber", None):
        filing_meta.registration = {**filing_meta.registration,
                                    "nrNumber": nr_number,
                                       "legalName": business_info_obj.get("legalName", None)}

    if not business:
        raise QueueException(f"Registration {filing_rec.id}, Unable to create business.")

    if offices := registration_filing["offices"]:
        update_offices(business, offices)

    if parties := registration_filing.get("parties"):
        update_parties(business, parties, filing_rec)

    # update court order, if any is present
    if court_order := registration_filing.get("courtOrder"):
        filings.update_filing_court_order(filing_rec, court_order)

    # Update the filing json with identifier and founding date.
    registration_json = copy.deepcopy(filing_rec.filing_json)
    registration_json["filing"]["business"] = {}
    registration_json["filing"]["business"]["identifier"] = business.identifier
    registration_json["filing"]["registration"]["business"]["identifier"] = business.identifier
    registration_json["filing"]["business"]["legalType"] = business.legal_type
    registration_json["filing"]["business"]["foundingDate"] = business.founding_date.isoformat()
    filing_rec._filing_json = registration_json  # pylint: disable=protected-access; bypass to update filing data

    return business, filing_rec, filing_meta
