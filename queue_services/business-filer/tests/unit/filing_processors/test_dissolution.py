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
from datedelta import datedelta
from datetime import datetime

import pytest

from business_model.models import BatchProcessing, Batch, Business, Office, OfficeType, Party, PartyRole, Filing
from business_model.models.document import DocumentType
# from legal_api.services.minio import MinioService
from business_filer.common.legislation_datetime import LegislationDatetime

from registry_schemas.example_data import DISSOLUTION, FILING_HEADER
from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors import dissolution
from business_filer.worker import process_filing

from tests.unit import create_business, create_filing
# from tests.utils import upload_file, assert_pdf_contains_text, has_expected_date_str_format


@pytest.mark.parametrize('legal_type,identifier,dissolution_type', [
    ('BC', 'BC1234567', 'involuntary'),
    ('BEN', 'BC1234567', 'involuntary'),
    ('CC', 'BC1234567', 'involuntary'),
    ('ULC', 'BC1234567', 'involuntary'),
    ('LLC', 'BC1234567', 'involuntary'),
    ('CP', 'CP1234567', 'involuntary'),
    ('SP', 'FM1234567', 'involuntary'),
    ('GP', 'FM1234567', 'involuntary'),
    ('BC', 'BC1234567', 'voluntary'),
    ('BEN', 'BC1234567', 'voluntary'),
    ('CC', 'BC1234567', 'voluntary'),
    ('ULC', 'BC1234567', 'voluntary'),
    ('LLC', 'BC1234567', 'voluntary'),
    ('CP', 'CP1234567', 'voluntary'),
    ('SP', 'FM1234567', 'voluntary'),
    ('GP', 'FM1234567', 'voluntary'),
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

    # if legal_type == Business.LegalTypes.COOP.value:
    #     affidavit_uploaded_by_user_file_key = upload_file('affidavit.pdf')
    #     filing_json['filing']['dissolution']['affidavitFileKey'] = affidavit_uploaded_by_user_file_key

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

    if dissolution_type == 'involuntary':
        batch = Batch(
            batch_type=Batch.BatchType.INVOLUNTARY_DISSOLUTION,
            status=Batch.BatchStatus.PROCESSING,
            size=1,
        )
        batch.save()
        batch_processing = BatchProcessing(
            batch_id=batch.id,
            business_id=business.id,
            filing_id=filing.id,
            business_identifier=business.identifier,
            step=BatchProcessing.BatchProcessingStep.DISSOLUTION,
            status=BatchProcessing.BatchProcessingStatus.QUEUED,
            created_date=datetime.utcnow()-datedelta(days=42),
            trigger_date=datetime.utcnow(),
            last_modified=datetime.utcnow()
        )
        batch_processing.save()

    # test
    dissolution.process(business, filing_json['filing'], filing, filing_meta, True)
    business.save()

    # validate
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
        # assert MinioService.get_file(documents[0].file_key)
        # affidavit_obj = MinioService.get_file(affidavit_key)
        # assert affidavit_obj
        # assert_pdf_contains_text('Filed on ', affidavit_obj.read())

    assert filing_meta.dissolution['dissolutionType'] == dissolution_type
    if dissolution_type == 'involuntary':
        assert batch_processing
        assert batch_processing.status == BatchProcessing.BatchProcessingStatus.COMPLETED

    expected_dissolution_date = filing.effective_date
    if dissolution_type == 'voluntary' and business.legal_type in (Business.LegalTypes.SOLE_PROP.value,
                                                                   Business.LegalTypes.PARTNERSHIP.value):
        expected_dissolution_date = datetime.fromisoformat(f'{dissolution_date}T07:00:00+00:00')

    expected_dissolution_date_str = LegislationDatetime.format_as_legislation_date(expected_dissolution_date)
    assert business.dissolution_date == expected_dissolution_date
    # dissolution_date_format_correct = has_expected_date_str_format(expected_dissolution_date_str, '%Y-%m-%d')
    assert dissolution_date_format_correct
    assert filing_meta.dissolution['dissolutionDate'] == expected_dissolution_date_str


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

    # if legal_type == Business.LegalTypes.COOP.value:
    #     affidavit_uploaded_by_user_file_key = upload_file('affidavit.pdf')
    #     filing_json['filing']['dissolution']['affidavitFileKey'] = affidavit_uploaded_by_user_file_key

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
        # assert MinioService.get_file(documents[0].file_key)
        # affidavit_obj = MinioService.get_file(affidavit_key)
        # assert affidavit_obj
        # assert_pdf_contains_text('Filed on ', affidavit_obj.read())

    assert filing_meta.dissolution['dissolutionType'] == dissolution_type

    dissolution_date_str = LegislationDatetime.format_as_legislation_date(filing.effective_date)
    # dissolution_date_format_correct = has_expected_date_str_format(dissolution_date_str, '%Y-%m-%d')
    assert dissolution_date_format_correct
    assert filing_meta.dissolution['dissolutionDate'] == dissolution_date_str

    final_filing = Filing.find_by_id(filing_id)
    assert filing_json['filing']['dissolution']['details'] == final_filing.order_details


@pytest.mark.parametrize('dissolution_type', [
    ('administrative'),
    ('involuntary'),
    ('voluntary'),
])
async def test_amalgamation_administrative_dissolution(app, session, mocker, dissolution_type):
    """Assert that the dissolution is processed."""
    from tests.unit.test_worker.test_amalgamation_application import test_regular_amalgamation_application_process
    identifier = await test_regular_amalgamation_application_process(app, session)
    # setup
    dissolution_filing_json = copy.deepcopy(FILING_HEADER)
    dissolution_filing_json['filing']['header']['name'] = 'dissolution'
    dissolution_filing_json['filing']['dissolution'] = DISSOLUTION
    dissolution_filing_json['filing']['dissolution']['dissolutionDate'] = '2018-04-08'
    dissolution_filing_json['filing']['dissolution']['dissolutionType'] = dissolution_type
    dissolution_filing_json['filing']['dissolution']['hasLiabilities'] = False
    dissolution_filing_json['filing']['dissolution']['details'] = 'Some Details here'

    business = Business.find_by_identifier(identifier)
    filing = create_filing('123', dissolution_filing_json, business_id=business.id)
    filing.effective_date = datetime.now()
    filing.save()

    # test
    filing_msg = {'filing': {'id': filing.id}}

    
    # mock out the email sender and event publishing
    mocker.patch('entity_filer.worker.publish_email_message', return_value=None)
    mocker.patch('entity_filer.worker.publish_event', return_value=None)
    mocker.patch('legal_api.services.bootstrap.AccountService.update_entity', return_value=None)

    await process_filing(filing_msg, app)

    # validate
    business = Business.find_by_identifier(identifier)
    assert business.state == Business.State.HISTORICAL
    assert business.state_filing_id == filing.id
    if dissolution_type == 'administrative':
        assert not business.amalgamation.one_or_none()
    else:
        amalgamation = business.amalgamation.one_or_none()
        assert amalgamation
        assert amalgamation.amalgamating_businesses.all()
