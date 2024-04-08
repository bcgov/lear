# Copyright © 2020 Province of British Columbia
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
"""The Unit Tests for the Incorporation filing."""

import copy
import random
from datetime import datetime
from unittest.mock import patch

import pytest
from business_model import BusinessCommon, DocumentType, Filing, LegalEntity
from business_model.models.colin_event_id import ColinEventId
from registry_schemas.example_data import INCORPORATION_FILING_TEMPLATE

from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors import incorporation_filing
from entity_filer.filing_processors.filing_components import legal_entity_info
from tests.unit import create_filing, nested_session

COOP_INCORPORATION_FILING_TEMPLATE = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
del COOP_INCORPORATION_FILING_TEMPLATE["filing"]["incorporationApplication"]["offices"]["recordsOffice"]
del COOP_INCORPORATION_FILING_TEMPLATE["filing"]["incorporationApplication"]["parties"][1]
del COOP_INCORPORATION_FILING_TEMPLATE["filing"]["incorporationApplication"]["shareStructure"]
del COOP_INCORPORATION_FILING_TEMPLATE["filing"]["incorporationApplication"]["incorporationAgreement"]
COOP_INCORPORATION_FILING_TEMPLATE["filing"]["incorporationApplication"]["nameRequest"]["legalType"] = "CP"
COOP_INCORPORATION_FILING_TEMPLATE["filing"]["incorporationApplication"]["cooperative"] = {
    "cooperativeAssociationType": "CP",
    "rulesFileKey": "cooperative/fa00c6bf-eaad-4a07-a3d2-4786ecd6b83b.jpg",
    "memorandumFileKey": "cooperative/f722bf16-86be-430d-928d-5529853a3a2c.pdf",
}

INCORPORATION_FILING_TEMPLATE = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
INCORPORATION_FILING_TEMPLATE["filing"]["incorporationApplication"]["courtOrder"] = {
    "fileNumber": "12356",
    "effectOfOrder": "planOfArrangement",
    "hasPlanOfArrangement": True,
}


@pytest.mark.parametrize(
    "legal_type, filing, next_corp_num ",
    [
        ("BC", copy.deepcopy(INCORPORATION_FILING_TEMPLATE), "BC0001095"),
        ("BEN", copy.deepcopy(INCORPORATION_FILING_TEMPLATE), "BC0001095"),
        ("CP", copy.deepcopy(COOP_INCORPORATION_FILING_TEMPLATE), "CP0001095"),
        ("ULC", copy.deepcopy(INCORPORATION_FILING_TEMPLATE), "BC0001095"),
        ("CC", copy.deepcopy(INCORPORATION_FILING_TEMPLATE), "BC0001095"),
    ],
)
def test_incorporation_filing_process_with_nr(app, session, legal_type, filing, next_corp_num):
    """Assert that the incorporation object is correctly populated to model objects."""
    # setup
    with nested_session(session):
        with patch.object(
            legal_entity_info, "get_next_corp_num", return_value=next_corp_num
        ) as mock_get_next_corp_num:  # noqa F841
            identifier = "NR 1234567"
            filing["filing"]["incorporationApplication"]["nameRequest"]["nrNumber"] = identifier
            filing["filing"]["incorporationApplication"]["nameRequest"]["legalType"] = legal_type
            filing["filing"]["incorporationApplication"]["nameRequest"]["legalName"] = "Test"
            if legal_type in ("BC", "BEN", "ULC"):
                del filing["filing"]["incorporationApplication"]["courtOrder"]
            # if legal_type == 'CP':
            #     rules_file_key_uploaded_by_user = upload_file('rules.pdf')
            #     memorandum_file_key_uploaded_by_user = upload_file('memorandum.pdf')
            #     filing['filing']['incorporationApplication']['cooperative']['rulesFileKey'] = \
            #         rules_file_key_uploaded_by_user
            #     filing['filing']['incorporationApplication']['cooperative']['memorandumFileKey'] = \
            #         memorandum_file_key_uploaded_by_user
            create_filing("123", filing)

            effective_date = datetime.utcnow()
            filing_rec = Filing(effective_date=effective_date, filing_json=filing)
            filing_meta = FilingMeta(application_date=effective_date)

            # test
            business, filing_rec, filing_meta = incorporation_filing.process(None, filing, filing_rec, filing_meta)

            # Assertions
            assert business.identifier == next_corp_num
            assert business.founding_date.replace(tzinfo=None) == effective_date
            assert business.entity_type == filing["filing"]["incorporationApplication"]["nameRequest"]["legalType"]
            assert business.state == BusinessCommon.State.ACTIVE
            entity_roles = business.entity_roles.all()
            if legal_type in ("BC", "BEN", "ULC", "CC"):
                assert business.legal_name == filing["filing"]["incorporationApplication"]["nameRequest"]["legalName"]
                assert len(entity_roles) == 2
                assert len(filing_rec.filing_entity_roles.all()) == 3
                assert len(business.share_classes.all()) == 2
                assert len(business.offices.all()) == 2  # One office is created in create_business method.
            if legal_type == "CC":
                assert business.legal_name == filing["filing"]["incorporationApplication"]["nameRequest"]["legalName"]
                assert len(entity_roles) == 2
                assert filing_rec.court_order_file_number == "12356"
                assert filing_rec.court_order_effect_of_order == "planOfArrangement"
            if legal_type == "CP":
                assert business.legal_name == filing["filing"]["incorporationApplication"]["nameRequest"]["legalName"]
                assert len(entity_roles) == 1
                assert len(filing_rec.filing_entity_roles.all()) == 2
                assert len(business.offices.all()) == 1
                # documents = business.documents.all()
                # assert len(documents) == 2
                # for document in documents:
                #     if document.type == DocumentType.COOP_RULES.value:
                #         original_rules_key = filing['filing']['incorporationApplication']['cooperative']['rulesFileKey']  # noqa E501; line too long
                #         assert document.file_key == original_rules_key
                #         assert MinioService.get_file(document.file_key)
                #     elif document.type == DocumentType.COOP_MEMORANDUM.value:
                #         original_memorandum_key = \
                #             filing['filing']['incorporationApplication']['cooperative']['memorandumFileKey']
                #         assert document.file_key == original_memorandum_key
                #         assert MinioService.get_file(document.file_key)
                # rules_files_obj = MinioService.get_file(rules_file_key_uploaded_by_user)
                # assert rules_files_obj
                # assert_pdf_contains_text('Filed on ', rules_files_obj.read())
                # memorandum_file_obj = MinioService.get_file(memorandum_file_key_uploaded_by_user)
                # assert memorandum_file_obj
                # assert_pdf_contains_text('Filed on ', memorandum_file_obj.read())

        all_calls = mock_get_next_corp_num.mock_calls
        assert all_calls
        assert len(all_calls) > 0
        all_calls[0].assert_called_with(filing['filing']['incorporationApplication']['nameRequest']['legalType'])


@pytest.mark.parametrize(
    "legal_type, filing, legal_name_suffix",
    [
        ("BC", copy.deepcopy(INCORPORATION_FILING_TEMPLATE), "B.C. LTD."),
        ("BEN", copy.deepcopy(INCORPORATION_FILING_TEMPLATE), "B.C. LTD."),
        (
            "ULC",
            copy.deepcopy(INCORPORATION_FILING_TEMPLATE),
            "B.C. UNLIMITED LIABILITY COMPANY",
        ),
        (
            "CC",
            copy.deepcopy(INCORPORATION_FILING_TEMPLATE),
            "B.C. COMMUNITY CONTRIBUTION COMPANY LTD.",
        ),
    ],
)
def test_incorporation_filing_process_no_nr(app, session, legal_type, filing, legal_name_suffix):
    """Assert that the incorporation object is correctly populated to model objects."""
    # setup
    next_corp_num = "BC0001095"
    with patch.object(
        legal_entity_info, "get_next_corp_num", return_value=next_corp_num
    ) as mock_get_next_corp_num:  # noqa F841
        filing["filing"]["incorporationApplication"]["nameRequest"]["legalType"] = legal_type
        create_filing("123", filing)

        effective_date = datetime.utcnow()
        filing_rec = Filing(effective_date=effective_date, filing_json=filing)
        filing_meta = FilingMeta(application_date=filing_rec.effective_date)

        # test
        business, filing_rec, filing_meta = incorporation_filing.process(None, filing, filing_rec, filing_meta)

        # Assertions
        assert business.identifier == next_corp_num
        assert business.founding_date.replace(tzinfo=None) == effective_date
        assert business.entity_type == legal_type
        assert business.legal_name == f"{business.identifier[2:]} {legal_name_suffix}"
        assert len(business.share_classes.all()) == 2
        assert len(business.offices.all()) == 2  # One office is created in create_business method.
        assert len(business.entity_roles.all()) == 2
        assert len(filing_rec.filing_entity_roles.all()) == 3
        assert filing_rec.court_order_file_number == "12356"
        assert filing_rec.court_order_effect_of_order == "planOfArrangement"

        # Parties
        parties = filing_rec.filing_json["filing"]["incorporationApplication"]["parties"]
        assert parties[0]["officer"]["firstName"] == "Joe"
        assert parties[0]["officer"]["lastName"] == "Swanson"
        assert parties[0]["officer"]["middleName"] == "P"
        assert parties[0]["officer"]["partyType"] == "person"
        assert parties[1]["officer"]["partyType"] == "organization"
        assert parties[1]["officer"]["organizationName"] == "Xyz Inc."

    all_calls = mock_get_next_corp_num.mock_calls
    assert all_calls
    assert len(all_calls) > 0
    all_calls[0].assert_called_with(filing['filing']['incorporationApplication']['nameRequest']['legalType'])


@pytest.mark.parametrize(
    "test_name, legal_type, response, expected",
    [
        ("short number", "BEN", "1234", "BC0001234"),
        ("full 9 number", "BEN", "1234567", "BC1234567"),
        ("too big number", "BEN", "12345678", None),
    ],
)
def test_get_next_corp_num(requests_mock, app, session, test_name, legal_type, response, expected):
    """Assert that the corpnum is the correct format."""
    from flask import current_app

    with nested_session(session):
        current_app.config["COLIN_API"] = "http://localhost"
        requests_mock.post(f'{current_app.config["COLIN_API"]}/BC', json={"corpNum": response})

        with patch.object(LegalEntity, "get_next_value_from_sequence", return_value=response):
            corp_num = legal_entity_info.get_next_corp_num(legal_type)

        assert corp_num == expected


def test_incorporation_filing_coop_from_colin(app, session):
    """Assert that an existing coop incorporation is loaded corrrectly."""
    # setup
    corp_num = "CP0000001"
    nr_num = "NR 1234567"
    colind_id = random.randint(1, 1000)
    filing = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)

    # Change the template to be a CP == Cooperative
    filing["filing"]["business"]["legalType"] = "CP"
    filing["filing"]["business"]["identifier"] = corp_num
    filing["filing"]["incorporationApplication"]["nameRequest"]["legalType"] = "CP"
    filing["filing"]["incorporationApplication"]["nameRequest"]["legalName"] = "Test"
    filing["filing"]["incorporationApplication"]["nameRequest"]["nrNumber"] = nr_num
    filing["filing"]["incorporationApplication"].pop("shareStructure")
    effective_date = datetime.utcnow()
    # Create the Filing obeject in the DB
    filing_rec = Filing(effective_date=effective_date, filing_json=filing)
    colin_event = ColinEventId()
    colin_event.colin_event_id = colind_id
    filing_rec.colin_event_ids.append(colin_event)
    # Override the state setting mechanism
    filing_rec.skip_status_listener = True
    filing_rec._status = "PENDING"
    filing_rec.save()
    filing_meta = FilingMeta(application_date=filing_rec.effective_date)

    # test
    business, filing_rec, filing_meta = incorporation_filing.process(None, filing, filing_rec, filing_meta)

    # Assertions
    assert business.identifier == corp_num
    assert business.founding_date.replace(tzinfo=None) == effective_date
    assert business.entity_type == filing["filing"]["incorporationApplication"]["nameRequest"]["legalType"]
    assert business.legal_name == "Test"
    assert len(business.offices.all()) == 2  # One office is created in create_business method.


@pytest.mark.parametrize(
    "legal_type, legal_name_suffix",
    [
        ("BC", "B.C. LTD."),
        ("ULC", "B.C. UNLIMITED LIABILITY COMPANY"),
        ("CC", "B.C. COMMUNITY CONTRIBUTION COMPANY LTD."),
    ],
)
def test_incorporation_filing_bc_company_from_colin(app, session, legal_type, legal_name_suffix):
    """Assert that an existing bc company(LTD, ULC, CCC) incorporation is loaded corrrectly."""
    # setup
    with nested_session(session):
        corp_num = "BC0000001"
        colind_id = random.randint(1, 1000)
        filing = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)

        # Change the template to be LTD, ULC or CCC
        filing["filing"]["business"]["legalType"] = legal_type
        filing["filing"]["business"]["identifier"] = corp_num
        filing["filing"]["incorporationApplication"]["nameRequest"]["legalType"] = legal_type
        effective_date = datetime.utcnow()
        # Create the Filing object in the DB
        filing_rec = Filing(effective_date=effective_date, filing_json=filing)
        colin_event = ColinEventId()
        colin_event.colin_event_id = colind_id
        filing_rec.colin_event_ids.append(colin_event)
        # Override the state setting mechanism
        filing_rec.skip_status_listener = True
        filing_rec._status = "PENDING"
        filing_rec.save()
        filing_meta = FilingMeta(application_date=filing_rec.effective_date)

        # test
        business, filing_rec, filing_meta = incorporation_filing.process(
            None, filing, filing_rec, filing_meta=filing_meta
        )

        # Assertions
        assert business.identifier == corp_num
        assert business.founding_date.replace(tzinfo=None) == effective_date
        assert business.entity_type == filing["filing"]["incorporationApplication"]["nameRequest"]["legalType"]
        assert business.legal_name == f"{business.identifier[2:]} {legal_name_suffix}"
        assert len(business.offices.all()) == 2  # One office is created in create_business method.
        assert len(business.share_classes.all()) == 2
        assert len(business.entity_roles.all()) == 2
