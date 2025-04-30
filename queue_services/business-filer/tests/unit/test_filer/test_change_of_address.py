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
"""The Test Suites to ensure that the worker is operating correctly."""
import copy
import datetime
from datetime import timezone
from http import HTTPStatus
import random
from unittest.mock import patch

import pycountry
import pytest
import pytz
from freezegun import freeze_time
from business_model.models import Business, Filing, PartyRole, User
from registry_schemas.example_data import (
    CHANGE_OF_ADDRESS,
    FILING_HEADER,
)

from business_filer.exceptions import QueueException
from business_filer.filing_processors.filing_components import business_info, business_profile, create_party, create_role
from business_filer.services.filer import process_filing
from tests.unit import (
    COD_FILING_TWO_ADDRESSES,
    COMBINED_FILING,
    create_business,
    create_filing,
    create_user,
)
from business_filer.common.filing_message import FilingMessage


def compare_addresses(business_address: dict, filing_address: dict):
    """Compare two address dicts."""
    for key, value in business_address.items():
        if value is None and filing_address.get(key):
            assert False
        elif key == 'addressCountry':
            pycountry.countries.search_fuzzy(value)[0].alpha_2 == \
                pycountry.countries.search_fuzzy(filing_address.get('addressCountry'))[0].alpha_2
            assert business_address[key] == 'CA'
        elif key not in ('addressType', 'id'):
            assert business_address.get(key) == (filing_address.get(key) or '')


def test_process_coa_filing(app, session):
    """Assert that a COD filling can be applied to the model correctly."""
    # vars
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    identifier = 'CP1234567'
    coa_filing = copy.deepcopy(FILING_HEADER)
    coa_filing['filing']['changeOfAddress'] = copy.deepcopy(CHANGE_OF_ADDRESS)
    new_delivery_address = coa_filing['filing']['changeOfAddress']['offices']['registeredOffice']['deliveryAddress']
    new_mailing_address = coa_filing['filing']['changeOfAddress']['offices']['registeredOffice']['mailingAddress']

    # setup
    business = create_business(identifier)
    business_id = business.id
    filing_id = (create_filing(payment_id, coa_filing, business.id)).id
    filing_msg = FilingMessage(filing_identifier=filing_id)

    # TEST
    process_filing(filing_msg)

    # Get modified data
    filing = Filing.find_by_id(filing_id)
    business = Business.find_by_internal_id(business_id)

    # check it out
    assert filing.transaction_id
    assert filing.business_id == business_id
    assert filing.status == Filing.Status.COMPLETED.value

    register_office = business.offices.filter_by(office_type='registeredOffice').one_or_none()

    delivery_address = register_office.addresses.filter_by(address_type='delivery').one_or_none().json
    compare_addresses(delivery_address, new_delivery_address)
    mailing_address = register_office.addresses.filter_by(address_type='mailing').one_or_none().json
    compare_addresses(mailing_address, new_mailing_address)
