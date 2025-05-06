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
"""Furnishings job processing rules for stage two of involuntary dissolution."""
from datetime import UTC, datetime

from flask import current_app
from sqlalchemy import exists, not_

from business_model.models import Batch, BatchProcessing, Business, Furnishing, db


def process(xml_furnishings: dict):
    """Run process to manage and track notifications for dissolution stage two process."""
    try:
        furnishing_subquery = exists().where(
            Furnishing.batch_id == BatchProcessing.batch_id,
            Furnishing.business_id == BatchProcessing.business_id,
            Furnishing.furnishing_name.in_([
                Furnishing.FurnishingName.INTENT_TO_DISSOLVE,
                Furnishing.FurnishingName.INTENT_TO_DISSOLVE_XPRO
            ])
        )
        batch_processings = (
            db.session.query(BatchProcessing)
            .filter(BatchProcessing.status == BatchProcessing.BatchProcessingStatus.PROCESSING)
            .filter(BatchProcessing.step == BatchProcessing.BatchProcessingStep.WARNING_LEVEL_2)
            .filter(Batch.id == BatchProcessing.batch_id)
            .filter(Batch.batch_type == Batch.BatchType.INVOLUNTARY_DISSOLUTION)
            .filter(Batch.status == Batch.BatchStatus.PROCESSING)
            .filter(not_(furnishing_subquery))
        ).all()

        bc_furnishings = []
        ep_furnishings = []

        for batch_processing in batch_processings:
            business: Business = batch_processing.business
            furnishing_name = (
                Furnishing.FurnishingName.INTENT_TO_DISSOLVE_XPRO
                if business.legal_type == Business.LegalTypes.EXTRA_PRO_A.value
                else Furnishing.FurnishingName.INTENT_TO_DISSOLVE
            )
            new_furnishing = Furnishing(
                furnishing_type=Furnishing.FurnishingType.GAZETTE,
                furnishing_name=furnishing_name,
                batch_id=batch_processing.batch_id,
                business_id=batch_processing.business_id,
                business_identifier=batch_processing.business_identifier,
                created_date=datetime.now(UTC),
                last_modified=datetime.now(UTC),
                status=Furnishing.FurnishingStatus.QUEUED,
                business_name=business.legal_name
            )
            new_furnishing.save()
            current_app.logger.debug(
                f"Created intent to dissolve furnishing entry for {new_furnishing.business_identifier} "
                f"with ID: {new_furnishing.id}"
            )

            if business.legal_type != Business.LegalTypes.EXTRA_PRO_A.value:
                bc_furnishings.append(new_furnishing)
            else:
                ep_furnishings.append(new_furnishing)

        if bc_furnishings:
            xml_furnishings[Furnishing.FurnishingName.INTENT_TO_DISSOLVE] = bc_furnishings

        if ep_furnishings:
            xml_furnishings[Furnishing.FurnishingName.INTENT_TO_DISSOLVE_XPRO] = ep_furnishings

    except Exception as err:
        current_app.logger.error(err)
