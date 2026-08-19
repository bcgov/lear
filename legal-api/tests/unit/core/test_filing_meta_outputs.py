# Copyright © 2026 Province of British Columbia
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
"""Pure unit tests for FilingMeta output-list alterations.

alter_outputs_dissolution operates only on the filing stand-in and the outputs
set, so it is exercised with SimpleNamespace stubs (no DB / app context).
"""
from types import SimpleNamespace

from business_model.models import Business

from legal_api.core import FilingMeta


def _filing(**kw):
    defaults = {"filing_type": None, "filing_sub_type": None, "json_legal_type": None, "meta_data": None}
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def test_alter_outputs_dissolution_firm_administrative_no_cert_no_raise():
    """Firms (SP/GP) carry no certificateOfDissolution output.

    Admin-dissolution suppression must be a no-op rather than a KeyError.
    Regression for bcgov/entity#33806 (admin dissolution 400'd the firm ledger).
    """
    filing = _filing(filing_type="dissolution", filing_sub_type="administrative",
                     json_legal_type=Business.LegalTypes.SOLE_PROP)
    outputs = set()
    result = FilingMeta.alter_outputs_dissolution(filing, outputs)
    assert result == set()


def test_alter_outputs_dissolution_benefit_administrative_removes_cert():
    """BC-family admin dissolution still suppresses the certificate."""
    filing = _filing(filing_type="dissolution", filing_sub_type="administrative",
                     json_legal_type=Business.LegalTypes.BCOMP)
    outputs = {"certificateOfDissolution"}
    result = FilingMeta.alter_outputs_dissolution(filing, outputs)
    assert "certificateOfDissolution" not in result


def test_alter_outputs_dissolution_coop_voluntary_missing_docs_no_raise():
    """certifiedRules/certifiedMemorandum may be absent; discard must not raise."""
    filing = _filing(filing_type="dissolution", filing_sub_type="voluntary",
                     json_legal_type=Business.LegalTypes.COOP)
    outputs = {"certificateOfDissolution"}
    result = FilingMeta.alter_outputs_dissolution(filing, outputs)
    assert result == {"certificateOfDissolution"}


def test_alter_outputs_special_resolution_missing_docs_no_raise():
    """certifiedMemorandum/certifiedRules may be absent; discard must not raise."""
    filing = _filing(filing_type="specialResolution",
                     meta_data={"legalFilings": [], "alteration": {}})
    outputs = set()
    result = FilingMeta.alter_outputs_special_resolution(filing, outputs)
    assert result == set()


def test_alter_outputs_special_resolution_removes_memorandum_keeps_new_rules():
    """Memorandum always suppressed; rules kept when uploadNewRules is set."""
    filing = _filing(filing_type="specialResolution",
                     meta_data={"legalFilings": ["changeOfName"], "alteration": {"uploadNewRules": True}})
    outputs = {"certifiedMemorandum", "certifiedRules"}
    result = FilingMeta.alter_outputs_special_resolution(filing, outputs)
    assert "certifiedMemorandum" not in result
    assert "certifiedRules" in result
    assert "certificateOfNameChange" in result
