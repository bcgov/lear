# Copyright © 2019 Province of British Columbia
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
"""The Test Suites to ensure that the worker is operating correctly."""
import datetime
import json
import random

import pytest

from tests import EPOCH_DATETIME
from tests.unit import AR_FILING, COA_FILING, COD_FILING, COMBINED_FILING, create_business, create_filing


def test_extract_payment_token():
    """Assert that the payment token can be extracted from the Queue delivered Msg."""
    from entity_filer.worker import extract_payment_token
    from stan.aio.client import Msg
    import stan.pb.protocol_pb2 as protocol

    token = {'paymentToken': {'id': 1234, 'statusCode': 'COMPLETED'}}

    msg = Msg()
    msg.proto = protocol.MsgProto
    msg.proto.data = json.dumps(token).encode('utf-8')

    assert extract_payment_token(msg) == token


def test_get_filing_by_payment_id(app, session):
    """Assert that a unique filling gets retrieved for a payment_id."""
    from entity_filer.worker import get_filing_by_payment_id

    payment_id = str(random.SystemRandom().getrandbits(0x58))

    create_filing(payment_id)

    filing = get_filing_by_payment_id(str(payment_id))

    assert filing
    assert filing.payment_token == payment_id


def test_process_filing_missing_app(app, session):
    """Assert that a filling will fail with no flask app supplied."""
    from entity_filer.worker import process_filing
    from legal_api.models import Filing

    # vars
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    identifier = 'CP1234567'

    # setup
    business = create_business(identifier)
    create_filing(payment_id, AR_FILING, business.id)
    payment_token = {'paymentToken': {'id': payment_id, 'statusCode': Filing.Status.COMPLETED.value}}

    # TEST
    with pytest.raises(Exception):
        process_filing(payment_token, flask_app=None)


def test_process_ar_filing(app, session):
    """Assert that an AR filling can be applied to the model correctly."""
    from entity_filer.worker import process_filing
    from entity_filer.worker import get_filing_by_payment_id
    from legal_api.models import Business, Filing

    # vars
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    identifier = 'CP1234567'
    agm_date = datetime.date.fromisoformat(AR_FILING['filing']['annualReport'].get('annualGeneralMeetingDate'))

    # setup
    business = create_business(identifier)
    business_id = business.id
    create_filing(payment_id, AR_FILING, business.id)
    payment_token = {'paymentToken': {'id': payment_id, 'statusCode': Filing.Status.COMPLETED.value}}

    # TEST
    process_filing(payment_token, app)

    # Get modified data
    filing = get_filing_by_payment_id(payment_id)
    business = Business.find_by_internal_id(business_id)

    # check it out
    assert filing.transaction_id
    assert filing.business_id == business_id
    assert filing.status == Filing.Status.COMPLETED.value
    assert datetime.datetime.date(business.last_agm_date) == agm_date
    assert business.last_ar_date.replace(tzinfo=None) == EPOCH_DATETIME


def test_process_coa_filing(app, session):
    """Assert that an AR filling can be applied to the model correctly."""
    from entity_filer.worker import process_filing
    from entity_filer.worker import get_filing_by_payment_id
    from legal_api.models import Business, Filing

    # vars
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    identifier = 'CP1234567'
    new_delivery_address = COA_FILING['filing']['changeOfAddress']['deliveryAddress']
    new_mailing_address = COA_FILING['filing']['changeOfAddress']['mailingAddress']

    # setup
    business = create_business(identifier)
    business_id = business.id
    create_filing(payment_id, COA_FILING, business.id)
    payment_token = {'paymentToken': {'id': payment_id, 'statusCode': Filing.Status.COMPLETED.value}}

    # TEST
    process_filing(payment_token, app)

    # Get modified data
    filing = get_filing_by_payment_id(payment_id)
    business = Business.find_by_internal_id(business_id)

    # check it out
    assert filing.transaction_id
    assert filing.business_id == business_id
    assert filing.status == Filing.Status.COMPLETED.value

    delivery_address = business.delivery_address.one_or_none().json
    for key in delivery_address.keys():
        if key != 'addressType':
            assert delivery_address[key] == new_delivery_address[key]

    mailing_address = business.mailing_address.one_or_none().json
    for key in mailing_address.keys():
        if key != 'addressType':
            assert mailing_address[key] == new_mailing_address[key]


def test_process_cod_filing(app, session):
    """Assert that an AR filling can be applied to the model correctly."""
    from entity_filer.worker import process_filing
    from entity_filer.worker import get_filing_by_payment_id
    from legal_api.models import Address, Business, Director, Filing
    from legal_api.resources.business import DirectorResource

    # vars
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    identifier = 'CP1234567'
    end_date = datetime.datetime.utcnow().date()
    director_address = Address(
        street=COD_FILING['filing']['changeOfDirectors']['directors'][3]['deliveryAddress']['streetAddress'],
        city=COD_FILING['filing']['changeOfDirectors']['directors'][3]['deliveryAddress']['addressCity'],
        country=COD_FILING['filing']['changeOfDirectors']['directors'][3]['deliveryAddress']['addressCountry'],
        postal_code=COD_FILING['filing']['changeOfDirectors']['directors'][3]['deliveryAddress']['postalCode'],
        region=COD_FILING['filing']['changeOfDirectors']['directors'][3]['deliveryAddress']['addressRegion'],
    )
    director_address.save()
    director = Director(
        first_name=COD_FILING['filing']['changeOfDirectors']['directors'][3]['officer']['firstName'],
        last_name=COD_FILING['filing']['changeOfDirectors']['directors'][3]['officer']['lastName'],
        middle_initial=COD_FILING['filing']['changeOfDirectors']['directors'][3]['officer']['middleInitial'],
        appointment_date=COD_FILING['filing']['changeOfDirectors']['directors'][3]['appointmentDate'],
        cessation_date=None,
        delivery_address=director_address
    )
    director.save()
    director_id = director.id
    # list of active/ceased directors in test filing
    active_directors = []
    ceased_directors = []
    for filed_director in COD_FILING['filing']['changeOfDirectors']['directors']:
        if filed_director.get('cessationDate'):
            ceased_directors.append(filed_director['officer']['firstName'])
        else:
            active_directors.append(filed_director['officer']['firstName'])

    # setup
    business = create_business(identifier)
    business.directors.append(director)
    business.save()
    # check that adding the director during setup was successful
    directors = Director.get_active_directors(business.id, end_date)
    assert len(directors) == 1
    assert directors[0].first_name == COD_FILING['filing']['changeOfDirectors']['directors'][3]['officer']['firstName']
    business_id = business.id
    create_filing(payment_id, COD_FILING, business.id)
    payment_token = {'paymentToken': {'id': payment_id, 'statusCode': Filing.Status.COMPLETED.value}}

    # TEST
    process_filing(payment_token, app)

    # Get modified data
    filing = get_filing_by_payment_id(payment_id)
    business = Business.find_by_internal_id(business_id)

    # check it out
    assert filing.transaction_id
    assert filing.business_id == business_id
    assert filing.status == Filing.Status.COMPLETED.value

    directors = Director.get_active_directors(business.id, end_date)
    assert len(directors) == 3
    for director in directors:
        # check that director in setup is not in the list (should've been ceased)
        assert director.id != director_id
        assert director.first_name not in ceased_directors
        assert director.first_name in active_directors
        active_directors.remove(director.first_name)
        # check returned only active directors
        assert director.cessation_date is None
        assert director.appointment_date
        assert director.delivery_address
        assert director.first_name == director.delivery_address.delivery_instructions

    # check added all active directors in filing
    assert active_directors == []
    # check cessation date set on ceased director
    assert DirectorResource._get_director(business, director_id)[0]['director']['cessationDate'] is not None


def test_process_combined_filing(app, session):
    """Assert that an AR filling can be applied to the model correctly."""
    from entity_filer.worker import process_filing
    from entity_filer.worker import get_filing_by_payment_id
    from legal_api.models import Address, Business, Director, Filing
    from legal_api.resources.business import DirectorResource

    # vars
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    identifier = 'CP1234567'
    agm_date = datetime.date.fromisoformat(COMBINED_FILING['filing']['annualReport'].get('annualGeneralMeetingDate'))
    new_delivery_address = COMBINED_FILING['filing']['changeOfAddress']['deliveryAddress']
    new_mailing_address = COMBINED_FILING['filing']['changeOfAddress']['mailingAddress']
    end_date = datetime.datetime.utcnow().date()
    director_address = Address(
        street=COMBINED_FILING['filing']['changeOfDirectors']['directors'][3]['deliveryAddress']['streetAddress'],
        city=COMBINED_FILING['filing']['changeOfDirectors']['directors'][3]['deliveryAddress']['addressCity'],
        country=COMBINED_FILING['filing']['changeOfDirectors']['directors'][3]['deliveryAddress']['addressCountry'],
        postal_code=COMBINED_FILING['filing']['changeOfDirectors']['directors'][3]['deliveryAddress']['postalCode'],
        region=COMBINED_FILING['filing']['changeOfDirectors']['directors'][3]['deliveryAddress']['addressRegion'],
    )
    director_address.save()
    director = Director(
        first_name=COMBINED_FILING['filing']['changeOfDirectors']['directors'][3]['officer']['firstName'],
        last_name=COMBINED_FILING['filing']['changeOfDirectors']['directors'][3]['officer']['lastName'],
        middle_initial=COMBINED_FILING['filing']['changeOfDirectors']['directors'][3]['officer']['middleInitial'],
        appointment_date=COMBINED_FILING['filing']['changeOfDirectors']['directors'][3]['appointmentDate'],
        cessation_date=None,
        delivery_address=director_address
    )
    director.save()
    director_id = director.id
    # list of active/ceased directors in test filing
    active_directors = []
    ceased_directors = []
    for filed_director in COMBINED_FILING['filing']['changeOfDirectors']['directors']:
        if filed_director.get('cessationDate'):
            ceased_directors.append(filed_director['officer']['firstName'])
        else:
            active_directors.append(filed_director['officer']['firstName'])

    # setup
    business = create_business(identifier)
    business.directors.append(director)
    business.save()
    # check that adding the director during setup was successful
    directors = Director.get_active_directors(business.id, end_date)
    assert len(directors) == 1
    assert directors[0].first_name == COD_FILING['filing']['changeOfDirectors']['directors'][3]['officer']['firstName']
    business_id = business.id
    create_filing(payment_id, COMBINED_FILING, business.id)
    payment_token = {'paymentToken': {'id': payment_id, 'statusCode': Filing.Status.COMPLETED.value}}

    # TEST
    process_filing(payment_token, app)

    # Get modified data
    filing = get_filing_by_payment_id(payment_id)
    business = Business.find_by_internal_id(business_id)

    # check it out
    assert filing.transaction_id
    assert filing.business_id == business_id
    assert filing.status == Filing.Status.COMPLETED.value
    assert datetime.datetime.date(business.last_agm_date) == agm_date
    assert business.last_ar_date.replace(tzinfo=None) == EPOCH_DATETIME

    # check address filing
    delivery_address = business.delivery_address.one_or_none().json
    for key in delivery_address.keys():
        if key != 'addressType':
            assert delivery_address[key] == new_delivery_address[key]

    mailing_address = business.mailing_address.one_or_none().json
    for key in mailing_address.keys():
        if key != 'addressType':
            assert mailing_address[key] == new_mailing_address[key]

    # check director filing
    directors = Director.get_active_directors(business.id, end_date)
    assert len(directors) == 3
    for director in directors:
        # check that director in setup is not in the list (should've been ceased)
        assert director.id != director_id
        assert director.first_name not in ceased_directors
        assert director.first_name in active_directors
        active_directors.remove(director.first_name)
        # check returned only active directors
        assert director.cessation_date is None
        assert director.appointment_date
        assert director.delivery_address
        assert director.first_name == director.delivery_address.delivery_instructions

    # check added all active directors in filing
    assert active_directors == []
    # check cessation date set on ceased director
    assert DirectorResource._get_director(business, director_id)[0]['director']['cessationDate'] is not None


def test_process_filing_failed(app, session):
    """Assert that an AR filling status is set to error if payment transaction failed."""
    from entity_filer.worker import process_filing
    from entity_filer.worker import get_filing_by_payment_id
    from legal_api.models import Business, Filing

    # vars
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    identifier = 'CP1234567'

    # setup
    business = create_business(identifier)
    business_id = business.id
    create_filing(payment_id, AR_FILING, business.id)
    payment_token = {'paymentToken': {'id': payment_id, 'statusCode': 'TRANSACTION_FAILED'}}

    # TEST
    process_filing(payment_token, app)

    # Get modified data
    filing = get_filing_by_payment_id(payment_id)
    business = Business.find_by_internal_id(business_id)

    # check it out
    assert filing.business_id == business_id
    assert filing.status == Filing.Status.ERROR.value
    assert not business.last_agm_date
    assert not business.last_ar_date
