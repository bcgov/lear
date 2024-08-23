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
import pytest

from legal_api.models import BatchProcessing, Furnishing, FurnishingGroup, XmlPayload

from furnishings.stage_processors.post_processor import PostProcessor, process

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
    ]
)
def test_process(app, session, test_name, furnishing_name, step):
    """Assert that FurnishingGroup and XmlPayload entry are created correctly."""
    furnishings = helper_create_furnishings(['BC1234567'], furnishing_name, step)
    furnishing_dict = {
        furnishing_name: furnishings
    }
    process(app, furnishing_dict)

    furnishing = furnishings[0]
    assert furnishing.status == Furnishing.FurnishingStatus.PROCESSED

    furnishing_group_id = furnishing.furnishing_group_id
    assert furnishing_group_id
    furnishing_group = FurnishingGroup.find_by_id(furnishing_group_id)
    assert furnishing_group

    xml_payload_id = furnishing_group.xml_payload_id
    assert xml_payload_id
    xml_payload = XmlPayload.find_by_id(xml_payload_id)
    assert xml_payload
    assert xml_payload.payload


def test_process_combined_xml(app, session):
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
    process(app, furnishing_dict)

    furnishing_stage_2 = furnishings_stage_2[0]
    assert furnishing_stage_2.status == Furnishing.FurnishingStatus.PROCESSED

    furnishing_stage_3 = furnishings_stage_3[0]
    assert furnishing_stage_3.status == Furnishing.FurnishingStatus.PROCESSED

    furnishing_group_id = furnishing_stage_2.furnishing_group_id
    assert furnishing_group_id
    assert furnishing_group_id == furnishing_stage_3.furnishing_group_id
    furnishing_group = FurnishingGroup.find_by_id(furnishing_group_id)
    assert furnishing_group

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
    ]
)
def test_processor_format_furnishings(app, session, test_name, furnishing_name, step):
    """Assert that furnishing details are formated/sorted correctly."""
    furnishings = helper_create_furnishings(
        ['BC7654321', 'BC1234567'],
        furnishing_name,
        step
    )

    furnishing_dict = {
        furnishing_name: furnishings,
    }

    processor = PostProcessor(app, furnishing_dict)
    processor._format_furnishings()

    assert processor._xml_data
    assert processor._xml_data['furnishings'][furnishing_name]['items']

    furnishing_items = processor._xml_data['furnishings'][furnishing_name]['items']
    assert furnishing_items[0] == furnishings[1]
    assert furnishing_items[1] == furnishings[0]
