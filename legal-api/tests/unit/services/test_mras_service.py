# Copyright © 2024 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for the MRAS service.

Test suite to ensure that the MRAS service is working as expected.
"""

from http import HTTPStatus
from unittest.mock import MagicMock, patch

import pytest
import requests

from legal_api.services import MrasService


MRAS_CONTENT_TARGET = """
<Jurisdictions xmlns="http://mras.ca/schema/v1">
    <Jurisdiction>
        <JurisdictionID>SK</JurisdictionID>
        <NameEn>Saskatchewan</NameEn>
        <NameFr>Saskatchewan</NameFr>
        <RedirectUrl>asdf</RedirectUrl>
        <TargetProfileID>1111</TargetProfileID>
    </Jurisdiction>
    <Jurisdiction>
        <JurisdictionID>QC</JurisdictionID>
        <NameEn>Quebec</NameEn>
        <NameFr>Québec</NameFr>
        <RedirectUrl>asdf</RedirectUrl>
    </Jurisdiction>
    <Jurisdiction>
        <JurisdictionID>MB</JurisdictionID>
        <NameEn>Manitoba</NameEn>
        <NameFr>Manitoba</NameFr>
        <RedirectUrl>asdf</RedirectUrl>
    </Jurisdiction>
    <Jurisdiction>
        <JurisdictionID>AB</JurisdictionID>
        <NameEn>Alberta</NameEn>
        <NameFr>Alberta</NameFr>
        <RedirectUrl>asdfasdf</RedirectUrl>
        <TargetProfileID>2222</TargetProfileID>
    </Jurisdiction>
</Jurisdictions>
"""

MRAS_CONTENT_NO_TARGET = """
<Jurisdictions xmlns="http://mras.ca/schema/v1">
    <Jurisdiction>
        <JurisdictionID>SK</JurisdictionID>
        <NameEn>Saskatchewan</NameEn>
        <NameFr>Saskatchewan</NameFr>
        <RedirectUrl>asdf</RedirectUrl>
    </Jurisdiction>
    <Jurisdiction>
        <JurisdictionID>QC</JurisdictionID>
        <NameEn>Quebec</NameEn>
        <NameFr>Québec</NameFr>
        <RedirectUrl>asdf</RedirectUrl>
    </Jurisdiction>
    <Jurisdiction>
        <JurisdictionID>MB</JurisdictionID>
        <NameEn>Manitoba</NameEn>
        <NameFr>Manitoba</NameFr>
        <RedirectUrl>asdf</RedirectUrl>
    </Jurisdiction>
    <Jurisdiction>
        <JurisdictionID>AB</JurisdictionID>
        <NameEn>Alberta</NameEn>
        <NameFr>Alberta</NameFr>
        <RedirectUrl>asdf</RedirectUrl>
    </Jurisdiction>
</Jurisdictions>
"""

@pytest.mark.parametrize(
        'test_name, mock_status, mock_return, expected', [
            ('HAS_JURISDICTIONS', HTTPStatus.OK, MRAS_CONTENT_TARGET, [
                {
                    "id": "SK",
                    "name": "Saskatchewan",
                    "nameFr": "Saskatchewan",
                    "redirectUrl": "asdf",
                    "targetProfileId": "1111"
                },
                {
                    "id": "AB",
                    "name": "Alberta",
                    "nameFr": "Alberta",
                    "redirectUrl": "asdfasdf",
                    "targetProfileId": "2222"
                }
            ]),
            ('NO_JURISDICTIONS', HTTPStatus.OK, MRAS_CONTENT_NO_TARGET, []),
            ('ERROR', HTTPStatus.UNAUTHORIZED, None, None)
        ]
)
def test_get_jurisdictions(session, test_name, mock_status, mock_return, expected):
    """Assert that returns foreign jurisdictions for the given business."""
    mock_response = MagicMock()
    mock_response.status_code = mock_status
    mock_response.content = mock_return
    with patch.object(requests, 'get', return_value=mock_response):
        jurisdictions = MrasService.get_jurisdictions('BC1234567')
        assert jurisdictions == expected
