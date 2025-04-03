# Copyright © 2025 Province of British Columbia
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
"""This module holds general utility functions and helpers for the main package."""
from datedelta import datedelta
import base64
import uuid
from business_common.utils.datetime import datetime
from datetime import datetime as _datetime, timezone
from contextlib import contextmanager
from freezegun import freeze_time

from business_model.models import (
    Batch,
    BatchProcessing,
    Business,
    db,
    Filing,
)

from business_model.models.db import VersioningProxy


EPOCH_DATETIME = datetime.from_date(_datetime(1970, 1, 1, tzinfo=timezone.utc))
FROZEN_DATETIME = _datetime(2001, 8, 5, 7, 7, 58, 272362, tzinfo=timezone.utc)

def factory_batch(batch_type=Batch.BatchType.INVOLUNTARY_DISSOLUTION,
                  status=Batch.BatchStatus.HOLD,
                  size=3,
                  notes=''):
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
                             trigger_date=datetime.utcnow() + datedelta(days=42),
                             notes=''
                             ):
    batch_processing = BatchProcessing(
        batch_id=batch_id,
        business_id=business_id,
        business_identifier=identifier,
        step=step,
        status=status,
        trigger_date=trigger_date,
        notes=notes
    )
    batch_processing.save()
    return batch_processing

def factory_business(identifier,
                     founding_date=EPOCH_DATETIME,
                     last_ar_date=None,
                     entity_type=Business.LegalTypes.COOP.value,
                     state=Business.State.ACTIVE,
                     naics_code=None,
                     naics_desc=None,
                     admin_freeze=False,
                     no_dissolution=False):
    """Create a business entity with a versioned business."""
    last_ar_year = None
    if last_ar_date:
        last_ar_year = last_ar_date.year
    business = Business(legal_name=f'legal_name-{identifier}',
                        founding_date=founding_date,
                        last_ar_date=last_ar_date,
                        last_ar_year=last_ar_year,
                        last_ledger_timestamp=EPOCH_DATETIME,
                        # dissolution_date=EPOCH_DATETIME,
                        identifier=identifier,
                        tax_id='BN123456789',
                        fiscal_year_end_date=FROZEN_DATETIME,
                        legal_type=entity_type,
                        state=state,
                        naics_code=naics_code,
                        naics_description=naics_desc,
                        admin_freeze=admin_freeze,
                        no_dissolution=no_dissolution)

    # Versioning business
    VersioningProxy.get_transaction_id(db.session())

    business.save()
    return business

def factory_completed_filing(business,
                             data_dict,
                             filing_date=FROZEN_DATETIME,
                             payment_token=None,
                             colin_id=None,
                             filing_type=None,
                             filing_sub_type=None):
    """Create a completed filing."""
    if not payment_token:
        payment_token = str(base64.urlsafe_b64encode(uuid.uuid4().bytes)).replace('=', '')

    with freeze_time(filing_date):

        filing = Filing()
        filing.business_id = business.id
        filing.filing_date = filing_date
        filing.filing_json = data_dict
        if filing_type:
            filing._filing_type = filing_type
        if filing_sub_type:
            filing._filing_sub_type = filing_sub_type
        
        if (filing.filing_type == 'adminFreeze' or
            (filing.filing_type == 'dissolution' and filing.filing_sub_type == 'involuntary')):
            filing.hide_in_ledger = True
        
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


def factory_pending_filing(business, data_dict, filing_date=FROZEN_DATETIME):
    """Create a pending filing."""
    filing = Filing()
    filing.business_id = business.id if business else None
    filing.filing_date = filing_date
    filing.filing_json = data_dict
    filing.payment_token = 2
    filing.save()
    return filing


@contextmanager
def nested_session(session):
    try:
        sess = session.begin_nested()
        yield sess
        sess.rollback()
    except AssertionError as err:
        raise err
    except exc.ResourceClosedError as err:
        # mean the close out of the transaction got fouled in pytest
        pass
    except Exception as err:
        raise err
    finally:
        pass
