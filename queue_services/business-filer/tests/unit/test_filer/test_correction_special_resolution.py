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
import io
import random

import pytest
from dateutil.parser import parse
from business_model.models import Business, Document, Filing, PartyRole
from business_model.models.document import DocumentType
# from legal_api.services.minio import MinioService
from registry_schemas.example_data import CORRECTION_COA, CORRECTION_CP_SPECIAL_RESOLUTION,\
                                        CP_SPECIAL_RESOLUTION_TEMPLATE, FILING_HEADER
from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors import correction
from business_filer.services.filer import process_filing
from tests.unit import create_entity, create_filing
# from tests.utils import upload_file, assert_pdf_contains_text


@pytest.mark.parametrize(
    'test_name, correct_filing_type, filing_template, correction_template',
    [
        ('sr_correction', 'specialResolution',
         CP_SPECIAL_RESOLUTION_TEMPLATE, CORRECTION_CP_SPECIAL_RESOLUTION)
    ]
)
async def test_special_resolution_correction(app, session, mocker, test_name, correct_filing_type,
                                             filing_template, correction_template):
    """Test the special resolution correction functionality."""
    return None
    # class MockFileResponse:
    #     """Mock the MinioService."""

    #     def __init__(self, file_content):
    #         self.data = io.BytesIO(file_content.encode('utf-8'))

    # # Mock the MinioService's get_file method to return a dictionary with 'data' pointing
    # # to an instance of MockFileResponse
    # mocker.patch('legal_api.services.minio.MinioService.get_file', return_value=MockFileResponse('fake file content'))
    # mocker.patch('business_filer.services.filer.publish_email_message', return_value=None)
    # mocker.patch('business_filer.services.filer.publish_event', return_value=None)
    # mocker.patch('business_filer.filing_processors.filing_components.name_request.consume_nr', return_value=None)
    # mocker.patch('business_filer.filing_processors.filing_components.business_profile.update_business_profile',
    #              return_value=None)
    # mocker.patch('business_filer.services.AccountService.update_entity', return_value=None)

    # # Create business
    # identifier = 'CP1234567'
    # coop_associate_type = 'HC'
    # business = create_entity(identifier, 'CP', 'COOP INC.')
    # business_id = business.id
    # business.association_type = 'OC'
    # business.save()

    # # Create an initial special resolution filing
    # sr_filing = copy.deepcopy(filing_template)
    # sr_payment_id = str(random.SystemRandom().getrandbits(0x58))
    # sr_filing_id = (create_filing(sr_payment_id, sr_filing, business_id=business_id)).id

    # # Mock the filing message
    # sr_filing_msg = {'filing': {'id': sr_filing_id}}
    # # Call the process_filing method for the original special resolution
    # await process_filing(sr_filing_msg, app)

    # if correct_filing_type == 'changeOfAddress':
    #     correction_data = copy.deepcopy(correction_template)
    #     correction_data['filing']['changeOfAddress']['offices'] = {}
    #     correction_data['filing']['correction']['correctedFilingId'] = sr_filing_id
    # else:
    #     # Simulate a correction filing
    #     correction_data = copy.deepcopy(FILING_HEADER)
    #     correction_data['filing']['correction'] = copy.deepcopy(correction_template)
    #     correction_data['filing']['header']['name'] = 'correction'
    #     correction_data['filing']['business'] = {'identifier': identifier}
    #     correction_data['filing']['correction']['correctedFilingType'] = correct_filing_type
    #     correction_data['filing']['correction']['resolution'] = '<p>xxxx</p>'
    #     correction_data['filing']['correction']['signatory'] = {
    #         'givenName': 'Joey',
    #         'familyName': 'Doe',
    #         'additionalName': ''
    #     }
    #     correction_data['filing']['correction']['cooperativeAssociationType'] = 'HC'
    #     # Update correction data to point to the original special resolution filing
    #     if 'correction' not in correction_data['filing']:
    #         correction_data['filing']['correction'] = {}
    #     correction_data['filing']['correction']['correctedFilingId'] = sr_filing_id
    # correction_payment_id = str(random.SystemRandom().getrandbits(0x58))
    # correction_filing_id = (create_filing(correction_payment_id, correction_data, business_id=business_id)).id

    # # Mock the correction filing message
    # correction_filing_msg = {'filing': {'id': correction_filing_id}}

    # # Call the process_filing method for the correction
    # await process_filing(correction_filing_msg, app)

    # # Assertions

    # business = Business.find_by_internal_id(business_id)

    # assert len(business.resolutions.all()) == 1
    # resolution = business.resolutions.first()
    # assert business.association_type == 'HC'
    # assert resolution is not None, 'Resolution should exist'
    # assert resolution.resolution == '<p>xxxx</p>', 'Resolution text should be corrected'

    # # # # Check if the signatory was updated
    # party = resolution.party
    # assert party is not None, 'Party should exist'
    # assert party.first_name == 'JOEY', 'First name should be corrected'
    # assert party.last_name == 'DOE', 'Last name should be corrected'

    # # Check outcome
    # final_filing = Filing.find_by_id(correction_filing_id)
    # alteration = final_filing.meta_data.get('correction', {})
    # assert business.association_type == coop_associate_type
    # assert alteration.get('fromCooperativeAssociationType') == 'OC'
    # assert alteration.get('toCooperativeAssociationType') == coop_associate_type

    # # Simulate another correction filing on previous correction
    # resolution_date = '2023-06-16'
    # signing_date = '2023-06-17'
    # correction_data_2 = copy.deepcopy(FILING_HEADER)
    # correction_data_2['filing']['correction'] = copy.deepcopy(CORRECTION_CP_SPECIAL_RESOLUTION)
    # correction_data_2['filing']['header']['name'] = 'correction'
    # correction_data_2['filing']['business'] = {'identifier': identifier}
    # correction_data_2['filing']['correction']['correctedFilingType'] = 'correction'
    # correction_data_2['filing']['correction']['resolution'] = '<p>yyyy</p>'
    # correction_data_2['filing']['correction']['resolutionDate'] = resolution_date
    # correction_data_2['filing']['correction']['signingDate'] = signing_date
    # correction_data_2['filing']['correction']['signatory'] = {
    #     'givenName': 'Sarah',
    #     'familyName': 'Doe',
    #     'additionalName': ''
    # }
    # # Update correction data to point to the original special resolution filing
    # if 'correction' not in correction_data_2['filing']:
    #     correction_data_2['filing']['correction'] = {}
    # correction_data_2['filing']['correction']['correctedFilingId'] = correction_filing_id
    # correction_payment_id_2 = str(random.SystemRandom().getrandbits(0x58))
    # correction_filing_id_2 = (create_filing(correction_payment_id_2, correction_data_2, business_id=business_id)).id
    # # Mock the correction filing message
    # correction_filing_msg_2 = {'filing': {'id': correction_filing_id_2}}
    # await process_filing(correction_filing_msg_2, app)

    # # Assertions
    # business = Business.find_by_internal_id(business_id)
    # resolution = business.resolutions.first()
    # assert resolution is not None, 'Resolution should exist'
    # assert resolution.resolution == '<p>yyyy</p>', 'Resolution text should be corrected'
    # assert resolution.resolution_date == parse(resolution_date).date()
    # assert resolution.signing_date == parse(signing_date).date()

    # # # Check if the signatory was updated
    party = resolution.party
    assert party is not None, 'Party should exist'
    assert party.first_name == 'SARAH', 'First name should be corrected'
    assert party.last_name == 'DOE', 'Last name should be corrected'


# def test_correction_coop_rules(app, session):
#     """Assert that the coop rules and memorandum is altered."""
#     # Create business
#     identifier = 'CP1234567'
#     business = create_entity(identifier, 'CP', 'COOP INC.')
#     business_id = business.id
#     business.save()

#     # Create an initial special resolution filing
#     sr_filing = copy.deepcopy(CP_SPECIAL_RESOLUTION_TEMPLATE)
#     sr_payment_id = str(random.SystemRandom().getrandbits(0x58))
#     sr_filing_id = (create_filing(sr_payment_id, sr_filing, business_id=business_id)).id

#     # Mock the filing message
#     sr_filing_msg = {'filing': {'id': sr_filing_id}}
#     # Call the process_filing method for the original special resolution
#     process_filing(sr_filing_msg, app)

#     correction_filing = copy.deepcopy(FILING_HEADER)
#     correction_filing['filing']['header']['name'] = 'correction'
#     correction_filing['filing']['business']['legalType'] = Business.LegalTypes.COOP.value
#     correction_filing['filing']['correction'] = copy.deepcopy(CORRECTION_CP_SPECIAL_RESOLUTION)
#     correction_filing['filing']['correction']['correctedFilingId'] = sr_filing_id
#     rules_file_key_uploaded_by_user = upload_file('rules.pdf')
#     correction_filing['filing']['correction']['rulesFileKey'] = rules_file_key_uploaded_by_user
#     correction_filing['filing']['correction']['rulesFileName'] = 'rules.pdf'
#     memorandum_file_key_uploaded_by_user = upload_file('memorandum.pdf')
#     correction_filing['filing']['correction']['memorandumFileKey'] = memorandum_file_key_uploaded_by_user
#     correction_filing['filing']['correction']['memorandumFileName'] = 'memorandum.pdf'

#     payment_id = str(random.SystemRandom().getrandbits(0x58))

#     filing_submission = create_filing(
#         payment_id, correction_filing, business_id=business.id, filing_date=datetime.datetime.utcnow()
#     )

#     filing_meta = FilingMeta()

#     # test
#     correction.process(correction_filing=filing_submission,
#                        filing=correction_filing['filing'],
#                        filing_meta=filing_meta,
#                        business=business)

#     business.save()

#     rules_document = session.query(Document). \
#         filter(Document.filing_id == filing_submission.id). \
#         filter(Document.type == DocumentType.COOP_RULES.value). \
#         one_or_none()

#     assert rules_document.file_key == correction_filing['filing']['correction']['rulesFileKey']
#     assert MinioService.get_file(rules_document.file_key)
#     rules_files_obj = MinioService.get_file(rules_file_key_uploaded_by_user)
#     assert rules_files_obj
#     assert_pdf_contains_text('Filed on ', rules_files_obj.read())
    
#     memorandum_document = session.query(Document). \
#         filter(Document.filing_id == filing_submission.id). \
#         filter(Document.type == DocumentType.COOP_MEMORANDUM.value). \
#         one_or_none()

#     assert memorandum_document.file_key == correction_filing['filing']['correction']['memorandumFileKey']
#     assert MinioService.get_file(memorandum_document.file_key)
#     memorandum_files_obj = MinioService.get_file(memorandum_file_key_uploaded_by_user)
#     assert memorandum_files_obj
#     assert_pdf_contains_text('Filed on ', memorandum_files_obj.read())
