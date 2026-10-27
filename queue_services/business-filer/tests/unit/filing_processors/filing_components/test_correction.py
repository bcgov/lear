# Copyright © 2026 Province of British Columbia
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
"""Unit Tests for the correction filing component processor: relationships in correct_corp_data."""
import copy
from datetime import datetime, timezone
import pytest
from business_model.models import Address, Business, Filing, Party, PartyRole

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors.filing_components import create_address
from business_filer.filing_processors.filing_components.correction import correct_corp_data
from tests.unit import create_business, create_filing

DELIVERY_ADDRESS = {
    'streetAddress': '123 Delivery St',
    'addressCity': 'Victoria',
    'addressCountry': 'CA',
    'postalCode': 'V8W 1W4',
    'addressRegion': 'BC'
}

MAILING_ADDRESS = {
    'streetAddress': '456 Mailing Ave',
    'addressCity': 'Vancouver',
    'addressCountry': 'CA',
    'postalCode': 'V6B 2T9',
    'addressRegion': 'BC'
}


@pytest.fixture
def business(session):
    """Return a test business."""
    import random
    identifier = f'BC{random.randint(1000000, 9999999)}'
    return create_business(identifier, legal_type='BEN')


@pytest.fixture
def filing_rec(session, business):
    """Return a test filing record associated with the business."""
    effective_dt = datetime(2023, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    filing = create_filing(business_id=business.id, filing_date=effective_dt)
    filing.effective_date = effective_dt
    filing.save()
    return filing


def _create_filing_meta(app_date=None) -> FilingMeta:
    """Return a FilingMeta instance configured for correction."""
    meta = FilingMeta(application_date=app_date or datetime(2023, 7, 1, tzinfo=timezone.utc))
    meta.correction = {}
    return meta


def test_correct_corp_data_relationships_create_director(app, session, business, filing_rec):
    """Test creating a new director via correction relationships."""
    filing_meta = _create_filing_meta()
    correction_filing = {
        'correction': {
            'relationships': [
                {
                    'entity': {'givenName': 'Alice', 'familyName': 'Wonderland'},
                    'deliveryAddress': copy.deepcopy(DELIVERY_ADDRESS),
                    'mailingAddress': copy.deepcopy(MAILING_ADDRESS),
                    'roles': [{'roleType': 'Director'}]
                }
            ]
        }
    }

    correct_corp_data(business, filing_rec, correction_filing, filing_meta)
    session.commit()

    roles = business.party_roles.all()
    assert len(roles) == 1
    assert roles[0].role == PartyRole.RoleTypes.DIRECTOR.value
    assert roles[0].party.first_name == 'ALICE'
    assert roles[0].party.last_name == 'WONDERLAND'
    assert roles[0].cessation_date is None

    # NOA flag should be True because a director changed
    assert filing_meta.correction.get('hasNoa') is True
    # lear_only should NOT be True because director changes are supported in colin
    assert filing_rec.lear_only is not True


def test_correct_corp_data_relationships_create_liquidator_receiver(app, session, business, filing_rec):
    """Test creating liquidator/receiver via correction relationships sets lear_only and hasNoa=False."""
    filing_meta = _create_filing_meta()
    correction_filing = {
        'correction': {
            'relationships': [
                {
                    'entity': {'businessName': 'Liquidators Inc.'},
                    'deliveryAddress': copy.deepcopy(DELIVERY_ADDRESS),
                    'roles': [{'roleType': 'Liquidator'}]
                },
                {
                    'entity': {'givenName': 'Bob', 'familyName': 'Receiver'},
                    'deliveryAddress': copy.deepcopy(DELIVERY_ADDRESS),
                    'roles': [{'roleType': 'Receiver'}]
                }
            ]
        }
    }

    correct_corp_data(business, filing_rec, correction_filing, filing_meta)
    session.commit()

    roles = business.party_roles.all()
    assert len(roles) == 2
    role_names = {r.role for r in roles}
    assert role_names == {PartyRole.RoleTypes.LIQUIDATOR.value, PartyRole.RoleTypes.RECEIVER.value}

    # NOA flag should remain False because no director changed
    assert filing_meta.correction.get('hasNoa') is False
    # lear_only should be set to True because only liquidators and receivers were changed
    assert filing_rec.lear_only is True


def test_correct_corp_data_relationships_cease_roles(app, session, business, filing_rec):
    """Test ceasing roles via correction: only director, liquidator, and receiver are allowed to cease."""
    app_date = datetime(2023, 7, 15, 10, 0, 0, tzinfo=timezone.utc)
    filing_meta = _create_filing_meta(app_date=app_date)

    # Setup active director, liquidator, receiver, and CEO
    dir_party = Party(first_name='DIR', last_name='ONE')
    dir_party.save()
    dir_role = PartyRole(role=PartyRole.RoleTypes.DIRECTOR.value, party_id=dir_party.id, business_id=business.id)
    dir_role.save()

    liq_party = Party(first_name='LIQ', last_name='ONE')
    liq_party.save()
    liq_role = PartyRole(role=PartyRole.RoleTypes.LIQUIDATOR.value, party_id=liq_party.id, business_id=business.id)
    liq_role.save()

    rec_party = Party(first_name='REC', last_name='ONE')
    rec_party.save()
    rec_role = PartyRole(role=PartyRole.RoleTypes.RECEIVER.value, party_id=rec_party.id, business_id=business.id)
    rec_role.save()

    ceo_party = Party(first_name='CEO', last_name='ONE')
    ceo_party.save()
    ceo_role = PartyRole(role=PartyRole.RoleTypes.CEO.value, party_id=ceo_party.id, business_id=business.id)
    ceo_role.save()

    session.commit()

    correction_filing = {
        'correction': {
            'relationships': [
                {
                    'entity': {'identifier': str(dir_party.id)},
                    'roles': [{'roleType': 'Director', 'cessationDate': '2023-07-15'}]
                },
                {
                    'entity': {'identifier': str(liq_party.id)},
                    'roles': [{'roleType': 'Liquidator', 'cessationDate': '2023-07-15'}]
                },
                {
                    'entity': {'identifier': str(rec_party.id)},
                    'roles': [{'roleType': 'Receiver', 'cessationDate': '2023-07-15'}]
                },
                {
                    'entity': {'identifier': str(ceo_party.id)},
                    'roles': [{'roleType': 'CEO', 'cessationDate': '2023-07-15'}]
                }
            ]
        }
    }

    correct_corp_data(business, filing_rec, correction_filing, filing_meta)
    session.commit()

    # Liquidator and receiver are ceased with application_date (not updated by update_relationships_cessation_date)
    assert PartyRole.find_by_internal_id(liq_role.id).cessation_date == app_date
    assert PartyRole.find_by_internal_id(rec_role.id).cessation_date == app_date

    # Director cessation date is updated/corrected to the payload's cessationDate
    assert PartyRole.find_by_internal_id(dir_role.id).cessation_date.date().isoformat() == '2023-07-15'

    # CEO role should NOT be ceased (not in allowed cease roles in correction)
    assert PartyRole.find_by_internal_id(ceo_role.id).cessation_date is None

    # NOA flag is True because director was in the relationships
    assert filing_meta.correction.get('hasNoa') is True


def test_correct_corp_data_relationships_update_appointment_date(app, session, business, filing_rec):
    """Test updating appointment date: only director role is updated."""
    filing_meta = _create_filing_meta()

    original_appt = datetime(2020, 1, 1, tzinfo=timezone.utc)
    new_appt = datetime(2018, 5, 20, tzinfo=timezone.utc)

    dir_party = Party(first_name='DIR', last_name='TWO')
    dir_party.save()
    dir_role = PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        party_id=dir_party.id,
        business_id=business.id,
        appointment_date=original_appt
    )
    dir_role.save()

    rec_party = Party(first_name='REC', last_name='TWO')
    rec_party.save()
    rec_role = PartyRole(
        role=PartyRole.RoleTypes.RECEIVER.value,
        party_id=rec_party.id,
        business_id=business.id,
        appointment_date=original_appt
    )
    rec_role.save()

    session.commit()

    correction_filing = {
        'correction': {
            'relationships': [
                {
                    'entity': {'identifier': str(dir_party.id)},
                    'roles': [{'roleType': 'Director', 'appointmentDate': new_appt}]
                },
                {
                    'entity': {'identifier': str(rec_party.id)},
                    'roles': [{'roleType': 'Receiver', 'appointmentDate': new_appt}]
                }
            ]
        }
    }

    correct_corp_data(business, filing_rec, correction_filing, filing_meta)
    session.commit()

    # Director appointment date is updated
    assert PartyRole.find_by_internal_id(dir_role.id).appointment_date == new_appt
    # Receiver appointment date is NOT updated (only DIRECTOR allowed)
    assert PartyRole.find_by_internal_id(rec_role.id).appointment_date == original_appt


def test_correct_corp_data_relationships_update_cessation_date(app, session, business, filing_rec):
    """Test updating cessation date on an existing director role."""
    filing_meta = _create_filing_meta()

    original_cease = datetime(2022, 1, 1, tzinfo=timezone.utc)
    new_cease = datetime(2022, 6, 30, tzinfo=timezone.utc)

    dir_party = Party(first_name='DIR', last_name='THREE')
    dir_party.save()
    dir_role = PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        party_id=dir_party.id,
        business_id=business.id,
        appointment_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
        cessation_date=original_cease
    )
    dir_role.save()
    session.commit()

    correction_filing = {
        'correction': {
            'relationships': [
                {
                    'entity': {'identifier': str(dir_party.id)},
                    'roles': [{'roleType': 'Director', 'cessationDate': new_cease}]
                }
            ]
        }
    }

    correct_corp_data(business, filing_rec, correction_filing, filing_meta)
    session.commit()

    assert PartyRole.find_by_internal_id(dir_role.id).cessation_date == new_cease


def test_correct_corp_data_relationships_update_addresses_and_entity_info(app, session, business, filing_rec):
    """Test updating address and personal information for an existing party relationship."""
    filing_meta = _create_filing_meta()

    party = Party(first_name='OLDGIVEN', last_name='OLDLAST')
    party.delivery_address = create_address(DELIVERY_ADDRESS, Address.DELIVERY)
    party.save()
    role = PartyRole(role=PartyRole.RoleTypes.DIRECTOR.value, party_id=party.id, business_id=business.id)
    role.save()
    session.commit()

    updated_delivery = copy.deepcopy(DELIVERY_ADDRESS)
    updated_delivery['streetAddress'] = '789 Corrected Blvd'

    correction_filing = {
        'correction': {
            'relationships': [
                {
                    'entity': {
                        'identifier': str(party.id),
                        'givenName': 'NewGiven',
                        'familyName': 'NewLast',
                        'email': 'new.email@example.com'
                    },
                    'deliveryAddress': updated_delivery
                }
            ]
        }
    }

    correct_corp_data(business, filing_rec, correction_filing, filing_meta)
    session.commit()

    updated_party = Party.find_by_id(party.id)
    assert updated_party.first_name == 'NEWGIVEN'
    assert updated_party.last_name == 'NEWLAST'
    assert updated_party.email == 'NEW.EMAIL@EXAMPLE.COM'
    assert updated_party.delivery_address.street == '789 Corrected Blvd'


def test_correct_corp_data_relationships_lear_only_not_set_if_other_changes(app, session, business, filing_rec):
    """Test lear_only is False if liquidator/receiver relationships coexist with other changes like offices."""
    filing_meta = _create_filing_meta()
    correction_filing = {
        'correction': {
            'relationships': [
                {
                    'entity': {'businessName': 'Liquidators Inc.'},
                    'roles': [{'roleType': 'Liquidator'}]
                }
            ],
            'offices': {
                'registeredOffice': {
                    'deliveryAddress': copy.deepcopy(DELIVERY_ADDRESS),
                    'mailingAddress': copy.deepcopy(MAILING_ADDRESS)
                }
            }
        }
    }

    correct_corp_data(business, filing_rec, correction_filing, filing_meta)
    session.commit()

    # Even though relationships only had Liquidator, offices was also present, so lear_only must not be True
    assert filing_rec.lear_only is not True


def test_correct_corp_data_relationships_missing_or_empty(app, session, business, filing_rec):
    """Test correction filing when relationships key is absent or empty list."""
    # Case 1: missing relationships
    filing_meta1 = _create_filing_meta()
    correct_corp_data(business, filing_rec, {'correction': {}}, filing_meta1)
    session.commit()
    assert filing_meta1.correction.get('hasNoa') is False
    assert filing_rec.lear_only is not True

    # Case 2: empty relationships list
    filing_meta2 = _create_filing_meta()
    correct_corp_data(business, filing_rec, {'correction': {'relationships': []}}, filing_meta2)
    session.commit()
    assert filing_meta2.correction.get('hasNoa') is False
    assert filing_rec.lear_only is not True
