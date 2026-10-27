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
"""Unit Tests for the relationships filing component processor and edge cases."""
import copy
from datetime import datetime, timezone
import pytest
from business_model.models import Address, Party, PartyRole, db
from business_model.models.types.party_class_type import PartyClassType

from business_filer.filing_processors.filing_components import create_address
from business_filer.filing_processors.filing_components.relationships import (
    _create_party,
    _create_role,
    _str_to_int,
    _str_to_upper,
    cease_relationships,
    create_relationships,
    update_relationship_addresses,
    update_relationship_entity_info,
    update_relationships_appointment_date,
    update_relationships_cessation_date,
)
from tests.unit import create_business, create_filing

DELIVERY_ADDRESS = {
    'streetAddress': '123 Delivery St',
    'streetAddressAdditional': 'Suite 100',
    'addressCity': 'Victoria',
    'addressCountry': 'CA',
    'postalCode': 'V8W 1W4',
    'addressRegion': 'BC',
    'deliveryInstructions': 'Leave at front desk'
}

MAILING_ADDRESS = {
    'streetAddress': '456 Mailing Ave',
    'streetAddressAdditional': 'PO Box 200',
    'addressCity': 'Vancouver',
    'addressCountry': 'CA',
    'postalCode': 'V6B 2T9',
    'addressRegion': 'BC',
    'deliveryInstructions': ''
}


@pytest.fixture
def business(session):
    """Return a test business."""
    import random
    identifier = f'BC{random.randint(1000000, 9999999)}'
    return create_business(identifier, legal_type='BEN')


@pytest.fixture
def filing(session, business):
    """Return a test filing associated with the business."""
    effective_dt = datetime(2023, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    filing_rec = create_filing(business_id=business.id, filing_date=effective_dt)
    filing_rec.effective_date = effective_dt
    filing_rec.save()
    return filing_rec


def test_create_party_person(app, session):
    """Test creating a person party with all fields and both addresses."""
    relationship = {
        'entity': {
            'givenName': '  Jane  ',
            'familyName': 'Doe',
            'middleInitial': 'm',
            'alternateName': 'janey',
            'email': 'jane.doe@example.com',
            'businessIdentifier': 'ID-9876'
        },
        'deliveryAddress': copy.deepcopy(DELIVERY_ADDRESS),
        'mailingAddress': copy.deepcopy(MAILING_ADDRESS)
    }
    party = _create_party(relationship)
    db.session.commit()

    assert party.first_name == 'JANE'
    assert party.last_name == 'DOE'
    assert party.middle_initial == 'M'
    assert party.alternate_name == 'JANEY'
    assert party.email == 'JANE.DOE@EXAMPLE.COM'
    assert party.identifier == 'ID-9876'
    assert party.party_type == Party.PartyTypes.PERSON.value
    assert party.organization_name is None

    assert party.delivery_address is not None
    assert party.delivery_address.street == DELIVERY_ADDRESS['streetAddress']
    assert party.delivery_address.address_type == Address.DELIVERY

    assert party.mailing_address is not None
    assert party.mailing_address.street == MAILING_ADDRESS['streetAddress']
    assert party.mailing_address.address_type == Address.MAILING


def test_create_party_organization(app, session):
    """Test creating an organization party when businessName is provided."""
    relationship = {
        'entity': {
            'businessName': 'Acme Holdings Ltd.',
            'businessIdentifier': 'BC0001234',
            'email': 'contact@acme.com'
        },
        'deliveryAddress': copy.deepcopy(DELIVERY_ADDRESS)
    }
    party = _create_party(relationship)
    db.session.commit()

    assert party.party_type == Party.PartyTypes.ORGANIZATION.value
    assert party.organization_name == 'ACME HOLDINGS LTD.'
    assert party.first_name is None
    assert party.last_name is None
    assert party.email == 'CONTACT@ACME.COM'
    assert party.delivery_address is not None
    assert party.mailing_address is None


@pytest.mark.parametrize('role_type_input, expected_role', [
    ('custodian', PartyRole.RoleTypes.CUSTODIAN.value),
    ('completing party', PartyRole.RoleTypes.COMPLETING_PARTY.value),
    ('COMPLETING PARTY', PartyRole.RoleTypes.COMPLETING_PARTY.value),
    ('Director', PartyRole.RoleTypes.DIRECTOR.value),
    ('DIRECTOR', PartyRole.RoleTypes.DIRECTOR.value),
    ('incorporator', PartyRole.RoleTypes.INCORPORATOR.value),
    ('liquidator', PartyRole.RoleTypes.LIQUIDATOR.value),
    ('proprietor', PartyRole.RoleTypes.PROPRIETOR.value),
    ('partner', PartyRole.RoleTypes.PARTNER.value),
    ('applicant', PartyRole.RoleTypes.APPLICANT.value),
    ('receiver', PartyRole.RoleTypes.RECEIVER.value),
    ('ceo', PartyRole.RoleTypes.CEO.value),
    ('cfo', PartyRole.RoleTypes.CFO.value),
    ('president', PartyRole.RoleTypes.PRESIDENT.value),
    ('vice president', PartyRole.RoleTypes.VICE_PRESIDENT.value),
    ('chair', PartyRole.RoleTypes.CHAIR.value),
    ('treasurer', PartyRole.RoleTypes.TREASURER.value),
    ('secretary', PartyRole.RoleTypes.SECRETARY.value),
    ('assistant secretary', PartyRole.RoleTypes.ASSISTANT_SECRETARY.value),
    ('other', PartyRole.RoleTypes.OTHER.value),
    ('unrecognized_role', ''),
])
def test_create_role_mappings(app, session, role_type_input, expected_role):
    """Test role conversion for all valid role types as well as unknown roles."""
    party = Party(first_name='TEST', last_name='USER')
    party.save()

    default_dt = datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    role_info = {'roleType': role_type_input}
    party_role = _create_role(party, role_info, default_appointment=default_dt, role_class=None)

    assert party_role.role == expected_role
    assert party_role.appointment_date == default_dt
    assert party_role.cessation_date is None
    assert party_role.party_class_type is None


def test_create_role_dates_and_class_type(app, session):
    """Test appointment fallback, cessation date, and role_class assignment."""
    party = Party(first_name='TEST', last_name='USER')
    party.save()

    role_info = {
        'roleType': 'CEO',
        'appointmentDate': '2022-03-15',
        'cessationDate': '2024-05-20'
    }
    # When default_appointment is None, fallback to role_info['appointmentDate']
    party_role = _create_role(
        party=party,
        role_info=role_info,
        default_appointment=None,
        role_class=PartyClassType.OFFICER
    )

    assert party_role.role == PartyRole.RoleTypes.CEO.value
    assert party_role.appointment_date == '2022-03-15'
    assert party_role.cessation_date == '2024-05-20'
    assert party_role.party_class_type == PartyClassType.OFFICER


def test_create_relationships_empty_and_none(app, session, business, filing):
    """Test create_relationships with None and empty list returns empty errors."""
    assert create_relationships(None, business, filing) == []
    assert create_relationships([], business, filing) == []


def test_create_relationships_new_parties(app, session, business, filing):
    """Test creating new parties and business roles."""
    relationships = [
        {
            'entity': {'givenName': 'Bob', 'familyName': 'Vance'},
            'deliveryAddress': copy.deepcopy(DELIVERY_ADDRESS),
            'roles': [{'roleType': 'Director'}]
        },
        {
            'entity': {'businessName': 'Vance Refrigeration'},
            'deliveryAddress': copy.deepcopy(DELIVERY_ADDRESS),
            'roles': [{'roleType': 'Liquidator'}]
        }
    ]

    err = create_relationships(relationships, business, filing)
    assert err == []
    session.commit()

    active_roles = business.party_roles.all()
    assert len(active_roles) == 2
    roles_map = {r.role: r.party for r in active_roles}

    assert PartyRole.RoleTypes.DIRECTOR.value in roles_map
    assert roles_map[PartyRole.RoleTypes.DIRECTOR.value].first_name == 'BOB'
    assert roles_map[PartyRole.RoleTypes.DIRECTOR.value].last_name == 'VANCE'
    assert roles_map[PartyRole.RoleTypes.DIRECTOR.value].party_type == Party.PartyTypes.PERSON.value

    assert PartyRole.RoleTypes.LIQUIDATOR.value in roles_map
    assert roles_map[PartyRole.RoleTypes.LIQUIDATOR.value].organization_name == 'VANCE REFRIGERATION'
    assert roles_map[PartyRole.RoleTypes.LIQUIDATOR.value].party_type == Party.PartyTypes.ORGANIZATION.value


def test_create_relationships_filing_party_roles_routing(app, session, business, filing):
    """Test that completing party, incorporator, and applicant are attached to filing, not business."""
    relationships = [
        {
            'entity': {'givenName': 'Dwight', 'familyName': 'Schrute'},
            'roles': [
                {'roleType': 'Completing Party'},
                {'roleType': 'Incorporator'},
                {'roleType': 'Applicant'},
                {'roleType': 'Director'}
            ]
        }
    ]

    err = create_relationships(relationships, business, filing)
    assert err == []
    session.commit()

    # Business should only have Director
    business_roles = [r.role for r in business.party_roles.all()]
    assert business_roles == [PartyRole.RoleTypes.DIRECTOR.value]

    # Filing should have Completing Party, Incorporator, Applicant
    filing_roles = [r.role for r in filing.filing_party_roles.all()]
    assert len(filing_roles) == 3
    assert set(filing_roles) == {
        PartyRole.RoleTypes.COMPLETING_PARTY.value,
        PartyRole.RoleTypes.INCORPORATOR.value,
        PartyRole.RoleTypes.APPLICANT.value
    }


def test_create_relationships_add_new_role_to_existing_party(app, session, business, filing):
    """Test adding a new role to an existing party for the business."""
    existing_party = Party(first_name='JIM', last_name='HALPERT')
    existing_party.save()
    existing_role = PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        party_id=existing_party.id,
        business_id=business.id,
        appointment_date=datetime(2020, 1, 1, tzinfo=timezone.utc)
    )
    existing_role.save()
    session.commit()

    # Add CEO role to the same party
    relationships = [
        {
            'entity': {
                'identifier': str(existing_party.id),
                'givenName': 'Jim',
                'familyName': 'Halpert'
            },
            'roles': [{'roleType': 'CEO'}]
        }
    ]

    err = create_relationships(relationships, business, filing)
    assert err == []
    session.commit()

    roles = PartyRole.get_party_roles_by_party_id(business.id, existing_party.id)
    assert len(roles) == 2
    role_names = {r.role for r in roles}
    assert role_names == {PartyRole.RoleTypes.DIRECTOR.value, PartyRole.RoleTypes.CEO.value}


def test_create_relationships_deduplication_active_role(app, session, business, filing):
    """Test that duplicate active roles are not created for the same party."""
    party = Party(first_name='PAM', last_name='BEESLY')
    party.save()
    PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        party_id=party.id,
        business_id=business.id,
        appointment_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
        cessation_date=None
    ).save()
    session.commit()

    # Attempt to add Director role again
    relationships = [
        {
            'entity': {'identifier': str(party.id), 'givenName': 'Pam', 'familyName': 'Beesly'},
            'roles': [{'roleType': 'Director'}]
        }
    ]

    err = create_relationships(relationships, business, filing)
    assert err == []
    session.commit()

    roles = PartyRole.get_party_roles_by_party_id(business.id, party.id)
    assert len(roles) == 1


def test_create_relationships_reappoint_ceased_role(app, session, business, filing):
    """Test that a role can be created if the previous role of that type has ceased."""
    party = Party(first_name='ANDY', last_name='BERNARD')
    party.save()
    PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        party_id=party.id,
        business_id=business.id,
        appointment_date=datetime(2019, 1, 1, tzinfo=timezone.utc),
        cessation_date=datetime(2021, 1, 1, tzinfo=timezone.utc)
    ).save()
    session.commit()

    # Re-appoint Andy Bernard as Director
    relationships = [
        {
            'entity': {'identifier': str(party.id), 'givenName': 'Andy', 'familyName': 'Bernard'},
            'roles': [{'roleType': 'Director'}]
        }
    ]

    err = create_relationships(relationships, business, filing)
    assert err == []
    session.commit()

    roles = PartyRole.get_party_roles_by_party_id(business.id, party.id)
    assert len(roles) == 2
    active_roles = [r for r in roles if r.cessation_date is None]
    assert len(active_roles) == 1
    assert active_roles[0].appointment_date == filing.effective_date


def test_create_relationships_ignore_role_with_cessation_date(app, session, business, filing):
    """Test that roles with a cessationDate in relationship_info are ignored by create_relationships."""
    relationships = [
        {
            'entity': {'givenName': 'Kevin', 'familyName': 'Malone'},
            'roles': [
                {'roleType': 'Director', 'cessationDate': '2023-01-01'}
            ]
        }
    ]

    err = create_relationships(relationships, business, filing)
    assert err == []
    session.commit()

    roles = business.party_roles.all()
    assert len(roles) == 0


def test_create_relationships_existing_party_id_no_roles_on_this_business(app, session, business, filing):
    """Edge case: party_id points to a party in DB, but with no party_roles on this business.
    create_relationships ignores the update.
    """
    other_business = create_business('BC9999991', legal_type='BEN')
    foreign_party = Party(first_name='STANLEY', last_name='HUDSON')
    foreign_party.save()
    PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        party_id=foreign_party.id,
        business_id=other_business.id
    ).save()
    session.commit()

    relationships = [
        {
            'entity': {
                'identifier': str(foreign_party.id),
                'givenName': 'Stanley',
                'familyName': 'Hudson'
            },
            'roles': [{'roleType': 'Director'}]
        }
    ]

    err = create_relationships(relationships, business, filing)
    assert err == []
    session.commit()

    # Should not have added any roles for this business
    roles = PartyRole.get_party_roles_by_party_id(business.id, foreign_party.id)
    assert len(roles) == 0


def test_create_relationships_unknown_party_id(app, session, business, filing):
    """Edge case: party_id provided does not exist in DB (e.g. 9999999).
    Since party_id is an existing identifier that is not found, the update is ignored
    and no party or party role records are created.
    """
    relationships = [
        {
            'entity': {
                'identifier': '9999999',
                'givenName': 'Oscar',
                'familyName': 'Martinez'
            },
            'roles': [{'roleType': 'Director'}]
        }
    ]

    err = create_relationships(relationships, business, filing)
    assert err == []
    session.commit()

    roles = business.party_roles.all()
    assert len(roles) == 0

    # Ensure no orphaned party record was created in the database
    party = Party.query.filter_by(first_name='OSCAR', last_name='MARTINEZ').first()
    assert party is None


def test_create_relationships_with_role_class(app, session, business, filing):
    """Test role_class parameter propagates to party_class_type."""
    relationships = [
        {
            'entity': {'givenName': 'Michael', 'familyName': 'Scott'},
            'roles': [{'roleType': 'CEO'}]
        }
    ]

    err = create_relationships(relationships, business, filing, role_class=PartyClassType.OFFICER)
    assert err == []
    session.commit()

    role = business.party_roles.all()[0]
    assert role.party_class_type == PartyClassType.OFFICER


def test_cease_relationships_standard(app, session, business):
    """Test standard cessation of an active role."""
    party = Party(first_name='ANGELA', last_name='MARTIN')
    party.save()
    role = PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        party_id=party.id,
        business_id=business.id,
        appointment_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
        cessation_date=None
    )
    role.save()
    session.commit()

    cease_dt = datetime(2023, 7, 1, 10, 0, 0, tzinfo=timezone.utc)
    relationships = [
        {
            'entity': {'identifier': str(party.id)},
            'roles': [{'roleType': 'Director', 'cessationDate': '2023-07-01'}]
        }
    ]

    cease_relationships(
        relationships=relationships,
        business=business,
        allowed_roles=[PartyRole.RoleTypes.DIRECTOR.value],
        date_time=cease_dt
    )
    session.commit()

    updated_role = PartyRole.find_by_internal_id(role.id)
    assert updated_role.cessation_date == cease_dt


def test_cease_relationships_default_date_time(app, session, business):
    """Test cease_relationships defaults to current UTC datetime when date_time is None."""
    party = Party(first_name='KELLY', last_name='KAPOOR')
    party.save()
    role = PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        party_id=party.id,
        business_id=business.id,
        appointment_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
        cessation_date=None
    )
    role.save()
    session.commit()

    relationships = [
        {
            'entity': {'identifier': str(party.id)},
            'roles': [{'roleType': 'Director', 'cessationDate': '2023-07-01'}]
        }
    ]

    before = datetime.now(timezone.utc)
    cease_relationships(
        relationships=relationships,
        business=business,
        allowed_roles=[PartyRole.RoleTypes.DIRECTOR.value],
        date_time=None
    )
    after = datetime.now(timezone.utc)
    session.commit()

    updated_role = PartyRole.find_by_internal_id(role.id)
    assert updated_role.cessation_date is not None
    assert before <= updated_role.cessation_date <= after


def test_cease_relationships_not_in_allowed_roles(app, session, business):
    """Test that a role not in allowed_roles is not ceased even with cessationDate in payload."""
    party = Party(first_name='RYAN', last_name='HOWARD')
    party.save()
    dir_role = PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        party_id=party.id,
        business_id=business.id,
        appointment_date=datetime(2020, 1, 1, tzinfo=timezone.utc)
    )
    dir_role.save()
    ceo_role = PartyRole(
        role=PartyRole.RoleTypes.CEO.value,
        party_id=party.id,
        business_id=business.id,
        appointment_date=datetime(2020, 1, 1, tzinfo=timezone.utc)
    )
    ceo_role.save()
    session.commit()

    relationships = [
        {
            'entity': {'identifier': str(party.id)},
            'roles': [
                {'roleType': 'Director', 'cessationDate': '2023-07-01'},
                {'roleType': 'CEO', 'cessationDate': '2023-07-01'}
            ]
        }
    ]

    # Only director is allowed to be ceased
    cease_relationships(
        relationships=relationships,
        business=business,
        allowed_roles=[PartyRole.RoleTypes.DIRECTOR.value],
        date_time=datetime(2023, 7, 1, tzinfo=timezone.utc)
    )
    session.commit()

    assert PartyRole.find_by_internal_id(dir_role.id).cessation_date is not None
    assert PartyRole.find_by_internal_id(ceo_role.id).cessation_date is None


def test_cease_relationships_already_ceased_unaffected(app, session, business):
    """Test that an already ceased role does not have its cessation_date overwritten."""
    party = Party(first_name='CREED', last_name='BRATTON')
    party.save()
    original_cease_dt = datetime(2021, 5, 1, tzinfo=timezone.utc)
    role = PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        party_id=party.id,
        business_id=business.id,
        appointment_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
        cessation_date=original_cease_dt
    )
    role.save()
    session.commit()

    new_cease_dt = datetime(2023, 10, 1, tzinfo=timezone.utc)
    relationships = [
        {
            'entity': {'identifier': str(party.id)},
            'roles': [{'roleType': 'Director', 'cessationDate': '2023-10-01'}]
        }
    ]

    cease_relationships(
        relationships=relationships,
        business=business,
        allowed_roles=[PartyRole.RoleTypes.DIRECTOR.value],
        date_time=new_cease_dt
    )
    session.commit()

    # Original cessation date must be preserved
    assert PartyRole.find_by_internal_id(role.id).cessation_date == original_cease_dt


def test_cease_relationships_no_cessation_date_in_payload(app, session, business):
    """Test that role is not ceased if cessationDate is None or missing in payload."""
    party = Party(first_name='MEREDITH', last_name='PALMER')
    party.save()
    role = PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        party_id=party.id,
        business_id=business.id,
        appointment_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
        cessation_date=None
    )
    role.save()
    session.commit()

    relationships = [
        {
            'entity': {'identifier': str(party.id)},
            'roles': [{'roleType': 'Director', 'cessationDate': None}]
        }
    ]

    cease_relationships(
        relationships=relationships,
        business=business,
        allowed_roles=[PartyRole.RoleTypes.DIRECTOR.value]
    )
    session.commit()

    assert PartyRole.find_by_internal_id(role.id).cessation_date is None


def test_cease_relationships_missing_or_invalid_identifier(app, session, business):
    """Test relationships missing identifier or with non-numeric identifier are ignored safely."""
    party = Party(first_name='TOBY', last_name='FLENDERSON')
    party.save()
    role = PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        party_id=party.id,
        business_id=business.id,
        appointment_date=datetime(2020, 1, 1, tzinfo=timezone.utc)
    )
    role.save()
    session.commit()

    relationships = [
        {
            'entity': {'givenName': 'Toby'},  # No identifier
            'roles': [{'roleType': 'Director', 'cessationDate': '2023-01-01'}]
        },
        {
            'entity': {'identifier': 'not-a-number'},
            'roles': [{'roleType': 'Director', 'cessationDate': '2023-01-01'}]
        }
    ]

    cease_relationships(
        relationships=relationships,
        business=business,
        allowed_roles=[PartyRole.RoleTypes.DIRECTOR.value]
    )
    session.commit()

    assert PartyRole.find_by_internal_id(role.id).cessation_date is None


def test_update_relationships_appointment_date_success(app, session, business):
    """Test updating the appointment date on an existing role."""
    party = Party(first_name='DARRYL', last_name='PHILBIN')
    party.save()
    role = PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        party_id=party.id,
        business_id=business.id,
        appointment_date=datetime(2020, 1, 1, tzinfo=timezone.utc)
    )
    role.save()
    session.commit()

    new_appt_date = datetime(2018, 5, 20, 0, 0, 0, tzinfo=timezone.utc)
    relationships = [
        {
            'entity': {'identifier': str(party.id)},
            'roles': [{'roleType': 'Director', 'appointmentDate': new_appt_date}]
        }
    ]

    update_relationships_appointment_date(
        relationships=relationships,
        business=business,
        allowed_roles=[PartyRole.RoleTypes.DIRECTOR.value]
    )
    session.commit()

    assert PartyRole.find_by_internal_id(role.id).appointment_date == new_appt_date


def test_update_relationships_appointment_date_role_not_allowed(app, session, business):
    """Test that appointment date is not updated if role is not in allowed_roles."""
    party = Party(first_name='ROY', last_name='ANDERSON')
    party.save()
    role = PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        party_id=party.id,
        business_id=business.id,
        appointment_date=datetime(2020, 1, 1, tzinfo=timezone.utc)
    )
    role.save()
    session.commit()

    relationships = [
        {
            'entity': {'identifier': str(party.id)},
            'roles': [{'roleType': 'Director', 'appointmentDate': datetime(2018, 5, 20, tzinfo=timezone.utc)}]
        }
    ]

    update_relationships_appointment_date(
        relationships=relationships,
        business=business,
        allowed_roles=[PartyRole.RoleTypes.CEO.value]  # CEO not allowed
    )
    session.commit()

    assert PartyRole.find_by_internal_id(role.id).appointment_date == datetime(2020, 1, 1, tzinfo=timezone.utc)


def test_update_relationships_appointment_date_missing_identifier(app, session, business):
    """Test relationships with missing identifier are safely skipped."""
    relationships = [
        {
            'entity': {'givenName': 'NoId'},
            'roles': [{'roleType': 'Director', 'appointmentDate': datetime(2020, 1, 1, tzinfo=timezone.utc)}]
        }
    ]
    # Should not raise exception
    update_relationships_appointment_date(relationships, business, [PartyRole.RoleTypes.DIRECTOR.value])


def test_update_relationships_cessation_date_success(app, session, business):
    """Test updating the cessation date on an existing role."""
    party = Party(first_name='JAN', last_name='LEVINSON')
    party.save()
    role = PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        party_id=party.id,
        business_id=business.id,
        appointment_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
        cessation_date=datetime(2022, 1, 1, tzinfo=timezone.utc)
    )
    role.save()
    session.commit()

    new_cessation_date = datetime(2023, 11, 30, 0, 0, 0, tzinfo=timezone.utc)
    relationships = [
        {
            'entity': {'identifier': str(party.id)},
            'roles': [{'roleType': 'Director', 'cessationDate': new_cessation_date}]
        }
    ]

    update_relationships_cessation_date(
        relationships=relationships,
        business=business,
        allowed_roles=[PartyRole.RoleTypes.DIRECTOR.value]
    )
    session.commit()

    assert PartyRole.find_by_internal_id(role.id).cessation_date == new_cessation_date


def test_update_relationships_cessation_date_role_not_allowed(app, session, business):
    """Test cessation date is not updated if role is not in allowed_roles."""
    party = Party(first_name='DAVID', last_name='WALLACE')
    party.save()
    role = PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        party_id=party.id,
        business_id=business.id,
        appointment_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
        cessation_date=datetime(2022, 1, 1, tzinfo=timezone.utc)
    )
    role.save()
    session.commit()

    relationships = [
        {
            'entity': {'identifier': str(party.id)},
            'roles': [{'roleType': 'Director', 'cessationDate': datetime(2023, 1, 1, tzinfo=timezone.utc)}]
        }
    ]

    update_relationships_cessation_date(
        relationships=relationships,
        business=business,
        allowed_roles=[PartyRole.RoleTypes.OFFICER.value]
    )
    session.commit()

    assert PartyRole.find_by_internal_id(role.id).cessation_date == datetime(2022, 1, 1, tzinfo=timezone.utc)


def test_update_relationships_cessation_date_missing_identifier(app, session, business):
    """Test relationships missing identifier are skipped safely."""
    relationships = [{'entity': {'givenName': 'Nobody'}, 'roles': [{'roleType': 'Director'}]}]
    update_relationships_cessation_date(relationships, business, [PartyRole.RoleTypes.DIRECTOR.value])


def test_update_relationship_addresses_create_when_none_exist(app, session, business):
    """Test creating addresses when the party previously had none."""
    party = Party(first_name='MOSE', last_name='SCHRUTE')
    party.save()
    PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        party_id=party.id,
        business_id=business.id
    ).save()
    session.commit()

    assert party.delivery_address is None
    assert party.mailing_address is None

    relationships = [
        {
            'entity': {'identifier': str(party.id)},
            'deliveryAddress': copy.deepcopy(DELIVERY_ADDRESS),
            'mailingAddress': copy.deepcopy(MAILING_ADDRESS)
        }
    ]

    update_relationship_addresses(relationships, business)
    session.commit()

    updated_party = Party.find_by_id(party.id)
    assert updated_party.delivery_address is not None
    assert updated_party.delivery_address.street == DELIVERY_ADDRESS['streetAddress']
    assert updated_party.delivery_address.address_type == Address.DELIVERY

    assert updated_party.mailing_address is not None
    assert updated_party.mailing_address.street == MAILING_ADDRESS['streetAddress']
    assert updated_party.mailing_address.address_type == Address.MAILING


def test_update_relationship_addresses_update_existing(app, session, business):
    """Test updating existing delivery and mailing addresses in-place."""
    party = Party(first_name='PHYLLIS', last_name='LAPIN')
    party.delivery_address = create_address(DELIVERY_ADDRESS, Address.DELIVERY)
    party.mailing_address = create_address(MAILING_ADDRESS, Address.MAILING)
    party.save()
    PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        party_id=party.id,
        business_id=business.id
    ).save()
    session.commit()

    original_delivery_id = party.delivery_address.id
    original_mailing_id = party.mailing_address.id

    new_delivery = copy.deepcopy(DELIVERY_ADDRESS)
    new_delivery['streetAddress'] = '999 New Delivery Blvd'
    new_mailing = copy.deepcopy(MAILING_ADDRESS)
    new_mailing['streetAddress'] = '888 New Mailing Way'

    relationships = [
        {
            'entity': {'identifier': str(party.id)},
            'deliveryAddress': new_delivery,
            'mailingAddress': new_mailing
        }
    ]

    update_relationship_addresses(relationships, business)
    session.commit()

    updated_party = Party.find_by_id(party.id)
    assert updated_party.delivery_address.id == original_delivery_id
    assert updated_party.delivery_address.street == '999 New Delivery Blvd'

    assert updated_party.mailing_address.id == original_mailing_id
    assert updated_party.mailing_address.street == '888 New Mailing Way'


def test_update_relationship_addresses_partial_updates(app, session, business):
    """Test partial update: only deliveryAddress or only mailingAddress updated."""
    party = Party(first_name='HOLLY', last_name='FLAX')
    party.delivery_address = create_address(DELIVERY_ADDRESS, Address.DELIVERY)
    party.mailing_address = create_address(MAILING_ADDRESS, Address.MAILING)
    party.save()
    PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        party_id=party.id,
        business_id=business.id
    ).save()
    session.commit()

    # 1. Only update delivery address (mailingAddress omitted)
    new_delivery = copy.deepcopy(DELIVERY_ADDRESS)
    new_delivery['streetAddress'] = '777 Solitary Way'
    relationships = [
        {
            'entity': {'identifier': str(party.id)},
            'deliveryAddress': new_delivery
        }
    ]

    update_relationship_addresses(relationships, business)
    session.commit()

    updated_party = Party.find_by_id(party.id)
    assert updated_party.delivery_address.street == '777 Solitary Way'
    assert updated_party.mailing_address.street == MAILING_ADDRESS['streetAddress']

    # 2. Only update mailing address (deliveryAddress omitted)
    new_mailing = copy.deepcopy(MAILING_ADDRESS)
    new_mailing['streetAddress'] = '555 New Mailing Rd'
    relationships_mailing_only = [
        {
            'entity': {'identifier': str(party.id)},
            'mailingAddress': new_mailing
        }
    ]

    update_relationship_addresses(relationships_mailing_only, business)
    session.commit()

    updated_party = Party.find_by_id(party.id)
    assert updated_party.delivery_address.street == '777 Solitary Way'
    assert updated_party.mailing_address.street == '555 New Mailing Rd'


def test_update_relationship_addresses_skip_unrelated_party(app, session, business):
    """Edge case: party exists in DB but has no roles on the provided business."""
    other_business = create_business('BC9999992', legal_type='BEN')
    party = Party(first_name='KAREN', last_name='FILIPPELLI')
    party.delivery_address = create_address(DELIVERY_ADDRESS, Address.DELIVERY)
    party.save()
    PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        party_id=party.id,
        business_id=other_business.id
    ).save()
    session.commit()

    new_delivery = copy.deepcopy(DELIVERY_ADDRESS)
    new_delivery['streetAddress'] = '111 Utica St'
    relationships = [
        {
            'entity': {'identifier': str(party.id)},
            'deliveryAddress': new_delivery
        }
    ]

    # Call with business (not other_business)
    update_relationship_addresses(relationships, business)
    session.commit()

    # Address must NOT be updated
    assert Party.find_by_id(party.id).delivery_address.street == DELIVERY_ADDRESS['streetAddress']


def test_update_relationship_addresses_invalid_identifiers(app, session, business):
    """Test that missing or invalid party identifier strings are skipped without error."""
    relationships = [
        {'entity': {}, 'deliveryAddress': copy.deepcopy(DELIVERY_ADDRESS)},
        {'entity': {'identifier': None}, 'deliveryAddress': copy.deepcopy(DELIVERY_ADDRESS)},
        {'entity': {'identifier': 'abc'}, 'deliveryAddress': copy.deepcopy(DELIVERY_ADDRESS)},
        {'entity': {'identifier': '9999999'}, 'deliveryAddress': copy.deepcopy(DELIVERY_ADDRESS)},
    ]
    # None of these should raise an exception
    update_relationship_addresses(relationships, business)


def test_update_relationship_entity_info_person(app, session, business):
    """Test updating all personal details for an existing person party."""
    party = Party(
        first_name='CHARLES',
        last_name='MINER',
        party_type=Party.PartyTypes.PERSON.value
    )
    party.save()
    PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        party_id=party.id,
        business_id=business.id
    ).save()
    session.commit()

    relationships = [
        {
            'entity': {
                'identifier': str(party.id),
                'givenName': '  Charlie  ',
                'familyName': 'Miner-Smith',
                'middleInitial': '  e  ',
                'alternateName': 'Chuck',
                'email': 'charles@saticoy.com',
                'businessIdentifier': 'B-1234'
            }
        }
    ]

    update_relationship_entity_info(relationships, business)
    session.commit()

    updated = Party.find_by_id(party.id)
    assert updated.first_name == 'CHARLIE'
    assert updated.last_name == 'MINER-SMITH'
    assert updated.middle_initial == 'E'
    assert updated.alternate_name == 'CHUCK'
    assert updated.email == 'CHARLES@SATICOY.COM'
    assert updated.identifier == 'B-1234'
    assert updated.party_type == Party.PartyTypes.PERSON.value
    assert updated.organization_name is None


def test_update_relationship_entity_info_switch_person_to_organization(app, session, business):
    """Test converting a person party to an organization party by adding businessName."""
    party = Party(
        first_name='ROBERT',
        last_name='CALIFORNIA',
        party_type=Party.PartyTypes.PERSON.value
    )
    party.save()
    PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        party_id=party.id,
        business_id=business.id
    ).save()
    session.commit()

    relationships = [
        {
            'entity': {
                'identifier': str(party.id),
                'businessName': 'Sabre International',
                'businessIdentifier': 'BC8888888',
                'email': 'ceo@sabre.com'
            }
        }
    ]

    update_relationship_entity_info(relationships, business)
    session.commit()

    updated = Party.find_by_id(party.id)
    assert updated.party_type == Party.PartyTypes.ORGANIZATION.value
    assert updated.organization_name == 'SABRE INTERNATIONAL'
    assert updated.first_name is None
    assert updated.last_name is None
    assert updated.email == 'CEO@SABRE.COM'
    assert updated.identifier == 'BC8888888'


def test_update_relationship_entity_info_switch_organization_to_person(app, session, business):
    """Test converting an organization party to a person party by removing businessName."""
    party = Party(
        organization_name='OLD HOLDINGS INC.',
        party_type=Party.PartyTypes.ORGANIZATION.value
    )
    party.save()
    PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        party_id=party.id,
        business_id=business.id
    ).save()
    session.commit()

    relationships = [
        {
            'entity': {
                'identifier': str(party.id),
                'givenName': 'Gabe',
                'familyName': 'Lewis',
                'businessName': None
            }
        }
    ]

    update_relationship_entity_info(relationships, business)
    session.commit()

    updated = Party.find_by_id(party.id)
    assert updated.party_type == Party.PartyTypes.PERSON.value
    assert updated.organization_name is None
    assert updated.first_name == 'GABE'
    assert updated.last_name == 'LEWIS'


def test_update_relationship_entity_info_skip_unrelated_party(app, session, business):
    """Edge case: party has no roles on the specified business -> info not updated."""
    other_business = create_business('BC9999993', legal_type='BEN')
    party = Party(first_name='NELLY', last_name='BERTRAM')
    party.save()
    PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        party_id=party.id,
        business_id=other_business.id
    ).save()
    session.commit()

    relationships = [
        {
            'entity': {
                'identifier': str(party.id),
                'givenName': 'ChangedName'
            }
        }
    ]

    update_relationship_entity_info(relationships, business)
    session.commit()

    assert Party.find_by_id(party.id).first_name == 'NELLY'

