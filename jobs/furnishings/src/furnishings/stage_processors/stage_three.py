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
"""Furnishings job procssing rules for stage three of involuntary dissolution."""
from datetime import datetime

from flask import Flask
from legal_api.models import Batch, BatchProcessing, Business, Furnishing, db
from sqlalchemy import exists, not_


def process(app: Flask):
    """Run process to manage and track notifications for dissolution stage three process."""
    try:
        furnishing_subquery = exists().where(
            Furnishing.batch_id == BatchProcessing.batch_id,
            Furnishing.business_id == BatchProcessing.business_id,
            Furnishing.furnishing_name.in_([
                Furnishing.FurnishingName.CORP_DISSOLVED,
                Furnishing.FurnishingName.CORP_DISSOLVED_XPRO
            ])
        )
        batch_processings = (
            db.session.query(BatchProcessing)
            .filter(BatchProcessing.status == BatchProcessing.BatchProcessingStatus.PROCESSING)
            .filter(BatchProcessing.step == BatchProcessing.BatchProcessingStep.DISSOLUTION)
            .filter(Batch.id == BatchProcessing.batch_id)
            .filter(Batch.batch_type == Batch.BatchType.INVOLUNTARY_DISSOLUTION)
            .filter(Batch.status == Batch.BatchStatus.PROCESSING)
            .filter(not_(furnishing_subquery))
        ).all()

        grouping_identifier = Furnishing.get_next_grouping_identifier()

        for batch_processing in batch_processings:
            business = batch_processing.business
            furnishing_name = (
                Furnishing.FurnishingName.CORP_DISSOLVED_XPRO
                if business.legal_type == Business.LegalTypes.EXTRA_PRO_A.value
                else Furnishing.FurnishingName.CORP_DISSOLVED
            )
            new_furnishing = Furnishing(
                furnishing_type=Furnishing.FurnishingType.GAZETTE,
                furnishing_name=furnishing_name,
                batch_id=batch_processing.batch_id,
                business_id=batch_processing.business_id,
                business_identifier=batch_processing.business_identifier,
                created_date=datetime.utcnow(),
                last_modified=datetime.utcnow(),
                status=Furnishing.FurnishingStatus.QUEUED,
                grouping_identifier=grouping_identifier,
                business_name=business.legal_name
            )
            new_furnishing.save()
        # TODO: create data files and SFTPing to BC Laws
        # TODO: mark furnishings entry processed

    except Exception as err:
        app.logger.error(err)
