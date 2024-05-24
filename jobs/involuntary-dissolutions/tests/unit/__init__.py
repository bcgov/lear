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