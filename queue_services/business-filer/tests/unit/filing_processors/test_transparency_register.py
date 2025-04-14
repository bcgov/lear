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
"""The Unit Tests for the Transparency Register filing."""
from datetime import datetime

import pytest
from business_model.models import Filing
from business_filer.common.legislation_datetime import LegislationDatetime

from business_filer.filing_processors import transparency_register
from tests.unit import create_business, create_filing


@pytest.mark.parametrize('test_name, sub_type, expected', [
    ('INITIAL', 'initial', None),
    ('CHANGE', 'change', None),
    ('ANNUAL', 'annual', 2024)
])
def test_transparency_register_filing_process_annual(app, session, test_name, sub_type, expected):
    """Assert that the transparency register object is correctly populated to model objects."""
    # setup
    effective_date = LegislationDatetime.as_legislation_timezone(datetime(2024, 3, 2))
    filing = {
        'filing': {
            'header': {
                'name': 'transparencyRegister',
                'date': LegislationDatetime.datenow().isoformat(),
                'effectiveDate': effective_date.isoformat(),
                'certifiedBy': 'test'
            },
            'business': {'identifier': 'BC1234567'},
            'transparencyRegister': {
                'type': sub_type,
                'ledgerReferenceNumber': '12384cnfjnj43'
            }}}

    business = create_business(filing['filing']['business']['identifier'])
    create_filing('123', filing)

    filing_rec = Filing(effective_date=effective_date, filing_json=filing)

    # test
    transparency_register.process(business, filing_rec, filing['filing'])

    # Assertions
    assert business.last_tr_year == expected
