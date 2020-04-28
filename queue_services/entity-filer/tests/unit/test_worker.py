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
import random

import pytest
import pytz
from freezegun import freeze_time
from legal_api.models import Business, Filing, PartyRole, User
from legal_api.resources.business import DirectorResource
from registry_schemas.example_data import ANNUAL_REPORT, CORRECTION_AR, INCORPORATION

from entity_filer.filing_processors import create_party, create_role
from entity_filer.worker import process_filing
from tests.pytest_marks import colin_api_integration
from tests.unit import (
    AR_FILING,
    COA_FILING,
    COD_FILING,
    COD_FILING_TWO_ADDRESSES,
    COMBINED_FILING,
    INCORP_FILING,
    create_business,
    create_filing,
    create_user,
)


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


def test_process_filing_missing_app(app, session):
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
        process_filing(filing_msg, flask_app=None)


def test_process_ar_filing(app, session):
    """Assert that an AR filling can be applied to the model correctly."""
    # vars
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    identifier = 'CP1234567'

    # setup
    business = create_business(identifier)
    business_id = business.id
    now = datetime.date(2020, 9, 17)
    ar_date = datetime.date(2020, 8, 5)
    agm_date = datetime.date(2020, 7, 1)
    ar = copy.deepcopy(ANNUAL_REPORT)
    ar['filing']['business']['identifier'] = identifier
    ar['filing']['annualReport']['annualReportDate'] = ar_date.isoformat()
    ar['filing']['annualReport']['annualGeneralMeetingDate'] = agm_date.isoformat()

    # TEST
    with freeze_time(now):
        filing = create_filing(payment_id, ar, business.id)
        filing_id = filing.id
        filing_msg = {'filing': {'id': filing_id}}
        process_filing(filing_msg, app)

    # Get modified data
    filing = Filing.find_by_id(filing_id)
    business = Business.find_by_internal_id(business_id)

    # check it out
    assert filing.transaction_id
    assert filing.business_id == business_id
    assert filing.status == Filing.Status.COMPLETED.value
    assert datetime.datetime.date(business.last_agm_date) == agm_date
    assert datetime.datetime.date(business.last_ar_date) == agm_date


def test_process_ar_filing_no_agm(app, session):
    """Assert that a no agm AR filling can be applied to the model correctly."""
    # vars
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    identifier = 'CP1234567'

    # setup
    business = create_business(identifier)
    business_id = business.id
    now = datetime.date(2020, 9, 17)
    ar_date = datetime.date(2020, 8, 5)
    agm_date = None
    ar = copy.deepcopy(ANNUAL_REPORT)
    ar['filing']['business']['identifier'] = identifier
    ar['filing']['annualReport']['annualReportDate'] = ar_date.isoformat()
    ar['filing']['annualReport']['annualGeneralMeetingDate'] = None

    # TEST
    with freeze_time(now):
        filing = create_filing(payment_id, ar, business.id)
        filing_id = filing.id
        filing_msg = {'filing': {'id': filing_id}}
        process_filing(filing_msg, app)

    # Get modified data
    filing = Filing.find_by_id(filing_id)
    business = Business.find_by_internal_id(business_id)

    # check it out
    assert filing.transaction_id
    assert filing.business_id == business_id
    assert filing.status == Filing.Status.COMPLETED.value
    assert business.last_agm_date == agm_date
    assert datetime.datetime.date(business.last_ar_date) == ar_date


def test_process_coa_filing(app, session):
    """Assert that a COD filling can be applied to the model correctly."""
    # vars
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    identifier = 'CP1234567'
    new_delivery_address = COA_FILING['filing']['changeOfAddress']['offices']['registeredOffice']['deliveryAddress']
    new_mailing_address = COA_FILING['filing']['changeOfAddress']['offices']['registeredOffice']['mailingAddress']

    # setup
    business = create_business(identifier)
    business_id = business.id
    filing_id = (create_filing(payment_id, COA_FILING, business.id)).id
    filing_msg = {'filing': {'id': filing_id}}

    # TEST
    process_filing(filing_msg, app)

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


def test_process_cod_filing(app, session):
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
        'roleType': 'Director',
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
        'roleType': 'Director',
        'appointmentDate': directors[3].get('appointmentDate'),
        'cessationDate': directors[3].get('cessationDate')
    }
    director3 = create_role(party=director_party3, role_info=role3)
    # prep director for address change
    director_party4_dict = directors[3]
    director_party4_dict['deliveryAddress']['streetAddress'] = 'should get changed'
    director_party4 = create_party(business.id, director_party4_dict)
    role4 = {
        'roleType': 'Director',
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
    process_filing(filing_msg, app)

    # Get modified data
    filing = Filing.find_by_id(filing_id)
    business = Business.find_by_internal_id(business_id)

    # check it out
    assert filing.transaction_id
    assert filing.business_id == business_id
    assert filing.status == Filing.Status.COMPLETED.value

    directors = PartyRole.get_active_directors(business.id, end_date)
    check_directors(business, directors, director_ceased_id, ceased_directors, active_directors)


def test_process_cod_mailing_address(app, session):
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
    process_filing(filing_msg, app)

    filing = Filing.find_by_id(filing_id)
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
    process_filing(filing_msg, app)

    filing = Filing.find_by_id(filing_id)
    business = Business.find_by_internal_id(business_id)

    directors = PartyRole.get_active_directors(business.id, end_date)
    # Get modified data
    filing = Filing.find_by_id(filing_id)
    business = Business.find_by_internal_id(business_id)

    # check it out
    assert len(list(filter(lambda x: x.party.mailing_address is not None, directors))) == 2
    assert filing.transaction_id
    assert filing.business_id == business_id
    assert filing.status == Filing.Status.COMPLETED.value


def test_process_combined_filing(app, session):
    """Assert that an AR filling can be applied to the model correctly."""
    # vars
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    identifier = 'CP1234567'
    business = create_business(identifier)
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
        'roleType': 'Director',
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
        'roleType': 'Director',
        'appointmentDate': directors[3].get('appointmentDate'),
        'cessationDate': directors[3].get('cessationDate')
    }
    director3 = create_role(party=director_party3, role_info=role3)
    # prep director for address change
    director_party4_dict = directors[3]
    director_party4_dict['deliveryAddress']['streetAddress'] = 'should get changed'
    director_party4 = create_party(business.id, director_party4_dict)
    role4 = {
        'roleType': 'Director',
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
    process_filing(filing_msg, app)

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


def test_process_filing_completed(app, session):
    """Assert that an AR filling status is set to completed once processed."""
    # vars
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    identifier = 'CP1234567'

    # setup
    business = create_business(identifier)
    business_id = business.id
    filing_id = (create_filing(payment_id, AR_FILING, business.id)).id
    filing_msg = {'filing': {'id': filing_id}}

    # TEST
    process_filing(filing_msg, app)

    # Get modified data
    filing = Filing.find_by_id(filing_id)
    business = Business.find_by_internal_id(business_id)

    # check it out
    assert filing.business_id == business_id
    assert filing.status == Filing.Status.COMPLETED.value
    assert filing.transaction_id
    assert business.last_agm_date
    assert business.last_ar_date


@colin_api_integration
def test_incorporation_filing(app, session):
    """Assert we can retrieve a new corp number from COLIN and incorporate a business."""
    # vars
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing = copy.deepcopy(INCORP_FILING)
    identifier = filing['filing']['incorporationApplication']['nameRequest']['nrNumber']
    business = create_business(identifier)
    filing_id = (create_filing(payment_id, filing, business.id)).id
    filing_msg = {'filing': {'id': filing_id}}

    assert business.identifier == 'NR 1234567'

    process_filing(filing_msg, app)
    filing = Filing.find_by_id(filing_id)
    business = Business.find_by_internal_id(filing.business_id)
    assert business.identifier != 'NR 1234567'
    assert len(business.share_classes.all()) == 2
    assert len(business.offices.all()) == 3  # One office is created in create_business method.


@colin_api_integration
def test_process_incorporation_parties(app, session):
    """Assert we successfully add parties in incorporation filing."""
    # vars
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing = copy.deepcopy(INCORP_FILING)
    schema_incorp = copy.deepcopy(INCORPORATION)
    filing['filing']['incorporationApplication']['parties'] = schema_incorp['parties']

    identifier = filing['filing']['incorporationApplication']['nameRequest']['nrNumber']
    business = create_business(identifier)
    filing_id = (create_filing(payment_id, filing, business.id)).id
    filing_msg = {'filing': {'id': filing_id}}

    process_filing(filing_msg, app)
    filing = Filing.find_by_id(filing_id)
    business = Business.find_by_internal_id(filing.business_id)
    assert len(PartyRole.get_parties_by_role(business.id, 'director')) == 1
    assert len(PartyRole.get_parties_by_role(business.id, 'incorporator')) == 1
    assert len(PartyRole.get_parties_by_role(business.id, 'completing_party')) == 1
    director = (PartyRole.get_parties_by_role(business.id, 'director'))[0]
    incorporator = (PartyRole.get_parties_by_role(business.id, 'incorporator'))[0]
    completing_party = (PartyRole.get_parties_by_role(business.id, 'completing_party'))[0]
    assert director.appointment_date
    assert incorporator.appointment_date
    assert completing_party.appointment_date


def test_correction_filing(app, session):
    """Assert we can process a correction filing."""
    # vars
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    identifier = 'CP1111111'
    correction_filing_comment = 'We need to fix directors'

    # get a fixed datetime to use in comparisons, in "local" (Pacific) timezone
    local_timezone = pytz.timezone('US/Pacific')
    correction_filing_date = \
        datetime.datetime(2019, 9, 17, 0, 0).replace(tzinfo=datetime.timezone.utc).astimezone(tz=local_timezone)

    # setup - create business, staff user, and original filing to be corrected
    business_id = create_business(identifier).id
    staff_user_id = create_user(username='staff_user').id
    original_filing_id = create_filing(payment_id, copy.deepcopy(ANNUAL_REPORT), business_id).id

    # setup - create correction filing
    filing = copy.deepcopy(CORRECTION_AR)
    filing['filing']['header']['identifier'] = identifier
    filing['filing']['correction']['comment'] = correction_filing_comment
    filing['filing']['correction']['correctedFilingId'] = original_filing_id
    correction_filing = create_filing(payment_id, filing, business_id, filing_date=correction_filing_date)
    correction_filing.submitter_id = staff_user_id
    correction_filing.save()

    correction_filing_id = correction_filing.id
    filing_msg = {'filing': {'id': correction_filing_id}}

    process_filing(filing_msg, app)

    # Get modified data
    original_filing = Filing.find_by_id(original_filing_id)
    correction_filing = Filing.find_by_id(correction_filing_id)
    staff_user = User.find_by_username('staff_user')

    # check that the correction filing is linked to the original filing
    assert original_filing.parent_filing
    assert original_filing.parent_filing == correction_filing

    # check that the correction comment has been added to the correction filing
    assert 0 < len(correction_filing.comments.all())
    assert correction_filing_comment == correction_filing.comments.all()[-1].comment
    assert staff_user.id == correction_filing.comments.all()[-1].staff.id

    # check that the correction filing is PENDING_CORRECTION
    assert correction_filing.status == 'PENDING_CORRECTION'

    # check that the original filing is marked as corrected
    # assert True is original_filing.is_corrected

    # check that the original filing has the new comment
    assert 0 < len(original_filing.comments.all())
    assert f'This filing was corrected on {correction_filing_date.date().isoformat()}.' == \
           original_filing.comments.all()[-1].comment
    assert staff_user.id == original_filing.comments.all()[-1].staff.id
