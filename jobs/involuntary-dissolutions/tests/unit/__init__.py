import datetime
from legal_api.models import (
    Batch,
    BatchProcessing,
    Business,
)

EPOCH_DATETIME = datetime.datetime.utcfromtimestamp(0).replace(tzinfo=datetime.timezone.utc)
FROZEN_DATETIME = datetime.datetime(2001, 8, 5, 7, 7, 58, 272362).replace(tzinfo=datetime.timezone.utc)

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

    business.save()
    return business

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
                             step = BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1,
                             status = BatchProcessing.BatchProcessingStatus.PROCESSING,
                             notes = ''):
    batch_processing = BatchProcessing(
        batch_id = batch_id,
        business_id = business_id,
        business_identifier = identifier,
        step = step,
        status = status,
        notes = notes
    )
    batch_processing.save()
    return batch_processing