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
"""The Unit Tests for the Amalgamation application filing."""

import copy
from datetime import datetime, timezone
from http import HTTPStatus
from unittest.mock import patch

import pytest
from business_model import Amalgamation, Filing, LegalEntity
from registry_schemas.example_data import AMALGAMATION_APPLICATION

from entity_filer.filing_processors.filing_components import legal_entity_info
from entity_filer.resources.worker import process_filing
from entity_filer.resources.worker import FilingMessage
from tests.unit import create_entity, create_filing


def test_amalgamation_application_process(app, session):
    """Assert that the amalgamation application object is correctly populated to model objects."""
    filing_type = "amalgamationApplication"
    amalgamating_identifier_1 = "BC9891234"
    amalgamating_identifier_2 = "BC9891235"
    nr_identifier = "NR 1234567"
    next_corp_num = "BC0001095"

    amalgamating_business_1_id = create_entity(amalgamating_identifier_1, "BC", "amalgamating business 1").id
    amalgamating_business_2_id = create_entity(amalgamating_identifier_2, "BC", "amalgamating business 2").id

    filing = {"filing": {}}
    filing["filing"]["header"] = {
        "name": filing_type,
        "date": "2019-04-08",
        "certifiedBy": "full name",
        "email": "no_one@never.get",
        "filingId": 1,
    }
    filing["filing"][filing_type] = copy.deepcopy(AMALGAMATION_APPLICATION)
    filing["filing"][filing_type]["amalgamatingBusinesses"] = [
        {"role": "amalgamating", "identifier": amalgamating_identifier_1},
        {"role": "amalgamating", "identifier": amalgamating_identifier_2},
    ]

    filing["filing"][filing_type]["nameRequest"]["nrNumber"] = nr_identifier

    filing_rec = create_filing("123", filing)
    effective_date = datetime.now(timezone.utc)
    filing_rec.effective_date = effective_date
    filing_rec.save()

    # test
    filing_msg = FilingMessage(filing_identifier=filing.id)
    with patch.object(legal_entity_info, "get_next_corp_num", return_value=next_corp_num):
        process_filing(filing_msg)

    # Assertions
    filing_rec = Filing.find_by_id(filing_rec.id)
    business = LegalEntity.find_by_identifier(next_corp_num)

    assert filing_rec.legal_entity_id == business.id
    assert filing_rec.status == Filing.Status.COMPLETED.value
    assert business.identifier
    assert business.founding_date == effective_date
    assert business.entity_type == filing["filing"][filing_type]["nameRequest"]["legalType"]
    assert business.legal_name == filing["filing"][filing_type]["nameRequest"]["legalName"]
    assert business.state == LegalEntity.State.ACTIVE

    assert len(business.share_classes.all()) == len(filing["filing"][filing_type]["shareStructure"]["shareClasses"])
    assert len(business.offices.all()) == len(filing["filing"][filing_type]["offices"])
    assert len(business.aliases.all()) == len(filing["filing"][filing_type]["nameTranslations"])
    assert business.party_roles[0].role == "director"
    assert filing_rec.filing_party_roles[0].role == "completing_party"

    assert business.amalgamation
    amalgamation: Amalgamation = business.amalgamation[0]
    assert amalgamation.amalgamation_date == effective_date
    assert amalgamation.filing_id == filing_rec.id
    assert amalgamation.amalgamation_type.name == filing["filing"][filing_type]["type"]
    assert amalgamation.court_approval == filing["filing"][filing_type]["courtApproval"]

    for amalgamating_business in amalgamation.amalgamating_businesses:
        assert amalgamating_business.role.name == "amalgamating"
        assert amalgamating_business.legal_entity_id in [amalgamating_business_1_id, amalgamating_business_2_id]
        dissolved_business = LegalEntity.find_by_internal_id(amalgamating_business.legal_entity_id)
        assert dissolved_business.state == LegalEntity.State.HISTORICAL
        assert dissolved_business.state_filing_id == filing_rec.id
        assert dissolved_business.dissolution_date == effective_date
