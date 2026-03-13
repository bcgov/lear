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
"""The Test Suite to ensure that the worker is operating correctly for corrections."""
import copy
import pytest
import random

from business_model.models import Business, Filing, PartyRole
from registry_schemas.example_data import (
    CHANGE_OF_DIRECTORS,
    CHANGE_OF_RECEIVERS,
    CHANGE_OF_LIQUIDATORS,
    CORRECTION_COL,
    CORRECTION_COR,
    FILING_TEMPLATE
)

from business_filer.common.filing_message import FilingMessage
from business_filer.services.filer import process_filing
from tests.unit import create_business, create_filing


COD = copy.deepcopy(CHANGE_OF_DIRECTORS)
COD['directors'][0]['actions'] = ['appointed']
COD['directors'][1]['actions'] = ['appointed']

CORRECTION_COD = copy.deepcopy(CORRECTION_COL)
CORRECTION_COD['filing']['correction']['correctedFilingType'] = 'changeOfDirectors'
CORRECTION_COD['filing']['correction']['relationships'][0]['roles'][0]['roleType'] = 'Director'


def _assert_common_data(business: Business, filing: Filing):
    """Assert the expected common data was updated by the filing processing."""
    assert filing.transaction_id
    assert filing.business_id == business.id
    assert filing.status == Filing.Status.COMPLETED.value


def _get_filing(filing_type: str, data: dict, identifier = 'BC1234567', needs_template = True):
    """Return the filing json, payment id and identifier."""
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    if needs_template:
        filing = copy.deepcopy(FILING_TEMPLATE)
        filing['filing'][filing_type] = copy.deepcopy(data)
    else:
        filing = copy.deepcopy(data)

    filing['filing']['header']['name'] = filing_type
    filing['filing']['business']['identifier'] = identifier
    filing['filing']['business']['legalType'] = 'BC'
    return filing, payment_id, identifier
    

@pytest.mark.parametrize('filing_name, original_data, correction_data, expected_lear_only', [
    ('changeOfDirectors', COD, CORRECTION_COD, False),
    ('changeOfLiquidators', CHANGE_OF_LIQUIDATORS, CORRECTION_COL, True),
    ('changeOfReceivers', CHANGE_OF_RECEIVERS, CORRECTION_COR, True),
])
def test_process_correction_filing_with_relationships(app, session, mocker, filing_name, original_data, correction_data, expected_lear_only):
    """Assert that correction filings can be applied to the model correctly."""
    # mock out the email sender and event publishing
    mocker.patch('business_filer.services.publish_event.PublishEvent.publish_email_message', return_value=None)
    mocker.patch('business_filer.services.publish_event.PublishEvent.publish_event', return_value=None)
    mocker.patch('business_filer.filing_processors.filing_components.business_profile.update_business_profile',
                 return_value=None)
    mocker.patch('business_filer.services.AccountService.update_entity', return_value=None)

    orig_filing, payment_id, identifier = _get_filing(filing_name, original_data)
    business = create_business(identifier)
    orig_filing_rec = create_filing(payment_id, orig_filing, business.id)

    # process original filing
    filing_msg = FilingMessage(filing_identifier=orig_filing_rec.id)
    process_filing(filing_msg)
    orig_processed_filing: Filing = Filing.find_by_id(orig_filing_rec.id)
    # sanity checks
    _assert_common_data(business, orig_processed_filing)
    party_roles = business.party_roles.all()
    assert len(party_roles) == 2

    # setup correction
    correction_filing, corrected_payment_id, _ = _get_filing('correction', correction_data, business.identifier, False)
    expected_given_name = 'corrected given name'
    expected_mailing_street = 'corrected mailing street'
    expected_delivery_street = 'corrected delivery street'
    corrected_party_id = party_roles[0].party.id
    correction_filing['filing']['correction']['correctedFilingId'] = orig_filing_rec.id
    correction_filing['filing']['correction']['relationships'][0]['entity']['identifier'] = corrected_party_id
    correction_filing['filing']['correction']['relationships'][0]['entity']['givenName'] = expected_given_name
    correction_filing['filing']['correction']['relationships'][0]['mailingAddress']['streetAddress'] = expected_mailing_street
    correction_filing['filing']['correction']['relationships'][0]['deliveryAddress']['streetAddress'] = expected_delivery_street
    
    correction_filing_rec = create_filing(corrected_payment_id, correction_filing, business.id)

    # process original filing
    correction_filing_msg = FilingMessage(filing_identifier=correction_filing_rec.id)
    process_filing(correction_filing_msg)
    correction_processed_filing: Filing = Filing.find_by_id(correction_filing_rec.id)
    # assert changes
    _assert_common_data(business, correction_processed_filing)
    assert correction_processed_filing.lear_only == expected_lear_only
    party_roles: list[PartyRole] = business.party_roles.all()
    assert len(party_roles) == 2
    for role in party_roles:
        if role.party.id == corrected_party_id:
            assert role.party.first_name == expected_given_name.upper()
            assert role.party.mailing_address.street == expected_mailing_street
            assert role.party.delivery_address.street == expected_delivery_street
