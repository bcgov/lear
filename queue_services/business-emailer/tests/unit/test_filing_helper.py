# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for filing_helper."""
import pytest

from business_emailer.filing_helper import is_special_resolution_correction_by_filing_json


SR_CORRECTION_KEYS = [
    "rulesInResolution",
    "resolution",
    "rulesFileKey",
    "memorandumFileKey",
    "memorandumInResolution",
    "cooperativeAssociationType",
]


@pytest.mark.parametrize("key", SR_CORRECTION_KEYS)
def test_returns_true_when_sr_correction_key_present(key):
    """Each SR correction key on its own should return True."""
    filing = {"correction": {key: "anything"}}
    assert is_special_resolution_correction_by_filing_json(filing) is True


def test_returns_true_when_multiple_sr_correction_keys_present():
    """Multiple SR correction keys should still return True."""
    filing = {"correction": {"resolution": "x", "rulesFileKey": "y"}}
    assert is_special_resolution_correction_by_filing_json(filing) is True


def test_returns_true_when_name_request_has_request_type():
    """nameRequest.requestType without SR keys should return True."""
    filing = {"correction": {"nameRequest": {"requestType": "CHG"}}}
    assert is_special_resolution_correction_by_filing_json(filing) is True


def test_returns_true_when_sr_key_and_name_request_type_both_present():
    """Both signals present should return True."""
    filing = {"correction": {"resolution": "x", "nameRequest": {"requestType": "CHG"}}}
    assert is_special_resolution_correction_by_filing_json(filing) is True


def test_returns_false_for_empty_correction():
    """Empty correction object should return False."""
    filing = {"correction": {}}
    assert is_special_resolution_correction_by_filing_json(filing) is False


def test_returns_false_for_unrelated_correction_keys():
    """Correction with only unrelated keys should return False."""
    filing = {"correction": {"comment": "typo fix", "legalName": "Acme Inc."}}
    assert is_special_resolution_correction_by_filing_json(filing) is False


def test_returns_false_when_name_request_missing_request_type():
    """nameRequest without requestType and no SR keys should return False."""
    filing = {"correction": {"nameRequest": {"legalType": "BC"}}}
    assert is_special_resolution_correction_by_filing_json(filing) is False


def test_returns_false_when_name_request_is_empty():
    """Empty nameRequest and no SR keys should return False."""
    filing = {"correction": {"nameRequest": {}}}
    assert is_special_resolution_correction_by_filing_json(filing) is False


def test_raises_type_error_when_correction_missing():
    """Filing with no 'correction' key raises TypeError (documents current behaviour)."""
    with pytest.raises(TypeError):
        is_special_resolution_correction_by_filing_json({})
