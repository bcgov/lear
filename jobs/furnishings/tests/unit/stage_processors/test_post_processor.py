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
from legal_api.models import BatchProcessing, Furnishing, FurnishingGroup, XmlPayload

from furnishings.stage_processors.post_processor import PostProcessor, process

from .. import factory_batch, factory_batch_processing, factory_business, factory_furnishing


def helper_create_furnishings(identifiers: list):
    """Test helper to create furnishings for post processing."""
    furnishings = []
    for identifier in identifiers:
        business = factory_business(identifier=identifier)
        batch = factory_batch()
        factory_batch_processing(
            batch_id=batch.id,
            business_id=business.id,
            identifier=business.identifier,
            step=BatchProcessing.BatchProcessingStep.WARNING_LEVEL_2
        )
        furnishing = factory_furnishing(
            batch_id=batch.id,
            business_id=business.id,
            identifier=business.identifier,
            furnishing_name=Furnishing.FurnishingName.INTENT_TO_DISSOLVE,
            furnishing_type=Furnishing.FurnishingType.GAZETTE,
            business_name=business.legal_name
        )
        furnishings.append(furnishing)
    return furnishings


def test_process(app, session):
    """Assert that FurnishingGroup and XmlPayload entry are created correctly."""
    furnishings = helper_create_furnishings(['BC1234567'])
    furnishing_dict = {
        Furnishing.FurnishingName.INTENT_TO_DISSOLVE: furnishings
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


def test_processor_format_furnishings(app, session):
    """Assert that furnishing details are formated/sorted correctly."""
    furnishings = helper_create_furnishings(['BC7654321', 'BC1234567'])
    name = Furnishing.FurnishingName.INTENT_TO_DISSOLVE
    furnishing_dict = {
        name: furnishings
    }

    processor = PostProcessor(app, furnishing_dict)
    processor._format_furnishings()

    assert processor._xml_data
    assert processor._xml_data['furnishings'][name]['items']
    furnishing_items = processor._xml_data['furnishings'][name]['items']
    assert furnishing_items[0] == furnishings[1]
    assert furnishing_items[1] == furnishings[0]
