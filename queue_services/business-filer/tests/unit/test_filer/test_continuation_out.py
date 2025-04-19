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
"""The Unit Tests for the Continuation Out filing."""
import copy
import random

from datetime import datetime
from business_model.models import Business, Filing

from registry_schemas.example_data import CONTINUATION_OUT, FILING_TEMPLATE
from business_filer.common.legislation_datetime import LegislationDatetime

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors import continuation_out
from tests.unit import create_business, create_filing


def tests_filer_continuation_out(app, session):
    """Assert that the continuation out object is correctly populated to model objects."""
    identifier = 'BC1234567'
    business = create_business(identifier, legal_type='CP')

    filing_json = copy.deepcopy(FILING_TEMPLATE)
    filing_json['filing']['business']['identifier'] = identifier
    filing_json['filing']['header']['name'] = 'continuationOut'
    filing_json['filing']['continuationOut'] = CONTINUATION_OUT

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    continuation_out_filing = create_filing(payment_id, filing_json, business_id=business.id)

    filing_meta = FilingMeta()

    # Test
    continuation_out.process(business, continuation_out_filing, filing_json['filing'], filing_meta)
    business.save()

    # Check outcome
    final_filing = Filing.find_by_id(continuation_out_filing.id)
    foreign_jurisdiction_json = filing_json['filing']['continuationOut']['foreignJurisdiction']
    continuation_out_date_str = filing_json['filing']['continuationOut']['continuationOutDate']
    continuation_out_date = LegislationDatetime.as_utc_timezone_from_legislation_date_str(continuation_out_date_str)

    assert filing_json['filing']['continuationOut']['courtOrder']['fileNumber'] == final_filing.court_order_file_number
    assert filing_json['filing']['continuationOut']['courtOrder']['effectOfOrder'] == final_filing.court_order_effect_of_order

    assert business.state == Business.State.HISTORICAL
    assert business.state_filing_id == final_filing.id
    assert business.jurisdiction == foreign_jurisdiction_json['country'].upper()
    assert business.foreign_jurisdiction_region == foreign_jurisdiction_json['region'].upper()
    assert business.foreign_legal_name == filing_json['filing']['continuationOut']['legalName']
    assert business.continuation_out_date == continuation_out_date

    assert filing_meta.continuation_out['country'] == foreign_jurisdiction_json['country']
    assert filing_meta.continuation_out['region'] == foreign_jurisdiction_json['region']
    assert filing_meta.continuation_out['continuationOutDate'] == continuation_out_date_str
    assert filing_meta.continuation_out['legalName'] == filing_json['filing']['continuationOut']['legalName']
