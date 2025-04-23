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
from flask import current_app
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


def test_publish_event():
    """Assert that publish_event is called with the correct struct."""
    import uuid
    from unittest.mock import AsyncMock
    from business_filer.services.filer import get_filing_types, publish_event, qsm
    from business_filer.common.datetime import datetime

    mock_publish = AsyncMock()
    qsm.service = mock_publish
    with freeze_time(datetime.now(timezone.utc)), \
            patch.object(uuid, 'uuid4', return_value=1):

        business = Business(identifier='BC1234567')
        filing = Filing(id=1,
                        effective_date=datetime.now(timezone.utc),
                        _filing_type='incorporationApplication',
                        _filing_json=INCORPORATION_FILING_TEMPLATE)

        publish_event(business, filing)

        payload = {
            'specversion': '1.x-wip',
            'type': 'bc.registry.business.' + filing.filing_type,
            'source': ''.join(
                [current_app.config.get('LEGAL_API_URL'),
                 '/business/',
                 business.identifier,
                 '/filing/',
                 str(filing.id)]),
            'id': str(uuid.uuid4()),
            'time': datetime.now(timezone.utc).isoformat(),
            'datacontenttype': 'application/json',
            'identifier': business.identifier,
            'data': {
                'filing': {
                    'header': {'filingId': filing.id,
                               'effectiveDate': filing.effective_date.isoformat()
                               },
                    'business': {'identifier': business.identifier},
                    'legalFilings': get_filing_types(filing.filing_json)
                }
            }
        }

    mock_publish.publish.assert_called_with('entity.events', payload)
