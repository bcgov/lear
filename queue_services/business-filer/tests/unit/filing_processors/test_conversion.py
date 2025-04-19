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
from unittest.mock import patch

import pytest
from business_model.models import Filing
from business_model.models.colin_event_id import ColinEventId
from business_filer.common.datetime import datetime
from registry_schemas.example_data import CONVERSION_FILING_TEMPLATE

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors import conversion
from tests.unit import create_filing


def test_conversion_process_with_nr(app, session):
    """Assert that the incorporation object is correctly populated to model objects."""
    # setup
    filing = copy.deepcopy(CONVERSION_FILING_TEMPLATE)
    identifier = 'BC1234567'
    nr_num = 'NR 1234567'
    filing['filing']['business']['identifier'] = identifier
    filing['filing']['conversion']['nameRequest']['nrNumber'] = nr_num
    filing['filing']['conversion']['nameRequest']['legalName'] = 'Test'
    create_filing('123', filing)

    effective_date = datetime.utcnow()
    filing_rec = Filing(effective_date=effective_date, filing_json=filing)
    filing_meta = FilingMeta(application_date=effective_date)

    # test
    business, filing_rec = conversion.process(None, filing, filing_rec, filing_meta)

    # Assertions
    assert business.identifier == identifier
    assert business.founding_date == effective_date
    assert business.legal_type == filing['filing']['conversion']['nameRequest']['legalType']
    assert business.legal_name == filing['filing']['conversion']['nameRequest']['legalName']
    assert len(business.share_classes.all()) == 2
    assert len(business.offices.all()) == 2  # One office is created in create_business method.


def test_conversion_process_no_nr(app, session):
    """Assert that the incorporation object is correctly populated to model objects."""
    # setup
    filing = copy.deepcopy(CONVERSION_FILING_TEMPLATE)
    identifier = 'BC1234567'
    filing['filing']['business']['identifier'] = identifier
    create_filing('123', filing)
    effective_date = datetime.utcnow()
    filing_rec = Filing(effective_date=effective_date, filing_json=filing)
    filing_meta = FilingMeta(application_date=effective_date)

    # test
    business, filing_rec = conversion.process(None, filing, filing_rec, filing_meta)

    # Assertions
    assert business.identifier == identifier
    assert business.founding_date == effective_date
    assert business.legal_type == filing['filing']['conversion']['nameRequest']['legalType']
    assert business.legal_name == business.identifier[2:] + ' B.C. LTD.'
    assert len(business.share_classes.all()) == 2
    assert len(business.offices.all()) == 2  # One office is created in create_business method.



def test_conversion_coop_from_colin(app, session):
    """Assert that an existing coop incorporation is loaded corrrectly."""
    # setup
    identifier = 'CP0000001'
    nr_num = 'NR 1234567'
    colind_id = 1
    filing = copy.deepcopy(CONVERSION_FILING_TEMPLATE)

    # Change the template to be a CP == Cooperative
    filing['filing']['business']['legalType'] = 'CP'
    filing['filing']['business']['identifier'] = identifier
    filing['filing']['conversion']['nameRequest']['legalType'] = 'CP'
    filing['filing']['conversion']['nameRequest']['legalName'] = 'Test'
    filing['filing']['conversion']['nameRequest']['nrNumber'] = nr_num
    filing['filing']['conversion'].pop('shareStructure')
    effective_date = datetime.utcnow()
    # Create the Filing obeject in the DB
    filing_rec = Filing(effective_date=effective_date,
                        filing_json=filing)
    colin_event = ColinEventId()
    colin_event.colin_event_id=colind_id
    filing_rec.colin_event_ids.append(colin_event)
    # Override the state setting mechanism
    filing_rec.skip_status_listener = True
    filing_rec._status = 'PENDING'
    filing_rec.save()
    filing_meta = FilingMeta(application_date=effective_date)

    # test
    business, filing_rec = conversion.process(None, filing, filing_rec, filing_meta)

    # Assertions
    assert business.identifier == identifier
    assert business.founding_date.replace(tzinfo=None) == effective_date.replace(tzinfo=None)
    assert business.legal_type == filing['filing']['conversion']['nameRequest']['legalType']
    assert business.legal_name == 'Test'
    assert len(business.offices.all()) == 2  # One office is created in create_business method.


@pytest.mark.parametrize('legal_type, legal_name_suffix', [
    ('BC', 'B.C. LTD.'),
    ('ULC', 'B.C. UNLIMITED LIABILITY COMPANY'),
    ('CC', 'B.C. COMMUNITY CONTRIBUTION COMPANY LTD.'),
])
def test_conversion_bc_company_from_colin(app, session, legal_type, legal_name_suffix):
    """Assert that an existing bc company(LTD, ULC, CCC) incorporation is loaded corrrectly."""
    # setup
    identifier = f'BC{random.randint(1000000, 9999999)}'
    colind_id = random.randint(1000000, 9999999)
    filing = copy.deepcopy(CONVERSION_FILING_TEMPLATE)

    # Change the template to be LTD, ULC or CCC
    filing['filing']['business']['legalType'] = legal_type
    filing['filing']['business']['identifier'] = identifier
    filing['filing']['conversion']['nameRequest']['legalType'] = legal_type
    effective_date = datetime.utcnow()
    # Create the Filing object in the DB
    filing_rec = Filing(effective_date=effective_date,
                        filing_json=filing)
    colin_event = ColinEventId()
    colin_event.colin_event_id=colind_id
    filing_rec.colin_event_ids.append(colin_event)
    # Override the state setting mechanism
    filing_rec.skip_status_listener = True
    filing_rec._status = 'PENDING'
    filing_rec.save()
    filing_meta = FilingMeta(application_date=effective_date)

    # test
    business, filing_rec = conversion.process(None, filing, filing_rec, filing_meta)

    # Assertions
    assert business.identifier == identifier
    assert business.founding_date.replace(tzinfo=None) == effective_date.replace(tzinfo=None)
    assert business.legal_type == filing['filing']['conversion']['nameRequest']['legalType']
    assert business.legal_name == f'{business.identifier[2:]} {legal_name_suffix}'
    assert len(business.offices.all()) == 2  # One office is created in create_business method.
    assert len(business.share_classes.all()) == 2
    assert len(business.party_roles.all()) == 1
    assert len(filing_rec.filing_party_roles.all()) == 2
