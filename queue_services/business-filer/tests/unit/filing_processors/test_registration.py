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
"""The Unit Tests for the Registration filing."""

import copy
from datetime import datetime, timezone
from http import HTTPStatus
from unittest.mock import patch, call

import pytest
from business_model.models import Business, Filing, RegistrationBootstrap
from business_filer.common.services import NaicsService
from business_filer.common.services.naics import NaicsService
from business_filer.common.services.account_service import AccountService
from registry_schemas.example_data import (
    FILING_HEADER,
    REGISTRATION
)

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors import registration
from business_filer.filing_processors.filing_components import business_profile
from tests.unit import create_filing


now = '2023-01-08'

GP_REGISTRATION = copy.deepcopy(FILING_HEADER)
GP_REGISTRATION['filing']['header']['name'] = 'registration'
GP_REGISTRATION['filing']['registration'] = copy.deepcopy(REGISTRATION)
GP_REGISTRATION['filing']['registration']['startDate'] = now

SP_REGISTRATION = copy.deepcopy(FILING_HEADER)
SP_REGISTRATION['filing']['header']['name'] = 'registration'
SP_REGISTRATION['filing']['registration'] = copy.deepcopy(REGISTRATION)
SP_REGISTRATION['filing']['registration']['startDate'] = now
SP_REGISTRATION['filing']['registration']['nameRequest']['legalType'] = 'SP'
SP_REGISTRATION['filing']['registration']['businessType'] = 'SP'
SP_REGISTRATION['filing']['registration']['parties'][0]['roles'] = [
    {
        'roleType': 'Completing Party',
        'appointmentDate': '2022-01-01'

    },
    {
        'roleType': 'Proprietor',
        'appointmentDate': '2022-01-01'

    }
]
del SP_REGISTRATION['filing']['registration']['parties'][1]


@pytest.mark.parametrize('legal_type,filing', [
    ('SP', copy.deepcopy(SP_REGISTRATION)),
    ('GP', copy.deepcopy(GP_REGISTRATION)),
])
def test_registration_process(app, session, legal_type, filing):
    """Assert that the registration object is correctly populated to model objects."""
    # setup
    identifier = 'NR 1234567'
    filing['filing']['registration']['nameRequest']['nrNumber'] = identifier
    filing['filing']['registration']['nameRequest']['legalName'] = 'Test'
    create_filing('123', filing)

    effective_date = datetime.now(timezone.utc)
    filing_rec = Filing(effective_date=effective_date, filing_json=filing)
    filing_meta = FilingMeta(application_date=effective_date)

    naics_response = {
        'code': REGISTRATION['business']['naics']['naicsCode'],
        'naicsKey': 'a4667c26-d639-42fa-8af3-7ec73e392569'
    }

    # test
    with patch.object(NaicsService, 'find_by_code', return_value=naics_response):
        business, filing_rec, filing_meta = registration.process(None, filing, filing_rec, filing_meta, None)

    # Assertions
    assert business.identifier.startswith('FM')
    assert business.founding_date == effective_date
    assert business.start_date == datetime.fromisoformat(f'{now}T08:00:00+00:00')
    assert business.legal_type == filing['filing']['registration']['nameRequest']['legalType']
    assert business.legal_name == filing['filing']['registration']['nameRequest']['legalName']
    assert business.naics_code == REGISTRATION['business']['naics']['naicsCode']
    assert business.naics_description == REGISTRATION['business']['naics']['naicsDescription']
    assert business.naics_key == naics_response['naicsKey']
    assert business.tax_id == REGISTRATION['business']['taxId']
    assert business.state == Business.State.ACTIVE
    if legal_type == 'SP':
        assert len(filing_rec.filing_party_roles.all()) == 1
        assert len(business.party_roles.all()) == 1
    if legal_type == 'GP':
        assert len(filing_rec.filing_party_roles.all()) == 1
        assert len(business.party_roles.all()) == 2
    assert len(business.offices.all()) == 1
    assert business.offices[0].office_type == 'businessOffice'


@pytest.mark.parametrize(
    'legal_type, filing, party_type, organization_name, first_name, last_name, middle_name, expected_pass_code',
    [
        ('SP', copy.deepcopy(SP_REGISTRATION), 'person', '', 'Jane', 'Doe', '', 'DOE, JANE'),
        ('SP', copy.deepcopy(SP_REGISTRATION), 'person', '', 'Jane', 'Doe', 'XYZ', 'DOE, JANE XYZ'),
        ('SP', copy.deepcopy(SP_REGISTRATION), 'organization', 'xyz org name', '', '', '', 'XYZ ORG NAME'),
        ('GP', copy.deepcopy(GP_REGISTRATION), 'person', '', 'Jane', 'Doe', '', 'DOE, JANE'),
        ('GP', copy.deepcopy(GP_REGISTRATION), 'person', '', 'Jane', 'Doe', 'XYZ', 'DOE, JANE XYZ'),
        ('GP', copy.deepcopy(GP_REGISTRATION), 'organization', 'xyz org name', '', '', '', 'XYZ ORG NAME')
    ])
def test_registration_affiliation(app, session, legal_type, filing, party_type, organization_name, first_name,
                                  last_name, middle_name, expected_pass_code):
    """Assert affiliation of a firm calls expected auth api endpoints and with expected parameter values."""

    # setup
    bootstrap = RegistrationBootstrap(account=1111111, _identifier='TNpUnst/Va')
    identifier = 'NR 1234567'
    org_party_tax_id = '123456789'
    org_party_identifier = 'BC1011333'
    filing['filing']['registration']['nameRequest']['nrNumber'] = identifier
    filing['filing']['registration']['nameRequest']['legalName'] = 'Test'
    filing['filing']['registration']['parties'][0]['officer']['partyType'] = party_type
    filing['filing']['registration']['parties'][0]['officer']['organizationName'] = organization_name
    filing['filing']['registration']['parties'][0]['officer']['firstName'] = first_name
    filing['filing']['registration']['parties'][0]['officer']['lastName'] = last_name
    filing['filing']['registration']['parties'][0]['officer']['middleName'] = middle_name

    create_filing('123', filing)

    effective_date = datetime.utcnow()
    filing_rec = Filing(effective_date=effective_date, filing_json=filing)
    filing_meta = FilingMeta(application_date=effective_date)

    naics_response = {
        'code': REGISTRATION['business']['naics']['naicsCode'],
        'naicsKey': 'a4667c26-d639-42fa-8af3-7ec73e392569'
    }

    # create business and filing records
    # TODO: Fix this
    with patch.object(NaicsService, 'find_by_code', return_value=naics_response):
        business, filing_rec, filing_meta = registration.process(None, filing, filing_rec, filing_meta, None)
        business.save()
        filing_rec.save()

    # test
    details = {
        'bootstrapIdentifier': bootstrap.identifier,
        'identifier': business.identifier,
        'nrNumber': identifier
    }

    with patch.object(AccountService, 'create_affiliation', return_value=HTTPStatus.OK):
        with patch.object(AccountService, 'delete_affiliation', return_value=HTTPStatus.OK):
            with patch.object(AccountService, 'update_entity', return_value=HTTPStatus.OK):
                with patch.object(RegistrationBootstrap, 'find_by_identifier', return_value=bootstrap):
                    business_profile.update_affiliation(business, filing_rec)
                    assert AccountService.create_affiliation.call_count == 1
                    assert AccountService.delete_affiliation.call_count == 0
                    assert AccountService.update_entity.call_count == 1

                    first_affiliation_call_args = AccountService.create_affiliation.call_args_list[0]
                    expected_affiliation_call_args = call(account=1111111,
                                                          business_registration=business.identifier,
                                                          business_name=business.legal_name,
                                                          corp_type_code=legal_type,
                                                          pass_code=expected_pass_code,
                                                          details=details,
                                                          flags=None)
                    assert first_affiliation_call_args == expected_affiliation_call_args

                    first_update_entity_call_args = AccountService.update_entity.call_args_list[0]
                    expected_update_entity_call_args = call(business_registration=bootstrap.identifier,
                                                            business_name=business.identifier,
                                                            corp_type_code='RTMP')
                    assert first_update_entity_call_args == expected_update_entity_call_args
