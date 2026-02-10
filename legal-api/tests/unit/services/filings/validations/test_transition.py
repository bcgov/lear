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
"""Test Post Restoration Transtion Application validation."""
import copy
from datetime import date

import datedelta
import pytest
from registry_schemas.example_data import TRANSITION_FILING_TEMPLATE

from legal_api.models import Address, Business, PartyRole
from legal_api.services.filings.validations.transition import validate
from tests.unit.models import factory_business, factory_party_role
from tests.unit.services.warnings import factory_address
from .test_common_validations import INVALID_ADDRESS_NO_POSTAL_CODE, VALID_ADDRESS_BC, VALID_OFFICE, VALID_OFFICE_EX_CA


VALID_OFFICES = {'registeredOffice': VALID_OFFICE,'recordsOffice': VALID_OFFICE}
INVALID_OFFICES_EX_CA = {'registeredOffice': VALID_OFFICE_EX_CA, 'recordsOffice': VALID_OFFICE_EX_CA}
INVALID_OFFICES_NO_REGISTERED = {'recordsOffice': VALID_OFFICE}
INVALID_OFFICES_NO_RECORDS = {'registeredOffice': VALID_OFFICE}

VALID_RELATIONSHIP = {'has_existing_id': True, 'valid_id': True, 'valid_address': True}
INVALID_RELATIONSHIP_NEW = {'has_existing_id': False, 'valid_id': False, 'valid_address': True}
INVALID_RELATIONSHIP_ID_MATCH = {'has_existing_id': True, 'valid_id': False, 'valid_address': True}
INVALID_RELATIONSHIP_ADDRESS = {'has_existing_id': True, 'valid_id': True, 'valid_address': False}

VALID_SHARE = {'has_rights_restrictions': False, 'has_series': False}
VALID_SHARE_SERIES = {'has_rights_restrictions': True, 'has_series': True}
INVALID_SHARE_SERIES = {'has_rights_restrictions': False, 'has_series': True}


@pytest.mark.parametrize('test_name, offices, relationship, share, expected_errs', [
    ('Valid', VALID_OFFICES, VALID_RELATIONSHIP, VALID_SHARE, None),
    ('Valid_series', VALID_OFFICES, VALID_RELATIONSHIP, VALID_SHARE_SERIES, None),
    ('Invalid_office_ex_ca',
     INVALID_OFFICES_EX_CA,
     VALID_RELATIONSHIP,
     VALID_SHARE,
     [{'error': "Address Region must be 'BC'.", 'path': '/filing/transition/offices/registeredOffice'},
      {'error': "Address Country must be 'CA'.", 'path': '/filing/transition/offices/registeredOffice'},
      {'error': "Address Region must be 'BC'.", 'path': '/filing/transition/offices/recordsOffice'},
      {'error': "Address Country must be 'CA'.", 'path': '/filing/transition/offices/recordsOffice'}]),
    ('Invalid_office_no_registered',
     INVALID_OFFICES_NO_REGISTERED,
     VALID_RELATIONSHIP,
     VALID_SHARE,
     [{'error': "Missing required offices ['registeredOffice'].", 'path': '/filing/transition/offices'}]),
    ('Invalid_office_no_records',
     INVALID_OFFICES_NO_RECORDS,
     VALID_RELATIONSHIP,
     VALID_SHARE,
     [{'error': "Missing required offices ['recordsOffice'].", 'path': '/filing/transition/offices'}]),
    ('Invalid_relationship_new',
     VALID_OFFICES,
     INVALID_RELATIONSHIP_NEW,
     VALID_SHARE,
     [{'error': 'New Relationships are not allowed in this filing.', 'path': '/filing/transition/relationships/0/entity'}]),
    ('Invalid_relationship_wrong_id',
     VALID_OFFICES,
     INVALID_RELATIONSHIP_ID_MATCH,
     VALID_SHARE,
     [{'error': 'Relationship with this identifier is not valid for this filing.', 'path': '/filing/transition/relationships/0/entity/identifier'}]),
    ('Invalid_relationship_address',
     VALID_OFFICES,
     INVALID_RELATIONSHIP_ADDRESS,
     VALID_SHARE,
     [{'error': 'Postal code is required.', 'path': '/filing/transition/relationships/0/deliveryAddress/postalCode'}]),
    ('Invalid_shares_series',
     VALID_OFFICES,
     VALID_RELATIONSHIP,
     INVALID_SHARE_SERIES,
     [{'error': 'Share class Class 1 Shares cannot have series when hasRightsOrRestrictions is false', 'path': '/filing/transition/shareClasses/0/series/'}]),
])
def test_validate_transition(session, test_name, offices, relationship, share, expected_errs):
    """Assert that a transition application can be validated."""
    # setup
    now = date.today()
    identifier = 'BC1234567'
    founding_date = now - datedelta.YEAR
    business: Business = factory_business(identifier, founding_date, founding_date, Business.LegalTypes.COMP)

    filing = copy.deepcopy(TRANSITION_FILING_TEMPLATE)
    filing['filing']['business']['identifier'] = identifier
    transition = filing['filing']['transition']

    transition['offices'] = offices

    filing_relationship = transition['relationships'][0]
    if relationship['valid_address']:
        filing_relationship['deliveryAddress'] = VALID_ADDRESS_BC
        filing_relationship['mailingAddress'] = VALID_ADDRESS_BC
    else:
        filing_relationship['deliveryAddress'] = INVALID_ADDRESS_NO_POSTAL_CODE
        filing_relationship['mailingAddress'] = VALID_ADDRESS_BC

    print(relationship)
    if relationship['has_existing_id']:
        officer_dict = {
            'firstName': 'Test',
            'lastName': 'Tester',
            'middleInitial': '',
            'partyType': 'person',
            'organizationName': ''
        }
        role: PartyRole = factory_party_role(
            Address.create_address(VALID_ADDRESS_BC),
            Address.create_address(VALID_ADDRESS_BC),
            officer_dict,
            founding_date,
            None,
            PartyRole.RoleTypes.DIRECTOR)
        print(role)
        business.party_roles.append(role)
        business.save()
        print(business.party_roles)
        filing_relationship['entity']['identifier'] = str(role.id if relationship['valid_id'] else role.id + 1)
        print(role.id)
        print(filing_relationship['entity']['identifier'])

    transition['relationships'] = [filing_relationship]
    
    filing_share = transition['shareStructure']['shareClasses'][0]
    filing_share['hasRightsOrRestrictions'] = share['has_rights_restrictions']
    if share['has_series']:
        filing_share['series'] = [{
            'name': 'Series 1 Shares',
            'priority': 1,
            'hasMaximumShares': True,
            'maxNumberOfShares': 50,
            'hasRightsOrRestrictions': False,
        }]
    else:
        filing_share['series'] = []

    transition['shareStructure']['shareClasses'] = [filing_share]

    # perform test
    err = validate(business, filing)
    if err:
        print(test_name, err.msg)

    assert (not err and not expected_errs) or err.msg == expected_errs
