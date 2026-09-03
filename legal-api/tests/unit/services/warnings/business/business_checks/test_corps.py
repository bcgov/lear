# Copyright © 2024 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in business with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Test suite to ensure Corpse business checks work correctly."""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from tests.unit.models import factory_business
from legal_api.services.warnings.business.business_checks import WarningType
from legal_api.services.warnings.business.business_checks.corps import check_business

@pytest.mark.parametrize("has_amalgamation, expected_warning", [
    (True, True),  # Future effective amalgamation
    (False, False)  # No amalgamation
])
def test_check_business(session, has_amalgamation, expected_warning):
    """Test the check_business function."""
    business = factory_business(identifier="BC1234567")

    mock_filing = Mock()
    mock_filing.id = "filing-id"
    mock_filing.filing_json = {
        "filing": {
            "amalgamationApplication": {
                "amalgamatingBusinesses": [{"identifier": "BC7654321"}],
                "nameRequest": {
                    "legalName": "NAMED AMALG CORP.",
                    "legalType": "BC"
                }
            },
            "business": {
                "identifier": "T987654321",
                "legalType": "BC"
            }
        }
    }
    if has_amalgamation:
        # Set effective_date in the future to simulate an amalgamation
        mock_filing.effective_date = datetime.now() + timedelta(days=1)
        mock_filing.payment_completion_date = datetime.now()
    else:
        # Set dates that do not indicate an amalgamation
        mock_filing.effective_date = datetime.now()
        mock_filing.payment_completion_date = datetime.now()

    with patch('business_model.models.business.Business.is_pending_amalgamating_business', return_value=mock_filing):
        result = check_business(business, is_staff=True)

        if expected_warning:
            assert len(result) == 1
            warning = result[0]
            assert warning['code'] == "AMALGAMATING_BUSINESS"
            assert warning['message'] == "This business is part of a future effective amalgamation."
            assert warning['warningType'] == WarningType.FUTURE_EFFECTIVE_AMALGAMATION
            assert 'amalgamationDate' in warning['data']
            assert isinstance(warning['data']['amalgamationDate'], datetime)
            assert warning['data']['filingId'] == "filing-id"
            assert warning['data']['amalgamatingBusinesses'] == [{"identifier": "BC7654321"}]
            assert warning['data']['resultingBusinessName'] == "NAMED AMALG CORP."
            assert warning['data']['resultingBusinessIdentifier'] == "T987654321"
        else:
            assert len(result) == 0


@pytest.mark.parametrize("name_request, expected_resulting_name", [
    # named amalgamation result - legalName present
    ({"legalName": "NAMED AMALG CORP.", "legalType": "BC"}, "NAMED AMALG CORP."),
    # numbered amalgamation result - no legalName key at all
    ({"correctNameOption": "correct-aml-numbered", "legalType": "BC"}, None),
    # no nameRequest present at all
    ({}, None),
])
def test_check_business_amalgamation_resulting_name(session, name_request, expected_resulting_name):
    """Test that resultingBusinessName reflects whether the amalgamation result is named or numbered."""
    business = factory_business(identifier="BC1234567")

    mock_filing = Mock()
    mock_filing.id = "filing-id"
    mock_filing.effective_date = datetime.now() + timedelta(days=1)
    mock_filing.payment_completion_date = datetime.now()
    mock_filing.filing_json = {
        "filing": {
            "amalgamationApplication": {
                "amalgamatingBusinesses": [{"identifier": "BC7654321"}],
                "nameRequest": name_request
            },
            "business": {
                "identifier": "T987654321",
                "legalType": "BC"
            }
        }
    }

    with patch('business_model.models.business.Business.is_pending_amalgamating_business', return_value=mock_filing):
        warning = check_business(business, is_staff=True)[0]

    assert warning['data'].get('resultingBusinessName') == expected_resulting_name

    if expected_resulting_name is None:
        assert 'resultingBusinessName' not in warning['data']
    else:
        assert 'resultingBusinessName' in warning['data']


def test_check_business_excludes_filing_id_for_non_staff(session):
    """Test that filing ids and the resulting business identifier are only included for staff users."""
    business = factory_business(identifier="BC1234567")
    mock_filing = Mock(
        id="filing-id",
        effective_date=datetime.now() + timedelta(days=1),
        payment_completion_date=datetime.now(),
        filing_json={
            "filing": {
                "amalgamationApplication": {
                    "amalgamatingBusinesses": [{"identifier": "BC7654321"}],
                    "nameRequest": {
                        "legalName": "NAMED AMALG CORP.",
                        "legalType": "BC"
                    }
                },
                "business": {
                    "identifier": "T987654321",
                    "legalType": "BC"
                }
            }
        }
    )

    with patch('business_model.models.business.Business.is_pending_amalgamating_business', return_value=mock_filing):
        warning = check_business(business)[0]

    assert warning['data'] == {
        "amalgamationDate": mock_filing.effective_date,
        "amalgamatingBusinesses": [{"identifier": "BC7654321"}],
        "resultingBusinessName": "NAMED AMALG CORP."
    }
    assert 'filingId' not in warning['data']
    assert 'resultingBusinessIdentifier' not in warning['data']
