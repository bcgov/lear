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
# from legal_api.resources.v1.business import DirectorResource
from registry_schemas.example_data import (
    ANNUAL_REPORT,
    CHANGE_OF_ADDRESS,
    CONTINUATION_IN_FILING_TEMPLATE,
    CORRECTION_AR,
    FILING_HEADER,
    INCORPORATION_FILING_TEMPLATE,
)

from business_filer.exceptions import QueueException
from business_filer.filing_processors.filing_components import business_info, business_profile, create_party, create_role
from business_filer.services.filer import process_filing
from tests.unit import (
    COD_FILING,
    COD_FILING_TWO_ADDRESSES,
    COMBINED_FILING,
    create_business,
    create_filing,
    create_user,
)
from business_filer.common.filing_message import FilingMessage


@pytest.mark.parametrize('test_name,withdrawal_pending,filing_status', [
    ('Process the Filing', False, 'PAID'),
    ('Dont process the Filing', False, 'WITHDRAWN'),
    ('Dont process the Filing', True, 'PAID'),
    ('Dont process the Filing', True, 'WITHDRAWN'),
])
def test_skip_process_filing(app, session, mocker, test_name, withdrawal_pending, filing_status):
    """Assert that an filling can be processed."""
    # vars
    filing_type = 'continuationIn'
    nr_identifier = f'NR {random.randint(1000000,9999999)}'
    next_corp_num = f'C{random.randint(1000000,9999999)}'

    filing = copy.deepcopy(CONTINUATION_IN_FILING_TEMPLATE)
    filing['filing'][filing_type]['nameRequest']['nrNumber'] = nr_identifier
    filing['filing'][filing_type]['nameTranslations'] = [{'name': 'ABCD Ltd.'}]
    filing_rec = create_filing('123', filing)
    effective_date = datetime.datetime.now(datetime.timezone.utc)
    filing_rec.effective_date = effective_date
    filing_rec._status = filing_status
    filing_rec.withdrawal_pending = withdrawal_pending
    filing_rec.save()

    # test
    filing_msg = FilingMessage(filing_identifier=filing_rec.id) 
    with patch.object(business_info, 'get_next_corp_num', return_value=next_corp_num):
        with patch.object(business_profile, 'update_business_profile', return_value=HTTPStatus.OK):
            if withdrawal_pending and filing_status != 'WITHDRAWN':
                with pytest.raises(QueueException):
                    process_filing(filing_msg)
            else:
                process_filing(filing_msg)

    business = Business.find_by_identifier(next_corp_num)
    if not withdrawal_pending and filing_status == 'PAID':
        assert business.state == Business.State.ACTIVE
