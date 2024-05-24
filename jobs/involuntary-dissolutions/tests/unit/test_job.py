import os
import psycopg2
import pytest

from datetime import datetime

from involuntary_dissolutions import create_app, initiate_dissolution_process
from legal_api.models import Configuration, Batch, BatchProcessing, Business
from tests import factory_business, factory_batch, factory_batch_processing
from unittest.mock import patch

def test_connection_failed():
    status = False
    try:
        connection = psycopg2.connect(user=os.getenv('FAKE_DATABASE_USERNAME', ''),
                                      password=os.getenv('FAKE_DATABASE_PASSWORD', ''),
                                      host=os.getenv('FAKE_DATABASE_HOST', ''),
                                      port=os.getenv('FAKE_DATABASE_PORT', '5432'),
                                      database=os.getenv('FAKE_DATABASE_NAME', ''))

        cursor = connection.cursor()
        status = True
    except Exception:
        status = False
    finally:
        assert status == False


def test_database_connection_succeed():
    status = False
    try:
        connection = psycopg2.connect(user=os.getenv('DATABASE_USERNAME', ''),
                                      password=os.getenv('DATABASE_PASSWORD', ''),
                                      host=os.getenv('DATABASE_HOST', ''),
                                      port=os.getenv('DATABASE_PORT', '5432'),
                                      database=os.getenv('DATABASE_NAME', ''))
        cursor = connection.cursor()
        status = True
    except Exception:
        status = False
    finally:
        assert status == True


def test_batch_already_ran_today():
    application = create_app()
    with application.app_context():
        factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.COMP.value)

        # first run
        initiate_dissolution_process(application)
        batches = Batch.find_by(batch_type=Batch.BatchType.INVOLUNTARY_DISSOLUTION)
        assert batches.count() == 1

        # second run
        initiate_dissolution_process(application)
        batches = Batch.find_by(batch_type=Batch.BatchType.INVOLUNTARY_DISSOLUTION)
        assert not batches.count() > 1


def test_batch_cron_invalid():
    application = create_app()
    with application.app_context():
        factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.COMP.value)

        # shouldn't run on a friday
        with patch.object(datetime, 'today', return_value=datetime.datetime(2024, 5, 24)):
            initiate_dissolution_process(application)
            batches = Batch.find_by(batch_type=Batch.BatchType.INVOLUNTARY_DISSOLUTION)
            assert batches.count() == 0

# TODO: test batch and batch_processing entries are created successfully for different scenarios
