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
"""File processing rules and actions for the incorporation of a business."""
import copy

from business_model.models import Business, Filing

from business_filer.exceptions import QueueException
from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors.filing_components import aliases, business_info, filings, shares
from business_filer.filing_processors.filing_components.offices import update_offices
from business_filer.filing_processors.filing_components.parties import update_parties
from business_filer.services import Flags


def process(business: Business,  # noqa: PLR0912
            filing: dict,
            filing_rec: Filing,
            filing_meta: FilingMeta,
            flags: Flags):  # pylint: disable=too-many-branches
    """Process the incoming incorporation filing."""
    # Extract the filing information for incorporation
    incorp_filing = filing.get("filing", {}).get("incorporationApplication")
    filing_meta.incorporation_application = {}

    if not incorp_filing:
        raise QueueException(f"IA legal_filing:incorporationApplication missing from {filing_rec.id}")
    if business:
        raise QueueException(f"Business Already Exist: IA legal_filing:incorporationApplication {filing_rec.id}")

    business_info_obj = incorp_filing.get("nameRequest")

    if filing_rec.colin_event_ids:
        corp_num = filing["filing"]["business"]["identifier"]
    else:
        # Reserve the Corp Number for this entity
        corp_num = business_info.get_next_corp_num(business_info_obj["legalType"], flags)
        if not corp_num:
            raise QueueException(
                f"incorporationApplication {filing_rec.id} unable to get a business registration number.")

    # Initial insert of the business record
    business = Business()
    business = business_info.update_business_info(corp_num, business, business_info_obj, filing_rec)
    business.state = Business.State.ACTIVE

    if nr_number := business_info_obj.get("nrNumber", None):
        filing_meta.incorporation_application = {**filing_meta.incorporation_application,
                                                 "nrNumber": nr_number,
                                                    "legalName": business_info_obj.get("legalName", None)}

    if not business:
        raise QueueException(f"IA incorporationApplication {filing_rec.id}, Unable to create business.")

    if offices := incorp_filing["offices"]:
        update_offices(business, offices)

    if parties := incorp_filing.get("parties"):
        update_parties(business, parties, filing_rec)

    if share_structure := incorp_filing.get("shareStructure"):
        shares.update_share_structure(business, share_structure)

    if name_translations := incorp_filing.get("nameTranslations"):
        aliases.update_aliases(business, name_translations)

    if court_order := incorp_filing.get("courtOrder"):
        filings.update_filing_court_order(filing_rec, court_order)

    if not filing_rec.colin_event_ids:
        # Update the filing json with identifier and founding date.
        ia_json = copy.deepcopy(filing_rec.filing_json)
        if not ia_json["filing"].get("business"):
            ia_json["filing"]["business"] = {}
        ia_json["filing"]["business"]["identifier"] = business.identifier
        ia_json["filing"]["business"]["legalType"] = business.legal_type
        ia_json["filing"]["business"]["foundingDate"] = business.founding_date.isoformat()
        filing_rec._filing_json = ia_json  # pylint: disable=protected-access; bypass to update filing data
    return business, filing_rec, filing_meta
