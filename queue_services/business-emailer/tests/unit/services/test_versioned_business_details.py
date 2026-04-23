# Copyright © 2026 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
"""Atomic unit tests for pure-transform helpers on VersionedBusinessDetailsService.

These eight staticmethods take a SQLAlchemy revision object (or a filing dict)
and return a plain dict. They don't touch the session, the network, or
LaunchDarkly, so we exercise them with `SimpleNamespace` stand-ins.
"""
from datetime import date, datetime
from types import SimpleNamespace

from business_model.models import Party
from business_model.utils.legislation_datetime import LegislationDatetime

from business_emailer.services.versioned_business_details import (
    VersionedBusinessDetailsService as VBDS,
)


# --------------------------------------------------------------------------- #
# share_class_revision_json                                                   #
# --------------------------------------------------------------------------- #

def test_share_class_revision_json_all_fields_populated():
    rev = SimpleNamespace(
        id=1, name="Common", priority=0,
        max_share_flag=True, max_shares="1000",
        par_value_flag=True, par_value=1.5, currency="CAD",
        special_rights_flag=False,
    )
    assert VBDS.share_class_revision_json(rev) == {
        "id": 1, "name": "Common", "priority": 0,
        "hasMaximumShares": True, "maxNumberOfShares": 1000,
        "hasParValue": True, "parValue": 1.5, "currency": "CAD",
        "hasRightsOrRestrictions": False,
    }


def test_share_class_revision_json_none_max_shares():
    rev = SimpleNamespace(
        id=2, name="Preferred", priority=1,
        max_share_flag=False, max_shares=None,
        par_value_flag=False, par_value=None, currency=None,
        special_rights_flag=True,
    )
    result = VBDS.share_class_revision_json(rev)
    assert result["maxNumberOfShares"] is None
    assert result["hasRightsOrRestrictions"] is True


# --------------------------------------------------------------------------- #
# share_series_revision_json                                                  #
# --------------------------------------------------------------------------- #

def test_share_series_revision_json_all_fields_populated():
    rev = SimpleNamespace(
        id=10, name="Series A", priority=1,
        max_share_flag=True, max_shares="250",
        special_rights_flag=True,
    )
    assert VBDS.share_series_revision_json(rev) == {
        "id": 10, "name": "Series A", "priority": 1,
        "hasMaximumShares": True, "maxNumberOfShares": 250,
        "hasRightsOrRestrictions": True,
    }


def test_share_series_revision_json_none_max_shares():
    rev = SimpleNamespace(
        id=11, name="Series B", priority=2,
        max_share_flag=False, max_shares=None,
        special_rights_flag=False,
    )
    assert VBDS.share_series_revision_json(rev)["maxNumberOfShares"] is None


# --------------------------------------------------------------------------- #
# name_translations_json                                                      #
# --------------------------------------------------------------------------- #

def test_name_translations_json_casts_id_to_str():
    rev = SimpleNamespace(id=42, alias="Le Nom", type="TRANSLATION")
    assert VBDS.name_translations_json(rev) == {
        "id": "42",
        "name": "Le Nom",
        "type": "TRANSLATION",
    }


# --------------------------------------------------------------------------- #
# resolution_json                                                             #
# --------------------------------------------------------------------------- #

def test_resolution_json_formats_date():
    rev = SimpleNamespace(id=7, resolution_date=date(2024, 3, 5),
                          resolution_type="SPECIAL")
    # "%B %-d, %Y" → "March 5, 2024"
    assert VBDS.resolution_json(rev) == {
        "id": 7,
        "date": "March 5, 2024",
        "type": "SPECIAL",
    }


# --------------------------------------------------------------------------- #
# business_revision_json                                                      #
# --------------------------------------------------------------------------- #

def test_business_revision_json_tombstone_returns_original():
    """When business_revision is None → return the passed business_json unchanged."""
    original = {"legalName": "Old Co", "identifier": "BC123"}
    assert VBDS.business_revision_json(None, original) is original


def test_business_revision_json_overlays_all_fields():
    dt = datetime(2024, 1, 15, 12, 0, 0)
    rev = SimpleNamespace(
        restriction_ind=True,
        dissolution_date=dt,
        restoration_expiry_date=dt,
        start_date=dt,
        continuation_out_date=dt,
        amalgamation_out_date=dt,
        tax_id="999000001BC0001",
        legal_name="New Co",
        legal_type="BC",
        naics_description="Software",
    )
    formatted = LegislationDatetime.format_as_legislation_date(dt)
    result = VBDS.business_revision_json(rev, {"legalName": "Old Co"})
    assert result["hasRestrictions"] is True
    assert result["dissolutionDate"] == formatted
    assert result["restorationExpiryDate"] == formatted
    assert result["startDate"] == formatted
    assert result["continuationOutDate"] == formatted
    assert result["amalgamationOutDate"] == formatted
    assert result["taxId"] == "999000001BC0001"
    assert result["legalName"] == "New Co"      # overridden
    assert result["legalType"] == "BC"
    assert result["naicsDescription"] == "Software"


def test_business_revision_json_null_dates_become_none():
    rev = SimpleNamespace(
        restriction_ind=False,
        dissolution_date=None,
        restoration_expiry_date=None,
        start_date=None,
        continuation_out_date=None,
        amalgamation_out_date=None,
        tax_id=None,
        legal_name="Co",
        legal_type="BC",
        naics_description=None,
    )
    result = VBDS.business_revision_json(rev, {})
    assert result["dissolutionDate"] is None
    assert result["restorationExpiryDate"] is None
    assert result["startDate"] is None
    assert result["continuationOutDate"] is None
    assert result["amalgamationOutDate"] is None
    # tax_id falsy → not written to output
    assert "taxId" not in result


# --------------------------------------------------------------------------- #
# get_incorporation_agreement_json / get_name_request_revision / get_contact_point_revision
# --------------------------------------------------------------------------- #

def _ia_filing(**ia_keys):
    """Build a minimal filing object with filing.json structure."""
    return SimpleNamespace(json={"filing": {"incorporationApplication": ia_keys}})


def test_get_incorporation_agreement_json_returns_value():
    filing = _ia_filing(incorporationAgreement={"type": "sample"})
    assert VBDS.get_incorporation_agreement_json(filing) == {"type": "sample"}


def test_get_incorporation_agreement_json_missing_returns_empty_dict():
    filing = _ia_filing()
    assert VBDS.get_incorporation_agreement_json(filing) == {}


def test_get_name_request_revision_returns_value():
    filing = _ia_filing(nameRequest={"legalName": "Newco"})
    assert VBDS.get_name_request_revision(filing) == {"legalName": "Newco"}


def test_get_name_request_revision_missing_returns_empty_dict():
    filing = _ia_filing()
    assert VBDS.get_name_request_revision(filing) == {}


def test_get_contact_point_revision_returns_value():
    filing = _ia_filing(contactPoint={"email": "a@b.com"})
    assert VBDS.get_contact_point_revision(filing) == {"email": "a@b.com"}


def test_get_contact_point_revision_missing_returns_empty_dict():
    filing = _ia_filing()
    assert VBDS.get_contact_point_revision(filing) == {}


# --------------------------------------------------------------------------- #
# get_header_revision                                                          #
# --------------------------------------------------------------------------- #

def test_get_header_revision_returns_header_dict():
    header = {"name": "annualReport", "date": "2024-01-01"}
    filing = SimpleNamespace(json={"filing": {"header": header}})
    assert VBDS.get_header_revision(filing) is header


# --------------------------------------------------------------------------- #
# address_revision_json                                                        #
# --------------------------------------------------------------------------- #

def test_address_revision_json_populated_with_country_description():
    rev = SimpleNamespace(
        street="123 Main St", street_additional="Suite 4",
        address_type="mailing", city="Victoria", region="BC",
        country="CA", postal_code="V8W 1A1",
        delivery_instructions="Leave at door",
    )
    result = VBDS.address_revision_json(rev)
    assert result["streetAddress"] == "123 Main St"
    assert result["streetAddressAdditional"] == "Suite 4"
    assert result["addressType"] == "mailing"
    assert result["addressCity"] == "Victoria"
    assert result["addressRegion"] == "BC"
    assert result["addressCountry"] == "CA"
    assert result["addressCountryDescription"] == "Canada"  # pycountry lookup
    assert result["postalCode"] == "V8W 1A1"
    assert result["deliveryInstructions"] == "Leave at door"


def test_address_revision_json_empty_country_skips_lookup():
    rev = SimpleNamespace(
        street=None, street_additional=None,
        address_type="delivery", city=None, region=None,
        country=None, postal_code=None, delivery_instructions=None,
    )
    result = VBDS.address_revision_json(rev)
    assert result["streetAddress"] == ""
    assert result["streetAddressAdditional"] == ""
    assert result["addressCity"] == ""
    assert result["addressRegion"] == ""
    assert result["addressCountry"] == ""
    assert result["addressCountryDescription"] == ""
    assert result["postalCode"] == ""
    assert result["deliveryInstructions"] == ""


# --------------------------------------------------------------------------- #
# party_revision_type_json                                                     #
# --------------------------------------------------------------------------- #

def test_party_revision_type_json_person_basic():
    rev = SimpleNamespace(
        party_type=Party.PartyTypes.PERSON.value,
        first_name="Jane", last_name="Doe",
        title=None, middle_initial=None, email=None,
    )
    result = VBDS.party_revision_type_json(rev, is_ia_or_after=False)
    assert result == {
        "officer": {"firstName": "Jane", "lastName": "Doe",
                    "partyType": Party.PartyTypes.PERSON.value}
    }


def test_party_revision_type_json_person_with_title_and_email():
    rev = SimpleNamespace(
        party_type=Party.PartyTypes.PERSON.value,
        first_name="Jane", last_name="Doe",
        title="Director", middle_initial=None, email="j@x.com",
    )
    result = VBDS.party_revision_type_json(rev, is_ia_or_after=False)
    assert result["title"] == "Director"
    assert result["officer"]["email"] == "j@x.com"


def test_party_revision_type_json_person_middle_initial_non_ia():
    """Non-IA → middleInitial key."""
    rev = SimpleNamespace(
        party_type=Party.PartyTypes.PERSON.value,
        first_name="Jane", last_name="Doe",
        title=None, middle_initial="A", email=None,
    )
    result = VBDS.party_revision_type_json(rev, is_ia_or_after=False)
    assert result["officer"]["middleInitial"] == "A"
    assert "middleName" not in result["officer"]


def test_party_revision_type_json_person_middle_initial_ia_or_after():
    """IA-or-after → middleName key (and middleInitial stays)."""
    rev = SimpleNamespace(
        party_type=Party.PartyTypes.PERSON.value,
        first_name="Jane", last_name="Doe",
        title=None, middle_initial="A", email=None,
    )
    result = VBDS.party_revision_type_json(rev, is_ia_or_after=True)
    assert result["officer"]["middleName"] == "A"
    assert result["officer"]["middleInitial"] == "A"


def test_party_revision_type_json_organization():
    rev = SimpleNamespace(
        party_type=Party.PartyTypes.ORGANIZATION.value,
        organization_name="Acme Ltd",
        identifier="BC1234",
        email="contact@acme.com",
    )
    result = VBDS.party_revision_type_json(rev, is_ia_or_after=False)
    assert result == {
        "officer": {
            "organizationName": "Acme Ltd",
            "partyType": Party.PartyTypes.ORGANIZATION.value,
            "identifier": "BC1234",
            "email": "contact@acme.com",
        }
    }


def test_party_revision_type_json_organization_no_email():
    rev = SimpleNamespace(
        party_type=Party.PartyTypes.ORGANIZATION.value,
        organization_name="Acme Ltd",
        identifier="BC1234",
        email=None,
    )
    result = VBDS.party_revision_type_json(rev, is_ia_or_after=True)
    assert "email" not in result["officer"]
