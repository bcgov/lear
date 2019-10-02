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

from tests.unit import AR_FILING, COA_FILING, COD_FILING, COMBINED_FILING, create_business, create_director, create_filing  # noqa I001, E501;


def compare_addresses(business_address: dict, filing_address: dict):
    """Compare two address dicts."""
    for key in business_address.keys():
        if key == 'addressCountry':
            assert business_address[key] == 'CA'
        elif key != 'addressType':
            assert business_address[key] == filing_address[key]


def active_ceased_lists(filing):
    """Create active/ceased director lists based on a filing json."""
    ceased_directors = []
    active_directors = []
    for filed_director in filing['filing']['changeOfDirectors']['directors']:
        if filed_director.get('cessationDate'):
            ceased_directors.append(filed_director['officer']['firstName'].upper())
        else:
            active_directors.append(filed_director['officer']['firstName'].upper())
    return ceased_directors, active_directors


def check_directors(business, directors, director_ceased_id, ceased_directors, active_directors):
    """Assert basic checks on directors."""
    from legal_api.resources.business import DirectorResource
    assert len(directors) == len(active_directors)
    for director in directors:
        # check that director in setup is not in the list (should've been ceased)
        assert director.id != director_ceased_id
        assert director.first_name not in ceased_directors
        assert director.first_name in active_directors
        active_directors.remove(director.first_name)
        # check returned only active directors
        assert director.cessation_date is None
        assert director.appointment_date
        assert director.delivery_address
        assert director.first_name == director.delivery_address.delivery_instructions.upper()

    # check added all active directors in filing
    assert active_directors == []
    # check cessation date set on ceased director
    assert DirectorResource._get_director(business, director_ceased_id)[0]['director']['cessationDate'] is not None


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
    ar_date = datetime.date.fromisoformat(COMBINED_FILING['filing']['annualReport'].get('annualReportDate'))

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
    assert datetime.datetime.date(business.last_ar_date) == ar_date


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
    compare_addresses(delivery_address, new_delivery_address)
    mailing_address = business.mailing_address.one_or_none().json
    compare_addresses(mailing_address, new_mailing_address)


def test_process_cod_filing(app, session):
    """Assert that an AR filling can be applied to the model correctly."""
    import copy
    from legal_api.models import Business, Director, Filing

    from entity_filer.worker import process_filing
    from entity_filer.worker import get_filing_by_payment_id

    # vars
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    identifier = 'CP1234567'
    end_date = datetime.datetime.utcnow().date()
    # prep director for no change
    filing_data = copy.deepcopy(COD_FILING)
    director1 = create_director(filing_data['filing']['changeOfDirectors']['directors'][0])
    # prep director for name change
    director2 = filing_data['filing']['changeOfDirectors']['directors'][1]
    director2['officer']['firstName'] = director2['officer']['prevFirstName']
    director2['officer']['middleInitial'] = director2['officer']['prevMiddleInitial']
    director2['officer']['lastName'] = director2['officer']['prevLastName']
    director2 = create_director(director2)
    # prep director for cease
    director3 = create_director(filing_data['filing']['changeOfDirectors']['directors'][2])
    director_ceased_id = director3.id
    # prep director for address change
    director4 = filing_data['filing']['changeOfDirectors']['directors'][3]
    director4['deliveryAddress']['streetAddress'] = 'should get changed'
    director4 = create_director(director4)

    # list of active/ceased directors in test filing
    ceased_directors, active_directors = active_ceased_lists(COD_FILING)

    # setup
    business = create_business(identifier)
    business.directors.append(director1)
    business.directors.append(director2)
    business.directors.append(director3)
    business.directors.append(director4)
    business.save()
    # check that adding the director during setup was successful
    directors = Director.get_active_directors(business.id, end_date)
    assert len(directors) == 4
    # create filing
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
    check_directors(business, directors, director_ceased_id, ceased_directors, active_directors)


def test_process_combined_filing(app, session):
    """Assert that an AR filling can be applied to the model correctly."""
    import copy
    from legal_api.models import Business, Director, Filing

    from entity_filer.worker import process_filing
    from entity_filer.worker import get_filing_by_payment_id

    # vars
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    identifier = 'CP1234567'
    agm_date = datetime.date.fromisoformat(COMBINED_FILING['filing']['annualReport'].get('annualGeneralMeetingDate'))
    ar_date = datetime.date.fromisoformat(COMBINED_FILING['filing']['annualReport'].get('annualReportDate'))
    new_delivery_address = COMBINED_FILING['filing']['changeOfAddress']['deliveryAddress']
    new_mailing_address = COMBINED_FILING['filing']['changeOfAddress']['mailingAddress']
    end_date = datetime.datetime.utcnow().date()
    # prep director for no change
    filing_data = copy.deepcopy(COMBINED_FILING)
    director1 = create_director(filing_data['filing']['changeOfDirectors']['directors'][0])
    # prep director for name change
    director2 = filing_data['filing']['changeOfDirectors']['directors'][1]
    director2['officer']['firstName'] = director2['officer']['prevFirstName']
    director2['officer']['middleInitial'] = director2['officer']['prevMiddleInitial']
    director2['officer']['lastName'] = director2['officer']['prevLastName']
    director2 = create_director(director2)
    # prep director for cease
    director3 = create_director(filing_data['filing']['changeOfDirectors']['directors'][2])
    director_ceased_id = director3.id
    # prep director for address change
    director4 = filing_data['filing']['changeOfDirectors']['directors'][3]
    director4['deliveryAddress']['streetAddress'] = 'should get changed'
    director4 = create_director(director4)

    # list of active/ceased directors in test filing
    ceased_directors, active_directors = active_ceased_lists(COMBINED_FILING)

    # setup
    business = create_business(identifier)
    business.directors.append(director1)
    business.directors.append(director2)
    business.directors.append(director3)
    business.directors.append(director4)
    business.save()
    # check that adding the director during setup was successful
    directors = Director.get_active_directors(business.id, end_date)
    assert len(directors) == 4
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
    assert datetime.datetime.date(business.last_ar_date) == ar_date

    # check address filing
    delivery_address = business.delivery_address.one_or_none().json
    compare_addresses(delivery_address, new_delivery_address)
    mailing_address = business.mailing_address.one_or_none().json
    compare_addresses(mailing_address, new_mailing_address)

    # check director filing
    directors = Director.get_active_directors(business.id, end_date)
    check_directors(business, directors, director_ceased_id, ceased_directors, active_directors)


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
