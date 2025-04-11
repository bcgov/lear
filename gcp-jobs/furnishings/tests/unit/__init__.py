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
"""The Test-Suite used to ensure that the Furnishings Job is working correctly."""
import base64
import uuid
from datetime import UTC, datetime

from datedelta import datedelta
from freezegun import freeze_time

from business_model.models import Address, Batch, BatchProcessing, Business, Filing, Furnishing, db
from business_model.models.colin_event_id import ColinEventId
from business_model.models.db import VersioningProxy

from .test_data.gotenburg_response import GOTENBURG_RESPONSE

EPOCH_DATETIME = datetime.utcfromtimestamp(0).replace(tzinfo=UTC)
FROZEN_DATETIME = datetime(2001, 8, 5, 7, 7, 58, 272362).replace(tzinfo=UTC)


def factory_business(identifier,
                     founding_date=EPOCH_DATETIME,
                     last_ar_date=None,
                     entity_type=Business.LegalTypes.COMP.value,
                     state=Business.State.ACTIVE,
                     admin_freeze=False,
                     no_dissolution=False):
    """Create a business."""
    last_ar_year = None
    if last_ar_date:
        last_ar_year = last_ar_date.year
    business = Business(legal_name=f"legal_name-{identifier}",
                        founding_date=founding_date,
                        last_ar_date=last_ar_date,
                        last_ar_year=last_ar_year,
                        identifier=identifier,
                        legal_type=entity_type,
                        state=state,
                        admin_freeze=admin_freeze,
                        no_dissolution=no_dissolution)
    business.save()
    return business


def factory_batch(batch_type=Batch.BatchType.INVOLUNTARY_DISSOLUTION,
                  status=Batch.BatchStatus.PROCESSING,
                  size=3,
                  notes=""):
    """Create a batch."""
    batch = Batch(
        batch_type=batch_type,
        status=status,
        size=size,
        notes=notes
    )
    batch.save()
    return batch


def factory_batch_processing(batch_id,
                             business_id,
                             identifier,
                             step=BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1,
                             status=BatchProcessing.BatchProcessingStatus.PROCESSING,
                             created_date=datetime.now(UTC),
                             trigger_date=datetime.now(UTC)+datedelta(days=42),
                             last_modified=datetime.now(UTC),
                             notes=""):
    """Create a batch processing entry."""
    batch_processing = BatchProcessing(
        batch_id=batch_id,
        business_id=business_id,
        business_identifier=identifier,
        step=step,
        status=status,
        created_date=created_date,
        trigger_date=trigger_date,
        last_modified=last_modified,
        notes=notes
    )
    batch_processing.save()
    return batch_processing


def factory_completed_filing(business,
                             data_dict,
                             filing_date=FROZEN_DATETIME,
                             payment_token=None,
                             colin_id=None,
                             filing_type=None,
                             filing_sub_type=None):
    """Create a completed filing."""
    if not payment_token:
        payment_token = str(base64.urlsafe_b64encode(uuid.uuid4().bytes)).replace("=", "")

    with freeze_time(filing_date):

        filing = Filing()
        filing.business_id = business.id
        filing.filing_date = filing_date
        filing.filing_json = data_dict
        if filing_type:
            filing._filing_type = filing_type
        if filing_sub_type:
            filing._filing_sub_type = filing_sub_type
        filing.save()

        transaction_id = VersioningProxy.get_transaction_id(db.session())
        filing.transaction_id = transaction_id
        filing.payment_token = payment_token
        filing.effective_date = filing_date
        filing.payment_completion_date = filing_date
        if colin_id:
            colin_event = ColinEventId()
            colin_event.colin_event_id = colin_id
            colin_event.filing_id = filing.id
            colin_event.save()
        filing.save()
    return filing


def factory_furnishing(batch_id,
                       business_id,
                       identifier,
                       furnishing_name=Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR,
                       furnishing_type=Furnishing.FurnishingType.EMAIL,
                       status=Furnishing.FurnishingStatus.QUEUED,
                       created_date=datetime.now(UTC),
                       last_modified=datetime.now(UTC),
                       last_ar_date=None,
                       business_name=None
                       ):
    """Create a furnishing entry."""
    furnishing = Furnishing(
        batch_id=batch_id,
        business_id=business_id,
        business_identifier=identifier,
        furnishing_name=furnishing_name,
        furnishing_type=furnishing_type,
        status=status,
        created_date=created_date,
        last_modified=last_modified,
        last_ar_date=last_ar_date,
        business_name=business_name
    )
    furnishing.save()
    return furnishing

def factory_address(address_type: str,
                    street="some street",
                    city="victoria",
                    country="CA",
                    postal_code="v512a9",
                    region="akjsdf",
                    business_id=None,
                    furnishings_id=None):
    """Create an address entrXy."""
    address = Address(
        address_type=address_type,
        street=street,
        city=city,
        country=country,
        postal_code=postal_code,
        region=region,
        business_id=business_id,
        furnishings_id=furnishings_id)
    address.save()
    return address

def factory_mras_response(identifier: str = "BC1234567",
                          jurisdictions: dict[str, str] = None):
    if not jurisdictions:
        jurisdictions = {"AB": "Alberta", "MB": "Manitoba"}
    xml_string = '<Jurisdictions xmlns="http://mras.ca/schema/v1">'
    for jur_id, jur_name in jurisdictions.items():
        xml_string += f"<Jurisdiction><JurisdictionID>{jur_id}</JurisdictionID><NameEn>{jur_name}</NameEn><NameFr>{jur_name}</NameFr><RedirectUrl>https://redirect.test.ca</RedirectUrl><TargetProfileID>0{identifier}</TargetProfileID></Jurisdiction>"
    xml_string += "</Jurisdictions>"
    return bytes(xml_string, "utf-8")
