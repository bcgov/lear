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
"""File processing rules and actions for the correction filing."""
import copy
import datetime
from contextlib import suppress

import dpath
from business_model.models import Address, Business, Filing, Party, PartyRole

from business_filer.common.legislation_datetime import LegislationDatetime
from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors.filing_components import (
    aliases,
    business_info,
    create_party,
    create_role,
    filings,
    resolutions,
    rules_and_memorandum,
    shares,
    update_address,
)

CEASE_ROLE_MAPPING = {
    **dict.fromkeys(Business.CORPS, PartyRole.RoleTypes.DIRECTOR.value),
    Business.LegalTypes.COOP.value: PartyRole.RoleTypes.DIRECTOR.value,
    Business.LegalTypes.PARTNERSHIP.value: PartyRole.RoleTypes.PARTNER.value,
    Business.LegalTypes.SOLE_PROP.value: PartyRole.RoleTypes.PROPRIETOR.value,
}


def correct_business_data(business: Business,  # noqa: PLR0915
                          correction_filing_rec: Filing,
                          correction_filing: dict,
                          filing_meta: FilingMeta):
    """Render the correction filing onto the business model objects."""
    # Update business legalName if present
    with suppress(IndexError, KeyError, TypeError):
        name_request_json = dpath.get(correction_filing, "/correction/nameRequest")
        from_legal_name = business.legal_name
        business_info.set_legal_name(business.identifier, business, name_request_json)
        if from_legal_name != business.legal_name:
            filing_meta.correction = {**filing_meta.correction,
                                      "fromLegalName": from_legal_name,
                                         "toLegalName": business.legal_name}

    # Update cooperativeAssociationType if present
    with suppress(IndexError, KeyError, TypeError):
        coop_association_type = dpath.get(correction_filing, "/correction/cooperativeAssociationType")
        from_association_type = business.association_type
        if coop_association_type:
            business_info.set_association_type(business, coop_association_type)
            filing_meta.correction = {**filing_meta.correction,
                                      "fromCooperativeAssociationType": from_association_type,
                                         "toCooperativeAssociationType": business.association_type}

    # Update Nature of Business
    if naics := correction_filing.get("correction", {}).get("business", {}).get("naics"):
        to_naics_code = naics.get("naicsCode")
        to_naics_description = naics.get("naicsDescription")
        if business.naics_description != to_naics_description:
            filing_meta.correction = {
                **filing_meta.correction,
                "fromNaicsCode": business.naics_code,
                   "toNaicsCode": to_naics_code,
                   "naicsDescription": to_naics_description}
            business_info.update_naics_info(business, naics)

    # update name translations, if any
    with suppress(IndexError, KeyError, TypeError):
        alias_json = dpath.get(correction_filing, "/correction/nameTranslations")
        aliases.update_aliases(business, alias_json)

    # Update offices if present
    with suppress(IndexError, KeyError, TypeError):
        offices_structure = dpath.get(correction_filing, "/correction/offices")
        _update_addresses(offices_structure)

    # Update parties
    with suppress(IndexError, KeyError, TypeError):
        party_json = dpath.get(correction_filing, "/correction/parties")
        update_parties(business, party_json, correction_filing_rec)

    # update court order, if any is present
    with suppress(IndexError, KeyError, TypeError):
        court_order_json = dpath.get(correction_filing, "/correction/courtOrder")
        filings.update_filing_court_order(correction_filing_rec, court_order_json)

    # update business start date, if any is present
    with suppress(IndexError, KeyError, TypeError):
        business_start_date = dpath.get(correction_filing, "/correction/startDate")
        if business_start_date:
            business.start_date = LegislationDatetime.as_utc_timezone_from_legislation_date_str(business_start_date)

    # update share structure and resolutions, if any
    with suppress(IndexError, KeyError, TypeError):
        share_structure = dpath.get(correction_filing, "/correction/shareStructure")
        shares.update_share_structure_correction(business, share_structure)

    # update resolution, if any
    with suppress(IndexError, KeyError, TypeError):
        resolution = dpath.get(correction_filing, "/correction/resolution")
        resolutions.update_resolution(business, resolution)
        if resolution:
            filing_meta.correction = {**filing_meta.correction, "hasResolution": True}

    # update signatory, if any
    with suppress(IndexError, KeyError, TypeError):
        signatory = dpath.get(correction_filing, "/correction/signatory")
        resolutions.update_signatory(business, signatory)

    # update business signing date, if any is present
    with suppress(IndexError, KeyError, TypeError):
        signing_date = dpath.get(correction_filing, "/correction/signingDate")
        resolutions.update_signing_date(business, signing_date)

    # update business resolution date, if any is present
    with suppress(IndexError, KeyError, TypeError):
        resolution_date = dpath.get(correction_filing, "/correction/resolutionDate")
        resolutions.update_resolution_date(business, resolution_date)

    # update rules, if any
    with suppress(IndexError, KeyError, TypeError):
        rules_file_key = dpath.get(correction_filing, "/correction/rulesFileKey")
        rules_file_name = dpath.get(correction_filing, "/correction/rulesFileName")
        if rules_file_key:
            rules_and_memorandum.update_rules(business, correction_filing_rec, rules_file_key, rules_file_name)
            filing_meta.correction = {**filing_meta.correction,
                                      "uploadNewRules": True}

    # update memorandum, if any
    with suppress(IndexError, KeyError, TypeError):
        memorandum_file_key = dpath.get(correction_filing, "/correction/memorandumFileKey")
        memorandum_file_name = dpath.get(correction_filing, "/correction/memorandumFileName")
        if memorandum_file_key:
            rules_and_memorandum.update_memorandum(business, correction_filing_rec,
                                                   memorandum_file_key, memorandum_file_name)
            filing_meta.correction = {**filing_meta.correction,
                                      "uploadNewMemorandum": True}

    with suppress(IndexError, KeyError, TypeError):
        if dpath.get(correction_filing, "/correction/memorandumInResolution"):
            filing_meta.correction = {**filing_meta.correction,
                                      "memorandumInResolution": True}

    with suppress(IndexError, KeyError, TypeError):
        if dpath.get(correction_filing, "/correction/rulesInResolution"):
            filing_meta.correction = {**filing_meta.correction,
                                      "rulesInResolution": True}


def update_parties(business: Business, parties: list, correction_filing_rec: Filing):
    """Create a new party or get them if they already exist."""
    if correction_filing_rec.colin_event_ids:
        # This may not be covering all the cases, introducing this to sync back the BEN to BC business as of today.
        directors = PartyRole.get_parties_by_role(business.id, PartyRole.RoleTypes.DIRECTOR.value)
        for party_info in parties:
            for director in directors:
                existing_director_name = \
                    director.party.first_name + director.party.middle_initial + director.party.last_name
                current_new_director_name = \
                    party_info["officer"].get("firstName") + party_info["officer"].get("middleInitial", "") + \
                    party_info["officer"].get("lastName")
                if existing_director_name.upper() == current_new_director_name.upper():
                    party_info["officer"]["id"] = director.party.id
                    break

        filing_json = copy.deepcopy(correction_filing_rec.filing_json)
        filing_json["filing"]["correction"]["parties"] = parties
        correction_filing_rec._filing_json = filing_json  # pylint: disable=protected-access; bypass to update

    # Cease the party roles not present in the edit request
    if parties is None:
        return
    end_date_time = datetime.datetime.now(datetime.UTC)
    parties_to_update = [party.get("officer").get("id") for party in parties if
                         party.get("officer").get("id") is not None]
    existing_party_roles = PartyRole.get_party_roles(business.id, end_date_time.date())
    for party_role in existing_party_roles:
        # Safety check, skip roles that should not be ceased
        if (expected_role := CEASE_ROLE_MAPPING.get(business.legal_type)) and \
                party_role.role != expected_role:
            continue
        if party_role.party_id not in parties_to_update:
            party_role.cessation_date = end_date_time

    # Create and Update
    for party_info in parties:
        # Create if id not present
        # If id is present and is a GUID then this is an id specific to the UI which is not relevant to the backend.
        # The backend will have an id of type int
        if not party_info.get("officer").get("id") or \
                (party_info.get("officer").get("id") and not isinstance(party_info.get("officer").get("id"), int)):
            _create_party_info(business, correction_filing_rec, party_info)
        else:
            # Update if id is present
            _update_party(party_info)


def _update_party(party_info):
    party = Party.find_by_id(party_id=party_info.get("officer").get("id"))
    if party:
        party.first_name = party_info["officer"].get("firstName", "").upper()
        party.last_name = party_info["officer"].get("lastName", "").upper()
        party.middle_initial = party_info["officer"].get("middleName", "").upper()
        party.title = party_info.get("title", "").upper()
        party.organization_name = party_info["officer"].get("organizationName", "").upper()
        party.party_type = party_info["officer"].get("partyType")
        party.email = party_info["officer"].get("email", "").lower()
        party.identifier = party_info["officer"].get("identifier", "").upper()
        # add addresses to party
        if party_info.get("deliveryAddress", None):
            update_address(party.delivery_address, party_info.get("deliveryAddress"))
        if party_info.get("mailingAddress", None):
            update_address(party.mailing_address, party_info.get("mailingAddress"))


def _create_party_info(business, correction_filing_rec, party_info):
    party = create_party(business_id=business.id, party_info=party_info, create=False)
    for role_type in party_info.get("roles"):
        role_str = role_type.get("roleType", "").lower()
        role = {
            "roleType": role_str,
            "appointmentDate": role_type.get("appointmentDate", None),
            "cessationDate": role_type.get("cessationDate", None)
        }
        party_role = create_role(party=party, role_info=role)
        if party_role.role in [PartyRole.RoleTypes.COMPLETING_PARTY.value]:
            correction_filing_rec.filing_party_roles.append(party_role)
        else:
            business.party_roles.append(party_role)


def _update_addresses(offices_structure):
    """Update addresses when offices exists."""
    for addresses in offices_structure.values():
        for updated_address in addresses.values():
            if updated_address.get("id", None):
                address = Address.find_by_id(updated_address.get("id"))
                if address:
                    update_address(address, updated_address)
