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
import copy
import datetime
from datetime import timezone
from http import HTTPStatus
import random
from unittest.mock import patch

import pycountry
import pytest
import pytz
from freezegun import freeze_time
from legal_api.models import Business, Filing, PartyRole, User
from legal_api.resources.v1.business import DirectorResource
from registry_schemas.example_data import (
    ANNUAL_REPORT,
    CHANGE_OF_ADDRESS,
    CONTINUATION_IN_FILING_TEMPLATE,
    CORRECTION_AR,
    FILING_HEADER,
    INCORPORATION_FILING_TEMPLATE,
)

from entity_queue_common.service_utils import QueueException
from entity_filer.filing_processors.filing_components import business_info, business_profile, create_party, create_role
from entity_filer.worker import process_filing
from tests.unit import (
    COD_FILING,
    COD_FILING_TWO_ADDRESSES,
    COMBINED_FILING,
    create_business,
    create_filing,
    create_user,
)


def compare_addresses(business_address: dict, filing_address: dict):
    """Compare two address dicts."""
    for key, value in business_address.items():
        if value is None and filing_address.get(key):
            assert False
        elif key == 'addressCountry':
            pycountry.countries.search_fuzzy(value)[0].alpha_2 == \
                pycountry.countries.search_fuzzy(filing_address.get('addressCountry'))[0].alpha_2
            assert business_address[key] == 'CA'
        elif key not in ('addressType', 'id'):
            assert business_address.get(key) == (filing_address.get(key) or '')


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
    assert len(directors) == len(active_directors)
    for director in directors:
        # check that director in setup is not in the list (should've been ceased)
        assert director.id != director_ceased_id
        assert director.party.first_name not in ceased_directors
        assert director.party.first_name in active_directors
        active_directors.remove(director.party.first_name)
        # check returned only active directors
        assert director.cessation_date is None
        assert director.appointment_date
        assert director.party.delivery_address
        assert director.party.first_name == director.party.delivery_address.delivery_instructions.upper()

    # check added all active directors in filing
    assert active_directors == []
    # check cessation date set on ceased director
    assert DirectorResource._get_director(business, director_ceased_id)[0]['director']['cessationDate'] is not None


async def test_process_filing_missing_app(app, session):
    """Assert that a filling will fail with no flask app supplied."""
    # vars
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    identifier = 'CP1234567'

    # setup
    business = create_business(identifier)
    create_filing(payment_id, None, business.id)
    filing_msg = {'filing': {'id': 'test_id'}}

    # TEST
    with pytest.raises(Exception):
        await process_filing(filing_msg, flask_app=None)


async def test_process_coa_filing(app, session):
    """Assert that a COD filling can be applied to the model correctly."""
    # vars
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    identifier = 'CP1234567'
    coa_filing = copy.deepcopy(FILING_HEADER)
    coa_filing['filing']['changeOfAddress'] = copy.deepcopy(CHANGE_OF_ADDRESS)
    new_delivery_address = coa_filing['filing']['changeOfAddress']['offices']['registeredOffice']['deliveryAddress']
    new_mailing_address = coa_filing['filing']['changeOfAddress']['offices']['registeredOffice']['mailingAddress']

    # setup
    business = create_business(identifier)
    business_id = business.id
    filing_id = (create_filing(payment_id, coa_filing, business.id)).id
    filing_msg = {'filing': {'id': filing_id}}

    # TEST
    await process_filing(filing_msg, app)

    # Get modified data
    filing = Filing.find_by_id(filing_id)
    business = Business.find_by_internal_id(business_id)

    # check it out
    assert filing.transaction_id
    assert filing.business_id == business_id
    assert filing.status == Filing.Status.COMPLETED.value

    register_office = business.offices.filter_by(office_type='registeredOffice').one_or_none()

    delivery_address = register_office.addresses.filter_by(address_type='delivery').one_or_none().json
    compare_addresses(delivery_address, new_delivery_address)
    mailing_address = register_office.addresses.filter_by(address_type='mailing').one_or_none().json
    compare_addresses(mailing_address, new_mailing_address)


async def test_process_cod_filing(app, session):
    """Assert that an AR filling can be applied to the model correctly."""
    # vars
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    identifier = 'CP1234567'
    business = create_business(identifier)
    end_date = datetime.datetime.utcnow().date()
    # prep director for no change
    filing_data = copy.deepcopy(COD_FILING)
    directors = filing_data['filing']['changeOfDirectors']['directors']
    director_party1 = create_party(business.id, directors[0])
    role1 = {
        'roleType': 'director',
        'appointmentDate': directors[0].get('appointmentDate'),
        'cessationDate': directors[0].get('cessationDate')
    }
    director1 = create_role(party=director_party1, role_info=role1)
    # prep director for name change
    director_party2_dict = directors[1]
    director_party2_dict['officer']['firstName'] = director_party2_dict['officer']['prevFirstName']
    director_party2_dict['officer']['middleInitial'] = director_party2_dict['officer']['prevMiddleInitial']
    director_party2_dict['officer']['lastName'] = director_party2_dict['officer']['prevLastName']
    director_party2 = create_party(business.id, director_party2_dict)
    role2 = {
        'roleType': 'director',
        'appointmentDate': director_party2_dict.get('appointmentDate'),
        'cessationDate': director_party2_dict.get('cessationDate')
    }
    director2 = create_role(party=director_party2, role_info=role2)
    # prep director for cease
    director_party3 = create_party(business.id, directors[2])
    role3 = {
        'roleType': 'director',
        'appointmentDate': directors[3].get('appointmentDate'),
        'cessationDate': directors[3].get('cessationDate')
    }
    director3 = create_role(party=director_party3, role_info=role3)
    # prep director for address change
    director_party4_dict = directors[3]
    director_party4_dict['deliveryAddress']['streetAddress'] = 'should get changed'
    director_party4 = create_party(business.id, director_party4_dict)
    role4 = {
        'roleType': 'director',
        'appointmentDate': director_party4_dict.get('appointmentDate'),
        'cessationDate': director_party4_dict.get('cessationDate')
    }
    director4 = create_role(party=director_party4, role_info=role4)

    # list of active/ceased directors in test filing
    ceased_directors, active_directors = active_ceased_lists(COD_FILING)

    # setup
    business.party_roles.append(director1)
    business.party_roles.append(director2)
    business.party_roles.append(director3)
    business.party_roles.append(director4)
    business.save()
    director_ceased_id = director3.id
    # check that adding the director during setup was successful
    directors = PartyRole.get_parties_by_role(business.id, PartyRole.RoleTypes.DIRECTOR.value)
    assert len(directors) == 4
    # create filing
    business_id = business.id
    filing_id = (create_filing(payment_id, COD_FILING, business.id)).id
    filing_msg = {'filing': {'id': filing_id}}

    # TEST
    await process_filing(filing_msg, app)

    # Get modified data
    filing = Filing.find_by_id(filing_id)
    business = Business.find_by_internal_id(business_id)

    # check it out
    assert filing.transaction_id
    assert filing.business_id == business_id
    assert filing.status == Filing.Status.COMPLETED.value

    directors = PartyRole.get_active_directors(business.id, end_date)
    check_directors(business, directors, director_ceased_id, ceased_directors, active_directors)


async def test_process_cod_mailing_address(app, session):
    """Assert that a COD address change filling can be applied to the model correctly."""
    # vars
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    identifier = 'CP1234567'
    end_date = datetime.datetime.utcnow().date()
    # prep director for no change
    filing_data = copy.deepcopy(COD_FILING_TWO_ADDRESSES)

    # setup
    business = create_business(identifier)
    business.save()

    directors = PartyRole.get_active_directors(business.id, end_date)
    assert len(directors) == 0

    # create filing
    business_id = business.id
    filing_data['filing']['changeOfDirectors']['directors'][0]['actions'] = ['appointed']
    filing_data['filing']['changeOfDirectors']['directors'][1]['actions'] = ['appointed']
    filing_id = (create_filing(payment_id, filing_data, business_id)).id
    filing_msg = {'filing': {'id': filing_id}}
    # TEST
    await process_filing(filing_msg, app)

    business = Business.find_by_internal_id(business_id)

    directors = PartyRole.get_active_directors(business.id, end_date)

    has_mailing = list(filter(lambda x: x.party.mailing_address is not None, directors))
    no_mailing = list(filter(lambda x: x.party.mailing_address is None, directors))

    assert len(has_mailing) == 1
    assert has_mailing[0].party.mailing_address.street == 'test mailing 1'
    assert no_mailing[0].party.mailing_address is None

    # Add/update mailing address to a director

    del filing_data['filing']['changeOfDirectors']['directors'][0]
    filing_data['filing']['changeOfDirectors']['directors'][0]['actions'] = ['addressChanged']

    mailing_address = {
        'streetAddress': 'test mailing 2',
        'streetAddressAdditional': 'test line 1',
        'addressCity': 'testcity',
        'addressCountry': 'Canada',
        'addressRegion': 'BC',
        'postalCode': 'T3S T3R',
        'deliveryInstructions': 'director1'
    }

    filing_data['filing']['changeOfDirectors']['directors'][0]['mailingAddress'] = mailing_address

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing_id = (create_filing(payment_id, filing_data, business_id)).id
    filing_msg = {'filing': {'id': filing_id}}
    await process_filing(filing_msg, app)

    business = Business.find_by_internal_id(business_id)

    directors = PartyRole.get_active_directors(business.id, end_date)
    # Get modified data
    filing = Filing.find_by_id(filing_id)

    # check it out
    assert len(list(filter(lambda x: x.party.mailing_address is not None, directors))) == 2
    assert filing.business_id == business_id
    assert filing.status == Filing.Status.COMPLETED.value


async def test_process_combined_filing(app, session, mocker):
    """Assert that an AR filling can be applied to the model correctly."""
    # mock out the email sender and event publishing
    mocker.patch('entity_filer.worker.publish_email_message', return_value=None)
    mocker.patch('entity_filer.worker.publish_event', return_value=None)

    # vars
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    identifier = 'CP1234567'
    business = create_business(identifier, legal_type='CP')
    agm_date = datetime.date.fromisoformat(COMBINED_FILING['filing']['annualReport'].get('annualGeneralMeetingDate'))
    ar_date = datetime.date.fromisoformat(COMBINED_FILING['filing']['annualReport'].get('annualReportDate'))
    new_delivery_address = COMBINED_FILING['filing']['changeOfAddress']['offices']['registeredOffice']['deliveryAddress']  # noqa: E501; line too long by 1 char
    new_mailing_address = COMBINED_FILING['filing']['changeOfAddress']['offices']['registeredOffice']['mailingAddress']
    end_date = datetime.datetime.utcnow().date()
    # prep director for no change
    filing_data = copy.deepcopy(COMBINED_FILING)
    directors = filing_data['filing']['changeOfDirectors']['directors']
    director_party1 = create_party(business.id, directors[0])
    role1 = {
        'roleType': 'director',
        'appointmentDate': directors[0].get('appointmentDate'),
        'cessationDate': directors[0].get('cessationDate')
    }
    director1 = create_role(party=director_party1, role_info=role1)
    # prep director for name change
    director_party2_dict = directors[1]
    director_party2_dict['officer']['firstName'] = director_party2_dict['officer']['prevFirstName']
    director_party2_dict['officer']['middleInitial'] = director_party2_dict['officer']['prevMiddleInitial']
    director_party2_dict['officer']['lastName'] = director_party2_dict['officer']['prevLastName']
    director_party2 = create_party(business.id, director_party2_dict)
    role2 = {
        'roleType': 'Director',
        'appointmentDate': director_party2_dict.get('appointmentDate'),
        'cessationDate': director_party2_dict.get('cessationDate')
    }
    director2 = create_role(party=director_party2, role_info=role2)
    # prep director for cease
    director_party3 = create_party(business.id, directors[2])
    role3 = {
        'roleType': 'director',
        'appointmentDate': directors[3].get('appointmentDate'),
        'cessationDate': directors[3].get('cessationDate')
    }
    director3 = create_role(party=director_party3, role_info=role3)
    # prep director for address change
    director_party4_dict = directors[3]
    director_party4_dict['deliveryAddress']['streetAddress'] = 'should get changed'
    director_party4 = create_party(business.id, director_party4_dict)
    role4 = {
        'roleType': 'director',
        'appointmentDate': director_party4_dict.get('appointmentDate'),
        'cessationDate': director_party4_dict.get('cessationDate')
    }
    director4 = create_role(party=director_party4, role_info=role4)

    # list of active/ceased directors in test filing
    ceased_directors, active_directors = active_ceased_lists(COMBINED_FILING)

    # setup
    business.party_roles.append(director1)
    business.party_roles.append(director2)
    business.party_roles.append(director3)
    business.party_roles.append(director4)
    business.save()
    director_ceased_id = director3.id
    # check that adding the directors during setup was successful
    directors = PartyRole.get_parties_by_role(business.id, PartyRole.RoleTypes.DIRECTOR.value)
    assert len(directors) == 4
    business_id = business.id
    filing_id = (create_filing(payment_id, COMBINED_FILING, business.id)).id
    filing_msg = {'filing': {'id': filing_id}}

    # TEST
    await process_filing(filing_msg, app)

    # Get modified data
    filing = Filing.find_by_id(filing_id)
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
    directors = PartyRole.get_active_directors(business.id, end_date)
    check_directors(business, directors, director_ceased_id, ceased_directors, active_directors)


async def test_process_filing_completed(app, session, mocker):
    """Assert that an AR filling status is set to completed once processed."""
    # vars
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    identifier = 'CP1234567'

    # mock out the email sender and event publishing
    mocker.patch('entity_filer.worker.publish_email_message', return_value=None)
    mocker.patch('entity_filer.worker.publish_event', return_value=None)

    # setup
    business = create_business(identifier, legal_type='CP')
    business_id = business.id
    filing_id = (create_filing(payment_id, ANNUAL_REPORT, business.id)).id
    filing_msg = {'filing': {'id': filing_id}}

    # TEST
    await process_filing(filing_msg, app)

    # Get modified data
    filing = Filing.find_by_id(filing_id)
    business = Business.find_by_internal_id(business_id)

    # check it out
    assert filing.business_id == business_id
    assert filing.status == Filing.Status.COMPLETED.value
    assert filing.transaction_id
    assert business.last_agm_date
    assert business.last_ar_date


async def test_publish_event():
    """Assert that publish_event is called with the correct struct."""
    import uuid
    from unittest.mock import AsyncMock
    from entity_filer.worker import APP_CONFIG, get_filing_types, publish_event, qsm
    from legal_api.utils.datetime import datetime

    mock_publish = AsyncMock()
    qsm.service = mock_publish
    with freeze_time(datetime.utcnow()), \
            patch.object(uuid, 'uuid4', return_value=1):

        business = Business(identifier='BC1234567')
        filing = Filing(id=1,
                        effective_date=datetime.utcnow(),
                        _filing_type='incorporationApplication',
                        _filing_json=INCORPORATION_FILING_TEMPLATE)

        await publish_event(business, filing)

        payload = {
            'specversion': '1.x-wip',
            'type': 'bc.registry.business.' + filing.filing_type,
            'source': ''.join(
                [APP_CONFIG.LEGAL_API_URL,
                 '/business/',
                 business.identifier,
                 '/filing/',
                 str(filing.id)]),
            'id': str(uuid.uuid4()),
            'time': datetime.utcnow().isoformat(),
            'datacontenttype': 'application/json',
            'identifier': business.identifier,
            'data': {
                'filing': {
                    'header': {'filingId': filing.id,
                               'effectiveDate': filing.effective_date.isoformat()
                               },
                    'business': {'identifier': business.identifier},
                    'legalFilings': get_filing_types(filing.filing_json)
                }
            }
        }

    mock_publish.publish.assert_called_with('entity.events', payload)


@pytest.mark.parametrize('test_name,withdrawal_pending,filing_status', [
    ('Process the Filing', False, 'PAID'),
    ('Dont process the Filing', False, 'WITHDRAWN'),
    ('Dont process the Filing', True, 'PAID'),
    ('Dont process the Filing', True, 'WITHDRAWN'),
])
async def test_skip_process_filing(app, session, mocker, test_name, withdrawal_pending, filing_status):
    """Assert that an filling can be processed."""
    # vars
    filing_type = 'continuationIn'
    nr_identifier = 'NR 1234567'
    next_corp_num = 'C0001095'

    filing = copy.deepcopy(CONTINUATION_IN_FILING_TEMPLATE)
    filing['filing'][filing_type]['nameRequest']['nrNumber'] = nr_identifier
    filing['filing'][filing_type]['nameTranslations'] = [{'name': 'ABCD Ltd.'}]
    filing_rec = create_filing('123', filing)
    effective_date = datetime.datetime.now(timezone.utc)
    filing_rec.effective_date = effective_date
    filing_rec._status = filing_status
    filing_rec.withdrawal_pending = withdrawal_pending
    filing_rec.save()

    # test
    filing_msg = {'filing': {'id': filing_rec.id}}
    
    with patch.object(business_info, 'get_next_corp_num', return_value=next_corp_num):
        with patch.object(business_profile, 'update_business_profile', return_value=HTTPStatus.OK):
            if withdrawal_pending and filing_status != 'WITHDRAWN':
                with pytest.raises(QueueException):
                    await process_filing(filing_msg, app)
            else:
                await process_filing(filing_msg, app)

    business = Business.find_by_identifier(next_corp_num)
    if not withdrawal_pending and filing_status == 'PAID':
        assert business.state == Business.State.ACTIVE
