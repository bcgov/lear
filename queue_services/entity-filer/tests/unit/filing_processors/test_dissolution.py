# Copyright © 2019 Province of British Columbia
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
"""The Unit Tests for the Voluntary Dissolution filing."""
import copy
import io
from datetime import datetime
import pytz

import pytest

from legal_api.models import Business, Office, OfficeType, Party, PartyRole, Filing
from legal_api.models.document import DocumentType
from legal_api.services.minio import MinioService
from registry_schemas.example_data import DISSOLUTION, FILING_HEADER
from entity_filer.filing_meta import FilingMeta
from tests.utils import upload_file, assert_pdf_contains_text, has_expected_date_str_format

from entity_filer.filing_processors import dissolution
from tests.unit import create_business, create_filing


@pytest.mark.parametrize('legal_type,identifier,dissolution_type', [
    ('BC', 'BC1234567', 'voluntary'),
    ('BEN', 'BC1234567', 'voluntary'),
    ('CC', 'BC1234567', 'voluntary'),
    ('ULC', 'BC1234567', 'voluntary'),
    ('LLC', 'BC1234567', 'voluntary'),
    ('CP', 'CP1234567', 'voluntary'),
    ('BC', 'BC1234567', 'administrative'),
    ('SP', 'FM1234567', 'administrative'),
    ('GP', 'FM1234567', 'administrative'),
])
def test_dissolution(app, session, minio_server, legal_type, identifier, dissolution_type):
    """Assert that the dissolution is processed."""
    # setup
    filing_json = copy.deepcopy(FILING_HEADER)
    dissolution_date = '2018-04-08'
    has_liabilities = False
    filing_json['filing']['header']['name'] = 'dissolution'

    filing_json['filing']['business']['identifier'] = identifier
    filing_json['filing']['business']['legalType'] = legal_type

    filing_json['filing']['dissolution'] = DISSOLUTION
    filing_json['filing']['dissolution']['dissolutionDate'] = dissolution_date
    filing_json['filing']['dissolution']['dissolutionType'] = dissolution_type
    filing_json['filing']['dissolution']['hasLiabilities'] = has_liabilities

    if legal_type == Business.LegalTypes.COOP.value:
        affidavit_uploaded_by_user_file_key = upload_file('affidavit.pdf')
        filing_json['filing']['dissolution']['affidavitFileKey'] = affidavit_uploaded_by_user_file_key
        filing_json['filing']['dissolution']['affidavitFileName'] = 'affidavit.pdf'

    business = create_business(identifier, legal_type=legal_type)
    member = Party(
        first_name='Michael',
        last_name='Crane',
        middle_initial='Joe',
        title='VP',
    )
    member.save()
    # sanity check
    assert member.id
    party_role = PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        appointment_date=datetime(2017, 5, 17),
        cessation_date=None,
        party_id=member.id,
        business_id=business.id
    )
    party_role.save()
    curr_roles = len(business.party_roles.all())

    business.dissolution_date = None
    business_id = business.id

    filing_meta = FilingMeta()
    filing = create_filing('123', filing_json)

    # test
    dissolution.process(business, filing_json['filing'], filing, filing_meta)
    business.save()

    # validate
    assert business.dissolution_date == filing.effective_date
    assert business.state == Business.State.HISTORICAL
    assert business.state_filing_id == filing.id
    assert len(business.party_roles.all()) == 2
    assert len(filing.filing_party_roles.all()) == 1

    custodial_office = session.query(Business, Office). \
            filter(Business.id == Office.business_id). \
            filter(Business.id == business_id). \
            filter(Office.office_type == OfficeType.CUSTODIAL). \
            one_or_none()
    assert custodial_office

    if filing_json['filing']['business']['legalType'] == Business.LegalTypes.COOP.value:
        documents = business.documents.all()
        assert len(documents) == 1
        assert documents[0].type == DocumentType.AFFIDAVIT.value
        affidavit_key = filing_json['filing']['dissolution']['affidavitFileKey']
        assert documents[0].file_key == affidavit_key
        assert MinioService.get_file(documents[0].file_key)
        affidavit_obj = MinioService.get_file(affidavit_key)
        assert affidavit_obj
        assert_pdf_contains_text('Filed on ', affidavit_obj.read())

    assert filing_meta.dissolution['dissolutionType'] == dissolution_type

    dissolution_date_str = datetime.date(filing.effective_date).isoformat()
    dissolution_date_format_correct = has_expected_date_str_format(dissolution_date_str, '%Y-%m-%d')
    assert dissolution_date_format_correct
    assert filing_meta.dissolution['dissolutionDate'] == dissolution_date_str


@pytest.mark.parametrize('legal_type,identifier,dissolution_type', [
    ('SP', 'FM1234567', 'administrative'),
    ('GP', 'FM1234567', 'administrative'),
])
def test_administrative_dissolution(app, session, minio_server, legal_type, identifier, dissolution_type):
    """Assert that the dissolution is processed."""
    # setup
    filing_json = copy.deepcopy(FILING_HEADER)
    dissolution_date = '2018-04-08'
    has_liabilities = False
    filing_json['filing']['header']['name'] = 'dissolution'

    filing_json['filing']['business']['identifier'] = identifier
    filing_json['filing']['business']['legalType'] = legal_type

    filing_json['filing']['dissolution'] = DISSOLUTION
    filing_json['filing']['dissolution']['dissolutionDate'] = dissolution_date
    filing_json['filing']['dissolution']['dissolutionType'] = dissolution_type
    filing_json['filing']['dissolution']['hasLiabilities'] = has_liabilities
    filing_json['filing']['dissolution']['details'] = 'Some Details here'

    if legal_type == Business.LegalTypes.COOP.value:
        affidavit_uploaded_by_user_file_key = upload_file('affidavit.pdf')
        filing_json['filing']['dissolution']['affidavitFileKey'] = affidavit_uploaded_by_user_file_key
        filing_json['filing']['dissolution']['affidavitFileName'] = 'affidavit.pdf'

    business = create_business(identifier, legal_type=legal_type)
    member = Party(
        first_name='Michael',
        last_name='Crane',
        middle_initial='Joe',
        title='VP',
    )
    member.save()
    # sanity check
    assert member.id
    party_role = PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        appointment_date=datetime(2017, 5, 17),
        cessation_date=None,
        party_id=member.id,
        business_id=business.id
    )
    party_role.save()
    curr_roles = len(business.party_roles.all())

    business.dissolution_date = None
    business_id = business.id

    filing_meta = FilingMeta()
    filing = create_filing('123', filing_json)
    filing_id = filing.id

    # test
    dissolution.process(business, filing_json['filing'], filing, filing_meta)
    business.save()

    # validate
    assert business.dissolution_date == filing.effective_date
    assert business.state == Business.State.HISTORICAL
    assert business.state_filing_id == filing.id
    assert len(business.party_roles.all()) == 2
    assert len(filing.filing_party_roles.all()) == 1

    custodial_office = session.query(Business, Office). \
            filter(Business.id == Office.business_id). \
            filter(Business.id == business_id). \
            filter(Office.office_type == OfficeType.CUSTODIAL). \
            one_or_none()
    assert custodial_office

    if filing_json['filing']['business']['legalType'] == Business.LegalTypes.COOP.value:
        documents = business.documents.all()
        assert len(documents) == 1
        assert documents[0].type == DocumentType.AFFIDAVIT.value
        affidavit_key = filing_json['filing']['dissolution']['affidavitFileKey']
        assert documents[0].file_key == affidavit_key
        assert MinioService.get_file(documents[0].file_key)
        affidavit_obj = MinioService.get_file(affidavit_key)
        assert affidavit_obj
        assert_pdf_contains_text('Filed on ', affidavit_obj.read())

    assert filing_meta.dissolution['dissolutionType'] == dissolution_type

    dissolution_date_str = datetime.date(filing.effective_date).isoformat()
    dissolution_date_format_correct = has_expected_date_str_format(dissolution_date_str, '%Y-%m-%d')
    assert dissolution_date_format_correct
    assert filing_meta.dissolution['dissolutionDate'] == dissolution_date_str

    final_filing = Filing.find_by_id(filing_id)
    assert filing_json['filing']['dissolution']['details'] == final_filing.order_details
