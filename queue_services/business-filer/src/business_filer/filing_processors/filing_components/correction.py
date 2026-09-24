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
from business_common.utils import LegislationDatetime
from business_model.models import Address, Business, Filing, Jurisdiction, Party, PartyRole

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors.filing_components import (
    aliases,
    business_info,
    create_address,
    create_party,
    create_role,
    filings,
    resolutions,
    rules_and_memorandum,
    shares,
    update_address,
)
from business_filer.filing_processors.filing_components.relationships import (
    cease_relationships,
    create_relationships,
    update_relationship_addresses,
    update_relationship_entity_info,
    update_relationships_appointment_date,
)
from business_filer.services.utils import is_same_str

CEASE_ROLE_MAPPING = {
    **dict.fromkeys(Business.CORPS, PartyRole.RoleTypes.DIRECTOR.value),
    Business.LegalTypes.COOP.value: PartyRole.RoleTypes.DIRECTOR.value,
    Business.LegalTypes.PARTNERSHIP.value: PartyRole.RoleTypes.PARTNER.value,
    Business.LegalTypes.SOLE_PROP.value: PartyRole.RoleTypes.PROPRIETOR.value,
}

CORRECTION_NAME_REQUEST_PATH = "/correction/nameRequest"
CORRECTION_PARTIES_PATH = "/correction/parties"
CORRECTION_OFFICES_PATH = "/correction/offices"
CORRECTION_NAME_TRANSLATIONS_PATH = "/correction/nameTranslations"
CORRECTION_SHARE_STRUCTURE_PATH = "/correction/shareStructure"


def correct_business_data(business: Business,
                          correction_filing_rec: Filing,
                          correction_filing: dict,
                          filing_meta: FilingMeta):
    """Update business data on correction."""
    # update court orders, if any is present
    with suppress(IndexError, KeyError, TypeError):
        court_orders_json = dpath.get(correction_filing, "/correction/courtOrders")
        filings.update_court_orders(business, court_orders_json, filing_meta)

    # update court order, if any is present
    with suppress(IndexError, KeyError, TypeError):
        court_order_json = dpath.get(correction_filing, "/correction/courtOrder")
        filings.create_court_order(correction_filing_rec, court_order_json, filing_meta)

    if business.state == Business.State.HISTORICAL.value:
        if business.legal_type in Business.CORPS:
            correct_corp_data_historical(business, correction_filing_rec, correction_filing, filing_meta)

        return

    if business.legal_type == Business.LegalTypes.COOP.value:
        correct_coop_data(business, correction_filing_rec, correction_filing, filing_meta)
    elif business.legal_type in Business.CORPS:
        correct_corp_data(business, correction_filing_rec, correction_filing, filing_meta)
    elif business.legal_type in (Business.LegalTypes.PARTNERSHIP.value, Business.LegalTypes.SOLE_PROP.value):
        correct_firm_data(business, correction_filing_rec, correction_filing, filing_meta)


def correct_firm_data(business: Business,
                      correction_filing_rec: Filing,
                      correction_filing: dict,
                      filing_meta: FilingMeta):
    """Correct firm data."""
    # Update business legalName if present
    with suppress(IndexError, KeyError, TypeError):
        name_request_json = dpath.get(correction_filing, CORRECTION_NAME_REQUEST_PATH)
        from_legal_name = business.legal_name
        business_info.set_legal_name(business.identifier, business, name_request_json)
        if from_legal_name != business.legal_name:
            filing_meta.correction = {
                **filing_meta.correction,
                "fromLegalName": from_legal_name,
                "toLegalName": business.legal_name
            }

    # Update offices if present
    with suppress(IndexError, KeyError, TypeError):
        offices_structure = dpath.get(correction_filing, CORRECTION_OFFICES_PATH)
        _update_addresses(offices_structure)

    # Update parties
    with suppress(IndexError, KeyError, TypeError):
        party_json = dpath.get(correction_filing, CORRECTION_PARTIES_PATH)
        update_parties(business, party_json, correction_filing_rec)

    # Update Nature of Business
    if naics := correction_filing.get("correction", {}).get("business", {}).get("naics"):
        to_naics_code = naics.get("naicsCode")
        to_naics_description = naics.get("naicsDescription")
        if business.naics_description != to_naics_description:
            filing_meta.correction = {
                **filing_meta.correction,
                "fromNaicsCode": business.naics_code,
                "toNaicsCode": to_naics_code,
                "naicsDescription": to_naics_description
            }
            business_info.update_naics_info(business, naics)

    # update business start date, if any is present
    with suppress(IndexError, KeyError, TypeError):
        business_start_date = dpath.get(correction_filing, "/correction/startDate")
        if business_start_date:
            business.start_date = LegislationDatetime.as_utc_timezone_from_legislation_date_str(business_start_date)


def correct_coop_data(business: Business,  # noqa: PLR0915
                      correction_filing_rec: Filing,
                      correction_filing: dict,
                      filing_meta: FilingMeta):
    """Correct coop data."""
    # Update business legalName if present
    with suppress(IndexError, KeyError, TypeError):
        name_request_json = dpath.get(correction_filing, CORRECTION_NAME_REQUEST_PATH)
        from_legal_name = business.legal_name
        business_info.set_legal_name(business.identifier, business, name_request_json)
        if from_legal_name != business.legal_name:
            filing_meta.correction = {
                **filing_meta.correction,
                "fromLegalName": from_legal_name,
                "toLegalName": business.legal_name
            }

    # Update offices if present
    with suppress(IndexError, KeyError, TypeError):
        offices_structure = dpath.get(correction_filing, CORRECTION_OFFICES_PATH)
        _update_addresses(offices_structure)

    # Update parties
    with suppress(IndexError, KeyError, TypeError):
        party_json = dpath.get(correction_filing, CORRECTION_PARTIES_PATH)
        update_parties(business, party_json, correction_filing_rec)

    # Update cooperativeAssociationType if present
    with suppress(IndexError, KeyError, TypeError):
        coop_association_type = dpath.get(correction_filing, "/correction/cooperativeAssociationType")
        from_association_type = business.association_type
        if coop_association_type:
            business_info.set_association_type(business, coop_association_type)
            filing_meta.correction = {
                **filing_meta.correction,
                "fromCooperativeAssociationType": from_association_type,
                "toCooperativeAssociationType": business.association_type
            }

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


def correct_corp_data_historical(business: Business,
                                 correction_filing_rec: Filing,
                                 correction_filing: dict,
                                 filing_meta: FilingMeta):
    """Correct historical corporation data."""
    # Update relationships (newer schema for parties)
    with suppress(IndexError, KeyError, TypeError):
        relationships = dpath.get(correction_filing, "/correction/relationships")
        create_relationships(relationships, business, correction_filing_rec)  # completing party

        # custodian
        update_relationship_addresses(relationships, business)
        update_relationship_entity_info(relationships, business)

    with suppress(IndexError, KeyError, TypeError):
        continuation_out = dpath.get(correction_filing, "/correction/continuationOut")
        if continuation_out:
            update_out("continuationOut", business, continuation_out, filing_meta)

    with suppress(IndexError, KeyError, TypeError):
        amalgamation_out = dpath.get(correction_filing, "/correction/amalgamationOut")
        if amalgamation_out:
            update_out("amalgamationOut", business, amalgamation_out, filing_meta)


def update_out(out_type: str, business: Business, out: dict, filing_meta: FilingMeta):
    """Update continuation out or amalgamation out."""
    out_date_str = out.get("date")
    country = out.get("country").upper()
    region = out.get("region").upper() if out.get("region") else None
    legal_name = out.get("legalName")
    out_date = LegislationDatetime.as_utc_timezone_from_legislation_date_str(out_date_str)
    existing_out_date = (
        business.continuation_out_date if out_type == "continuationOut" else business.amalgamation_out_date
    )

    if not (
        is_same_str(country, business.jurisdiction) and
        is_same_str(region, business.foreign_jurisdiction_region) and
        is_same_str(legal_name, business.foreign_legal_name) and
        out_date == existing_out_date
    ):
        filing_meta.correction[out_type] = {
            "country": country,
            "region": region,
            "legalName": legal_name,
            "date": out_date_str
        }

    if out_type == "continuationOut":
        business.continuation_out_date = out_date
    elif out_type == "amalgamationOut":
        business.amalgamation_out_date = out_date

    business.jurisdiction = country
    business.foreign_legal_name = legal_name
    business.foreign_jurisdiction_region = region


def correct_corp_data(business: Business,
                      correction_filing_rec: Filing,
                      correction_filing: dict,
                      filing_meta: FilingMeta):
    """Correct corporation data."""
    to_legal_type = None
    with suppress(IndexError, KeyError, TypeError):
        to_legal_type = dpath.get(correction_filing, "/correction/newLegalType")
        if to_legal_type and business.legal_type != to_legal_type:
            filing_meta.correction = {
                **filing_meta.correction,
                "fromLegalType": business.legal_type,
                "toLegalType": to_legal_type
            }
            business_info.set_corp_type(business, {"legalType": to_legal_type})

    # Update business legalName if present
    with suppress(IndexError, KeyError, TypeError):
        name_request_json = dpath.get(correction_filing, CORRECTION_NAME_REQUEST_PATH)
        from_legal_name = business.legal_name
        business_info.set_legal_name(business.identifier, business, name_request_json, to_legal_type)
        if from_legal_name != business.legal_name:
            filing_meta.correction = {
                **filing_meta.correction,
                "fromLegalName": from_legal_name,
                "toLegalName": business.legal_name
            }

    # update name translations, if any
    with suppress(IndexError, KeyError, TypeError):
        alias_json = dpath.get(correction_filing, CORRECTION_NAME_TRANSLATIONS_PATH)
        aliases.update_aliases(business, alias_json)

    # Update offices if present
    with suppress(IndexError, KeyError, TypeError):
        offices_structure = dpath.get(correction_filing, CORRECTION_OFFICES_PATH)
        _update_addresses(offices_structure)

    # Update parties
    with suppress(IndexError, KeyError, TypeError):
        party_json = dpath.get(correction_filing, CORRECTION_PARTIES_PATH)
        update_parties(business, party_json, correction_filing_rec)

    # Update relationships (newer schema for parties)
    with suppress(IndexError, KeyError, TypeError):
        relationships = dpath.get(correction_filing, "/correction/relationships")
        create_relationships(relationships, business, correction_filing_rec)
        cease_relationships(relationships,
                            business,
                            [
                                PartyRole.RoleTypes.DIRECTOR.value,
                                PartyRole.RoleTypes.LIQUIDATOR.value,
                                PartyRole.RoleTypes.RECEIVER.value
                            ],
                            filing_meta.application_date)

        update_relationships_appointment_date(relationships, business, [PartyRole.RoleTypes.DIRECTOR.value])
        update_relationship_addresses(relationships, business)
        update_relationship_entity_info(relationships, business)
        _set_lear_only(correction_filing, correction_filing_rec, relationships, business)

    # update share structure and resolutions, if any
    with suppress(IndexError, KeyError, TypeError):
        share_structure = dpath.get(correction_filing, CORRECTION_SHARE_STRUCTURE_PATH)
        shares.update_share_structure_correction(business, share_structure)

    with suppress(IndexError, KeyError, TypeError):
        amalgamation = dpath.get(correction_filing, "/correction/amalgamation")
        if amalgamation:
            update_amalgamation(business, amalgamation, filing_meta)

    with suppress(IndexError, KeyError, TypeError):
        continuation_in = dpath.get(correction_filing, "/correction/continuationIn")
        if continuation_in:
            update_continuation_in(business, continuation_in, filing_meta)


def update_continuation_in(business: Business, continuation_in: dict, filing_meta: FilingMeta):
    """Update continuation in details on correction."""
    jurisdiction = Jurisdiction.get_continuation_in_jurisdiction(business.id)

    country = continuation_in.get("country")
    region = continuation_in.get("region")

    if not (
        is_same_str(country, jurisdiction.country) and
        is_same_str(region, jurisdiction.region)
    ):
        filing_meta.correction["continuationIn"] = {
            "country": country,
            "region": region
        }

    jurisdiction.country = country
    jurisdiction.region = region
    jurisdiction.legal_name = continuation_in.get("legalName")
    jurisdiction.identifier = continuation_in.get("identifier")
    incorporation_date = continuation_in.get("incorporationDate")
    jurisdiction.incorporation_date = LegislationDatetime.as_utc_timezone_from_legislation_date_str(incorporation_date)

    if expro := continuation_in.get("expro"):
        jurisdiction.expro_identifier = expro.get("identifier")
        jurisdiction.expro_legal_name = expro.get("legalName")


def update_amalgamation(business: Business, amalgamation: dict, filing_meta: FilingMeta):
    """Update amalgamation details on correction."""
    amalgamation_db = business.amalgamation.first()
    amalgamating_businesses_db = amalgamation_db.amalgamating_businesses.all()
    amalgamating_businesses = amalgamation.get("amalgamatingBusinesses", [])
    amalgamation_meta = {}

    if amalgamation_db.court_approval != bool(amalgamation.get("courtApproval")):
        amalgamation_db.court_approval = bool(amalgamation.get("courtApproval"))
        amalgamation_meta["courtApproval"] = amalgamation.get("courtApproval")

    amalgamating_businesses_corrected = False
    for amalgamating_business in amalgamating_businesses:
        amalgamating_business_db = next((ab for ab in amalgamating_businesses_db
                                         if ab.id == amalgamating_business.get("id")), None)
        foreign_identifier = amalgamating_business.get("identifier")
        foreign_name = amalgamating_business.get("legalName")
        if (
            not is_same_str(amalgamating_business_db.foreign_identifier, foreign_identifier) or
            not is_same_str(amalgamating_business_db.foreign_name, foreign_name)
        ):
            amalgamating_businesses_corrected = True
            amalgamating_business_db.foreign_identifier = foreign_identifier
            amalgamating_business_db.foreign_name = foreign_name

        if foreign_jurisdiction := amalgamating_business.get("foreignJurisdiction"):
            country = foreign_jurisdiction.get("country").upper()
            region = (foreign_jurisdiction.get("region") or "").upper()
            if (
                not is_same_str(amalgamating_business_db.foreign_jurisdiction, country) or
                not is_same_str(amalgamating_business_db.foreign_jurisdiction_region, region)
            ):
                amalgamating_businesses_corrected = True
                amalgamating_business_db.foreign_jurisdiction = country
                amalgamating_business_db.foreign_jurisdiction_region = region

    if amalgamating_businesses_corrected:
        amalgamation_meta["amalgamatingBusinessesCorrected"] = amalgamating_businesses_corrected

    if amalgamation_meta:
        filing_meta.correction["amalgamation"] = amalgamation_meta


def update_parties(business: Business, parties: list, correction_filing_rec: Filing):
    """Create a new party or get them if they already exist."""
    if correction_filing_rec.colin_event_ids:
        # This may not be covering all the cases, introducing this to sync back the BEN to BC business as of today.
        directors = PartyRole.get_parties_by_role(business.id, PartyRole.RoleTypes.DIRECTOR.value)
        for party_info in parties:
            for director in directors:
                current_new_director_name = " ".join([
                    x.strip() for x in [
                        party_info["officer"].get("firstName"),
                        party_info["officer"].get("middleInitial"),
                        party_info["officer"].get("lastName")
                    ] if x and x.strip()]).upper()
                if director.party.name == current_new_director_name:
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
        party.first_name = (party_info["officer"].get("firstName") or "").upper()
        party.last_name = (party_info["officer"].get("lastName") or "").upper()
        party.middle_initial = (party_info["officer"].get("middleName") or "").upper()
        party.title = (party_info.get("title") or "").upper()
        party.organization_name = (party_info["officer"].get("organizationName") or "").upper()
        party.party_type = party_info["officer"].get("partyType")
        party.email = (party_info["officer"].get("email") or "").lower()
        party.identifier = (party_info["officer"].get("identifier") or "").upper()
        # add addresses to party
        if party.delivery_address:
            party.delivery_address = update_address(party.delivery_address, party_info.get("deliveryAddress"))
        else:
            party.delivery_address = create_address(party_info.get("deliveryAddress"), Address.DELIVERY)

        if party.mailing_address:
            party.mailing_address = update_address(party.mailing_address, party_info.get("mailingAddress"))
        else:
            party.mailing_address = create_address(party_info.get("mailingAddress"), Address.MAILING)

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


def _set_lear_only(correction_filing: dict, filing_rec: Filing, relationships: list[dict], business: Business):
    """Set lear_only if the only changes are to receivers and/or liquidators."""
    def _has_director_role(relationship: dict):
        """Return True if the relationship contains a director role."""
        return any(role for role in relationship["roles"] if role["roleType"].lower() == "director")

    if (
        (
            not any((
                # below are the only changes the colin api supports for corrections
                bool(dpath.get(correction_filing, CORRECTION_NAME_REQUEST_PATH, default=None)),
                bool(dpath.get(correction_filing, CORRECTION_NAME_TRANSLATIONS_PATH, default=None)),
                bool(dpath.get(correction_filing, CORRECTION_OFFICES_PATH, default=None)),
                bool(dpath.get(correction_filing, CORRECTION_PARTIES_PATH, default=None)),
                bool(dpath.get(correction_filing, CORRECTION_SHARE_STRUCTURE_PATH, default=None)))
        )) and (
            relationships and
            # colin-api only supports relationships changes to directors
            not any(relationship for relationship in relationships if _has_director_role(relationship))
        )
    ):
        filing_rec.lear_only = True
            