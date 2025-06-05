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
"""The Unit Tests for the Incorporation filing."""

import copy
import random
from datetime import datetime, timezone, timezone
from unittest.mock import patch

import pytest
from business_model.models import Business, Filing
from business_model.models.colin_event_id import ColinEventId
from business_model.models.document import DocumentType
from business_filer.services import Flags
# from legal_api.services import MinioService
from business_filer.services import AccountService
from registry_schemas.example_data import INCORPORATION_FILING_TEMPLATE

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors import incorporation_filing
from business_filer.filing_processors.filing_components import business_info
from tests.unit import create_filing
# from tests.utils import assert_pdf_contains_text, upload_file


COOP_INCORPORATION_FILING_TEMPLATE = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
del COOP_INCORPORATION_FILING_TEMPLATE['filing']['incorporationApplication']['offices']['recordsOffice']
del COOP_INCORPORATION_FILING_TEMPLATE['filing']['incorporationApplication']['parties'][1]
del COOP_INCORPORATION_FILING_TEMPLATE['filing']['incorporationApplication']['shareStructure']
del COOP_INCORPORATION_FILING_TEMPLATE['filing']['incorporationApplication']['incorporationAgreement']
COOP_INCORPORATION_FILING_TEMPLATE['filing']['incorporationApplication']['nameRequest']['legalType'] = 'CP'
COOP_INCORPORATION_FILING_TEMPLATE['filing']['incorporationApplication']['cooperative'] = {
    'cooperativeAssociationType': 'CP',
    'rulesFileKey': 'cooperative/fa00c6bf-eaad-4a07-a3d2-4786ecd6b83b.jpg',
    'memorandumFileKey': 'cooperative/f722bf16-86be-430d-928d-5529853a3a2c.pdf'
}

INCORPORATION_FILING_TEMPLATE = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
INCORPORATION_FILING_TEMPLATE['filing']['incorporationApplication']['courtOrder'] = \
    {
        'fileNumber': '12356',
        'effectOfOrder': 'planOfArrangement',
        'hasPlanOfArrangement': True
}


@pytest.mark.parametrize('legal_type, filing, next_corp_num ', [
    ('BC', copy.deepcopy(INCORPORATION_FILING_TEMPLATE), 'BC0001095'),
    ('BEN', copy.deepcopy(INCORPORATION_FILING_TEMPLATE), 'BC0001095'),
    ('CP', copy.deepcopy(COOP_INCORPORATION_FILING_TEMPLATE), 'CP0001095'),
    ('ULC', copy.deepcopy(INCORPORATION_FILING_TEMPLATE), 'BC0001095'),
    ('CC', copy.deepcopy(INCORPORATION_FILING_TEMPLATE), 'BC0001095'),
])
def test_incorporation_filing_process_with_nr(app, session, legal_type, filing, next_corp_num):
    """Assert that the incorporation object is correctly populated to model objects."""
    # setup
    with patch.object(business_info, 'get_next_corp_num', return_value=next_corp_num) as mock_get_next_corp_num:
        identifier = f'NR {random.randint(1000000, 9999999)}'
        filing['filing']['incorporationApplication']['nameRequest']['nrNumber'] = identifier
        filing['filing']['incorporationApplication']['nameRequest']['legalType'] = legal_type
        filing['filing']['incorporationApplication']['nameRequest']['legalName'] = 'Test'
        if legal_type not in ('CC', 'CP'):
            del filing['filing']['incorporationApplication']['courtOrder']
        create_filing('123', filing)

        effective_date = datetime.now(timezone.utc)
        filing_rec = Filing(effective_date=effective_date, filing_json=filing)
        filing_meta = FilingMeta(application_date=effective_date)

        # test
        business, filing_rec, filing_meta = incorporation_filing.process(None, filing, filing_rec, filing_meta, None)

        # Assertions
        assert business.identifier == next_corp_num
        assert business.founding_date == effective_date
        assert business.legal_type == filing['filing']['incorporationApplication']['nameRequest']['legalType']
        assert business.legal_name == filing['filing']['incorporationApplication']['nameRequest']['legalName']
        assert business.state == Business.State.ACTIVE
        assert len(business.party_roles.all()) == 1
        if legal_type in ('BC', 'BEN', 'ULC', 'CC'):
            assert len(filing_rec.filing_party_roles.all()) == 2
            assert len(business.share_classes.all()) == 2
            assert len(business.offices.all()) == 2  # One office is created in create_business method.
        if legal_type == 'CC':
            assert filing_rec.court_order_file_number == '12356'
            assert filing_rec.court_order_effect_of_order == 'planOfArrangement'
        if legal_type == 'CP':
            assert len(filing_rec.filing_party_roles.all()) == 1
            assert len(business.offices.all()) == 1

    mock_get_next_corp_num.assert_called_with(
        filing['filing']['incorporationApplication']['nameRequest']['legalType'], None)


@pytest.mark.parametrize('legal_type, filing, legal_name_suffix', [
    ('BC', copy.deepcopy(INCORPORATION_FILING_TEMPLATE), 'B.C. LTD.'),
    ('BEN', copy.deepcopy(INCORPORATION_FILING_TEMPLATE), 'B.C. LTD.'),
    ('ULC', copy.deepcopy(INCORPORATION_FILING_TEMPLATE), 'B.C. UNLIMITED LIABILITY COMPANY'),
    ('CC', copy.deepcopy(INCORPORATION_FILING_TEMPLATE), 'B.C. COMMUNITY CONTRIBUTION COMPANY LTD.'),
])
def test_incorporation_filing_process_no_nr(app, session, legal_type, filing, legal_name_suffix):
    """Assert that the incorporation object is correctly populated to model objects."""
    # setup
    next_corp_num = 'BC0001095'
    with patch.object(business_info, 'get_next_corp_num', return_value=next_corp_num) as mock_get_next_corp_num:
        filing['filing']['incorporationApplication']['nameRequest']['legalType'] = legal_type
        create_filing('123', filing)

        effective_date = datetime.now(timezone.utc)
        filing_rec = Filing(effective_date=effective_date, filing_json=filing)
        filing_meta = FilingMeta(application_date=filing_rec.effective_date)

        # test
        business, filing_rec, filing_meta = incorporation_filing.process(None, filing, filing_rec, filing_meta, None)

        # Assertions
        assert business.identifier == next_corp_num
        assert business.founding_date == effective_date
        assert business.legal_type == legal_type
        assert business.legal_name == f'{business.identifier[2:]} {legal_name_suffix}'
        assert len(business.share_classes.all()) == 2
        assert len(business.offices.all()) == 2  # One office is created in create_business method.
        assert len(business.party_roles.all()) == 1
        assert len(filing_rec.filing_party_roles.all()) == 2
        assert filing_rec.court_order_file_number == '12356'
        assert filing_rec.court_order_effect_of_order == 'planOfArrangement'

        # Parties
        parties = filing_rec.filing_json['filing']['incorporationApplication']['parties']
        assert parties[0]['officer']['firstName'] == 'Joe'
        assert parties[0]['officer']['lastName'] == 'Swanson'
        assert parties[0]['officer']['middleName'] == 'P'
        assert parties[0]['officer']['partyType'] == 'person'
        assert parties[1]['officer']['partyType'] == 'organization'
        assert parties[1]['officer']['organizationName'] == 'Xyz Inc.'

    mock_get_next_corp_num.assert_called_with(
        filing['filing']['incorporationApplication']['nameRequest']['legalType'], None)


@pytest.mark.parametrize('registry,business_type,prefix,num_length', [
    ('colin', 'BEN', 'BC', 9),
    ('colin', 'BC', 'BC', 9),
    ('br', 'CP', 'CP', 9),
    ('br', 'FM', 'FM', 9)
])
def test_get_next_corp_num(requests_mock, mocker, app,
                           registry,
                           business_type,
                           prefix,
                           num_length,
                           ):
    """Assert that the corpnum is the correct format."""
    if registry == 'colin':
        from flask import current_app
        mocker.patch('business_filer.filing_processors.filing_components.business_info.AccountService.get_bearer_token', return_value='token')
        colin_api = current_app.config.get("COLIN_API", "http://test.test")

        with app.app_context():
            requests_mock.post(f'{colin_api}/BC', json={'corpNum': '1234567'})

            corp_num = business_info.get_next_corp_num(business_type)
    
    if registry == 'br':
        corp_num = business_info.get_next_corp_num(business_type)

    assert corp_num.startswith(prefix)
    assert len(corp_num) == num_length


def test_incorporation_filing_coop_from_colin(app, session):
    """Assert that an existing coop incorporation is loaded corrrectly."""
    # setup
    corp_num = f'CP{random.randint(1000000, 9999999)}'
    nr_num = f'NR {random.randint(1000000, 9999999)}'
    colind_id = random.randint(1, 9999999)
    filing = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)

    # Change the template to be a CP == Cooperative
    filing['filing']['business']['legalType'] = 'CP'
    filing['filing']['business']['identifier'] = corp_num
    filing['filing']['incorporationApplication']['nameRequest']['legalType'] = 'CP'
    filing['filing']['incorporationApplication']['nameRequest']['legalName'] = 'Test'
    filing['filing']['incorporationApplication']['nameRequest']['nrNumber'] = nr_num
    filing['filing']['incorporationApplication'].pop('shareStructure')
    effective_date = datetime.now(timezone.utc)
    # Create the Filing obeject in the DB
    filing_rec = Filing(effective_date=effective_date,
                        filing_json=filing)
    colin_event = ColinEventId()
    colin_event.colin_event_id = colind_id
    filing_rec.colin_event_ids.append(colin_event)
    # Override the state setting mechanism
    filing_rec.skip_status_listener = True
    filing_rec._status = 'PENDING'
    filing_rec.save()
    filing_meta = FilingMeta(application_date=filing_rec.effective_date)

    # test
    business, filing_rec, filing_meta = incorporation_filing.process(None, filing, filing_rec, filing_meta, None)

    # Assertions
    assert business.identifier == corp_num
    assert business.founding_date == effective_date
    assert business.legal_type == filing['filing']['incorporationApplication']['nameRequest']['legalType']
    assert business.legal_name == 'Test'
    assert len(business.offices.all()) == 2  # One office is created in create_business method.


@pytest.mark.parametrize('legal_type, legal_name_suffix', [
    ('BC', 'B.C. LTD.'),
    ('ULC', 'B.C. UNLIMITED LIABILITY COMPANY'),
    ('CC', 'B.C. COMMUNITY CONTRIBUTION COMPANY LTD.'),
])
def test_incorporation_filing_bc_company_from_colin(app, session, legal_type, legal_name_suffix):
    """Assert that an existing bc company(LTD, ULC, CCC) incorporation is loaded corrrectly."""
    # setup
    corp_num = f'BC{random.randint(1000000, 9999999)}'
    colind_id = random.randint(0, 9999999)
    filing = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)

    # Change the template to be LTD, ULC or CCC
    filing['filing']['business']['legalType'] = legal_type
    filing['filing']['business']['identifier'] = corp_num
    filing['filing']['incorporationApplication']['nameRequest']['legalType'] = legal_type
    effective_date = datetime.now(timezone.utc)
    # Create the Filing object in the DB
    filing_rec = Filing(effective_date=effective_date,
                        filing_json=filing)
    colin_event = ColinEventId()
    colin_event.colin_event_id = colind_id
    filing_rec.colin_event_ids.append(colin_event)
    # Override the state setting mechanism
    filing_rec.skip_status_listener = True
    filing_rec._status = 'PENDING'
    filing_rec.save()
    filing_meta = FilingMeta(application_date=filing_rec.effective_date)

    # test
    business, filing_rec, filing_meta = incorporation_filing.process(None, filing, filing_rec, filing_meta, None)

    # Assertions
    assert business.identifier == corp_num
    assert business.founding_date == effective_date # .replace(tzinfo=None)
    assert business.legal_type == filing['filing']['incorporationApplication']['nameRequest']['legalType']
    assert business.legal_name == f'{business.identifier[2:]} {legal_name_suffix}'
    assert len(business.offices.all()) == 2  # One office is created in create_business method.
    assert len(business.share_classes.all()) == 2
    assert len(business.party_roles.all()) == 1
