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
"""The Unit Tests for the continuation in filing."""

import copy
from datetime import datetime, timezone, timezone
from http import HTTPStatus
from unittest.mock import patch

from business_model.models import Business, Document, DocumentType, Filing
from business_filer.common.legislation_datetime import LegislationDatetime
from registry_schemas.example_data import CONTINUATION_IN_FILING_TEMPLATE

from business_filer.filing_processors.filing_components import business_info, business_profile
from business_filer.services.filer import process_filing
from tests.unit import create_filing
from business_filer.common.filing_message import FilingMessage


def test_continuation_in_process(app, session):
    """Assert that the continuation in object is correctly populated to model objects."""
    filing_type = 'continuationIn'
    nr_identifier = 'NR 1234567'
    next_corp_num = 'C0001095'

    filing = copy.deepcopy(CONTINUATION_IN_FILING_TEMPLATE)
    filing['filing'][filing_type]['nameRequest']['nrNumber'] = nr_identifier
    filing['filing'][filing_type]['nameTranslations'] = [{'name': 'ABCD Ltd.'}]
    filing_rec = create_filing('123', filing)
    effective_date = datetime.now(timezone.utc)
    filing_rec.effective_date = effective_date
    filing_rec.save()

    filing_msg = FilingMessage(filing_identifier=filing_rec.id)

    # test
    with patch.object(business_info, 'get_next_corp_num', return_value=next_corp_num):
        with patch.object(business_profile, 'update_business_profile', return_value=HTTPStatus.OK):
            process_filing(filing_msg)

    # Assertions
    filing_rec = Filing.find_by_id(filing_rec.id)
    business = Business.find_by_identifier(next_corp_num)

    assert filing_rec.business_id == business.id
    assert filing_rec.status == Filing.Status.COMPLETED.value
    assert business.identifier
    assert business.founding_date == effective_date
    assert business.legal_type == filing['filing'][filing_type]['nameRequest']['legalType']
    assert business.legal_name == filing['filing'][filing_type]['nameRequest']['legalName']
    assert business.state == Business.State.ACTIVE

    assert len(business.share_classes.all()) == len(filing['filing'][filing_type]['shareStructure']['shareClasses'])
    assert len(business.offices.all()) == len(filing['filing'][filing_type]['offices'])
    assert len(business.aliases.all()) == len(filing['filing'][filing_type]['nameTranslations'])
    assert business.party_roles[0].role == 'director'
    assert filing_rec.filing_party_roles[0].role == 'completing_party'

    # verify foreign jurisdiction
    assert len(business.jurisdictions.all()) == 1
    jurisdiction = business.jurisdictions.all()[0]
    foreign_jurisdiction = filing['filing'][filing_type]['foreignJurisdiction']
    assert jurisdiction.country == foreign_jurisdiction.get('country')
    assert jurisdiction.region == foreign_jurisdiction.get('region')

    assert filing_rec.meta_data[filing_type]['country'] == jurisdiction.country
    assert filing_rec.meta_data[filing_type]['region'] == jurisdiction.region

    assert jurisdiction.legal_name == foreign_jurisdiction.get('legalName')
    assert jurisdiction.identifier == foreign_jurisdiction.get('identifier')
    assert jurisdiction.incorporation_date == LegislationDatetime.as_utc_timezone_from_legislation_date_str(
        foreign_jurisdiction.get('incorporationDate'))
    assert jurisdiction.tax_id == foreign_jurisdiction.get('taxId')

    if expro_business := filing['filing'][filing_type].get('business'):
        assert jurisdiction.expro_identifier == expro_business.get('identifier')
        assert jurisdiction.expro_legal_name == expro_business.get('legalName')

    assert jurisdiction.filing_id == filing_rec.id

    documents = Document.find_all_by(filing_rec.id, DocumentType.DIRECTOR_AFFIDAVIT.value)
    assert len(documents) == 1
    assert documents[0].file_key == foreign_jurisdiction.get('affidavitFileKey')
    assert filing_rec.meta_data[filing_type]['affidavitFileKey'] == foreign_jurisdiction.get('affidavitFileKey')

    documents = Document.find_all_by(filing_rec.id, DocumentType.AUTHORIZATION_FILE.value)
    authorization_files = filing['filing'][filing_type]['authorization'].get('files', [])
    assert len(documents) == len(authorization_files)
    for document in documents:
        file = next(x for x in authorization_files if x.get('fileKey') == document.file_key)
        assert file.get('fileName') == document.file_name

        authorization_files = filing_rec.meta_data[filing_type]['authorizationFiles']
        file = next(x for x in authorization_files if x.get('fileKey') == document.file_key)
        assert file.get('fileName') == document.file_name
