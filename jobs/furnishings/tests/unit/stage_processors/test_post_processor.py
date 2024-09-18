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
from unittest.mock import patch

import pytest
from legal_api.models import BatchProcessing, Furnishing, FurnishingGroup, XmlPayload
from legal_api.utils.legislation_datetime import LegislationDatetime

from furnishings.stage_processors.post_processor import PostProcessor

from .. import factory_batch, factory_batch_processing, factory_business, factory_furnishing


def helper_create_furnishings(identifiers: list, furnishing_name, step):
    """Test helper to create furnishings for post processing."""
    furnishings = []
    for identifier in identifiers:
        business = factory_business(identifier=identifier)
        batch = factory_batch()
        factory_batch_processing(
            batch_id=batch.id,
            business_id=business.id,
            identifier=business.identifier,
            step=step
        )
        furnishing = factory_furnishing(
            batch_id=batch.id,
            business_id=business.id,
            identifier=business.identifier,
            furnishing_name=furnishing_name,
            furnishing_type=Furnishing.FurnishingType.GAZETTE,
            business_name=business.legal_name
        )
        furnishings.append(furnishing)
    return furnishings

@pytest.mark.parametrize(
    'test_name, furnishing_name, step', [
        (
            'STAGE_2_BC',
            Furnishing.FurnishingName.INTENT_TO_DISSOLVE,
            BatchProcessing.BatchProcessingStep.WARNING_LEVEL_2
        ),
        (
            'STAGE_2_EP',
            Furnishing.FurnishingName.INTENT_TO_DISSOLVE_XPRO,
            BatchProcessing.BatchProcessingStep.WARNING_LEVEL_2
        ),
        (
            'STAGE_3_BC',
            Furnishing.FurnishingName.CORP_DISSOLVED,
            BatchProcessing.BatchProcessingStep.DISSOLUTION
        ),
        (
            'STAGE_3_EP',
            Furnishing.FurnishingName.CORP_DISSOLVED_XPRO,
            BatchProcessing.BatchProcessingStep.DISSOLUTION
        ),
    ]
)
def test_processor(app, session, sftpserver, sftpconnection, test_name, furnishing_name, step):
    """Assert that FurnishingGroup and XmlPayload entry are created correctly."""
    furnishings = helper_create_furnishings(['BC1234567'], furnishing_name, step)
    furnishing_dict = {
        furnishing_name: furnishings
    }

    processor = PostProcessor(app, furnishing_dict)
    with sftpserver.serve_content({app.config.get('BCLAWS_SFTP_STORAGE_DIRECTORY'): {}}):
        with patch.object(processor, '_bclaws_sftp_connection', new=sftpconnection):
            with patch.object(processor, '_disable_bclaws_sftp', new=False):
                processor.process()
                # assert xml file is uploaded
                with sftpconnection as sftpclient:
                    assert len(sftpclient.listdir(app.config.get('BCLAWS_SFTP_STORAGE_DIRECTORY'))) == 1

    # assert the furnishings are marked as processed
    furnishing = furnishings[0]
    assert furnishing.status == Furnishing.FurnishingStatus.PROCESSED

    # assert the furnishing group is created
    furnishing_group_id = furnishing.furnishing_group_id
    assert furnishing_group_id
    furnishing_group = FurnishingGroup.find_by_id(furnishing_group_id)
    assert furnishing_group

    # assert xml payload is generated
    xml_payload_id = furnishing_group.xml_payload_id
    assert xml_payload_id
    xml_payload = XmlPayload.find_by_id(xml_payload_id)
    assert xml_payload
    assert xml_payload.payload


def test_processor_combined_xml(app, session, sftpserver, sftpconnection):
    """Assert that FurnishingGroup and XmlPayload entry are created correctly for both stages at once."""
    furnishing_name_stage_2 = Furnishing.FurnishingName.INTENT_TO_DISSOLVE
    furnishings_stage_2 = helper_create_furnishings(
        ['BC2222222'],
        furnishing_name_stage_2,
        BatchProcessing.BatchProcessingStep.WARNING_LEVEL_2
    )

    furnishing_name_stage_3 = Furnishing.FurnishingName.CORP_DISSOLVED
    furnishings_stage_3 = helper_create_furnishings(
        ['BC3333333'],
        furnishing_name_stage_3,
        BatchProcessing.BatchProcessingStep.DISSOLUTION
    )

    furnishing_dict = {
        furnishing_name_stage_2: furnishings_stage_2,
        furnishing_name_stage_3: furnishings_stage_3
    }

    processor = PostProcessor(app, furnishing_dict)
    with sftpserver.serve_content({app.config.get('BCLAWS_SFTP_STORAGE_DIRECTORY'): {}}):
        with patch.object(processor, '_bclaws_sftp_connection', new=sftpconnection):
            with patch.object(processor, '_disable_bclaws_sftp', new=False):
                processor.process()
                # assert xml file is uploaded
                with sftpconnection as sftpclient:
                    assert len(sftpclient.listdir(app.config.get('BCLAWS_SFTP_STORAGE_DIRECTORY'))) == 1


    # assert the furnishings are marked as processed
    furnishing_stage_2 = furnishings_stage_2[0]
    assert furnishing_stage_2.status == Furnishing.FurnishingStatus.PROCESSED
    furnishing_stage_3 = furnishings_stage_3[0]
    assert furnishing_stage_3.status == Furnishing.FurnishingStatus.PROCESSED

    # assert the furnishing group is created
    furnishing_group_id = furnishing_stage_2.furnishing_group_id
    assert furnishing_group_id
    assert furnishing_group_id == furnishing_stage_3.furnishing_group_id
    furnishing_group = FurnishingGroup.find_by_id(furnishing_group_id)
    assert furnishing_group

    # assert xml payload is generated
    xml_payload_id = furnishing_group.xml_payload_id
    assert xml_payload_id
    xml_payload = XmlPayload.find_by_id(xml_payload_id)
    assert xml_payload
    assert xml_payload.payload


@pytest.mark.parametrize(
    'test_name, furnishing_name, step', [
        (
            'STAGE_2_BC',
            Furnishing.FurnishingName.INTENT_TO_DISSOLVE,
            BatchProcessing.BatchProcessingStep.WARNING_LEVEL_2
        ),
        (
            'STAGE_2_EP',
            Furnishing.FurnishingName.INTENT_TO_DISSOLVE_XPRO,
            BatchProcessing.BatchProcessingStep.WARNING_LEVEL_2
        ),
        (
            'STAGE_3_BC',
            Furnishing.FurnishingName.CORP_DISSOLVED,
            BatchProcessing.BatchProcessingStep.DISSOLUTION
        ),
        (
            'STAGE_3_EP',
            Furnishing.FurnishingName.CORP_DISSOLVED_XPRO,
            BatchProcessing.BatchProcessingStep.DISSOLUTION
        ),
    ]
)
def test_processor_format_furnishings(app, session, test_name, furnishing_name, step):
    """Assert that furnishing details are formated/sorted correctly."""
    processed_date = LegislationDatetime.now()
    furnishings = helper_create_furnishings(
        ['BC7654321', 'BC1234567'],
        furnishing_name,
        step
    )

    furnishing_dict = {
        furnishing_name: furnishings,
    }

    xml_data = PostProcessor._format_furnishings(furnishing_dict, processed_date)

    assert xml_data
    assert xml_data['furnishings'][furnishing_name]['items']

    furnishing_items = xml_data['furnishings'][furnishing_name]['items']
    assert furnishing_items[0] == furnishings[1]
    assert furnishing_items[1] == furnishings[0]
