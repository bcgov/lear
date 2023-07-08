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
"""The Unit Tests and the helper routines."""
import copy
import json
from datetime import datetime
from random import randrange
from unittest.mock import Mock

from legal_api.models import Business, Filing, RegistrationBootstrap, User
from registry_schemas.example_data import (
    ALTERATION,
    ALTERATION_FILING_TEMPLATE,
    ANNUAL_REPORT,
    CHANGE_OF_DIRECTORS,
    CHANGE_OF_REGISTRATION,
    CONSENT_CONTINUATION_OUT,
    CONTINUATION_OUT,
    CORP_CHANGE_OF_ADDRESS,
    CORRECTION_CP_SPECIAL_RESOLUTION,
    CORRECTION_INCORPORATION,
    CORRECTION_REGISTRATION,
    CP_SPECIAL_RESOLUTION_TEMPLATE,
    DISSOLUTION,
    FILING_HEADER,
    FILING_TEMPLATE,
    INCORPORATION_FILING_TEMPLATE,
    REGISTRATION,
    RESTORATION,
)
from sqlalchemy_continuum import versioning_manager

from tests import EPOCH_DATETIME


FILING_TYPE_MAPPER = {
    # annual report structure is different than other 2
    'annualReport': ANNUAL_REPORT['filing']['annualReport'],
    'changeOfAddress': CORP_CHANGE_OF_ADDRESS,
    'changeOfDirectors': CHANGE_OF_DIRECTORS,
    'alteration': ALTERATION
}

LEGAL_NAME = 'test business'


def create_user(user_name: str):
    """Return a new user model."""
    user = User()
    user.username = user_name
    user.save()
    return user


def create_business(identifier, legal_type=None, legal_name=None):
    """Return a test business."""
    business = Business()
    business.identifier = identifier
    business.legal_type = legal_type
    business.legal_name = legal_name
    business.save()
    return business


def create_filing(token=None, filing_json=None, business_id=None, filing_date=EPOCH_DATETIME, bootstrap_id: str = None):
    """Return a test filing."""
    filing = Filing()
    if token:
        filing.payment_token = str(token)
    filing.filing_date = filing_date

    if filing_json:
        filing.filing_json = filing_json
    if business_id:
        filing.business_id = business_id
    if bootstrap_id:
        filing.temp_reg = bootstrap_id

    filing.save()
    return filing


def prep_incorp_filing(session, identifier, payment_id, option, legal_type=None):
    """Return a new incorp filing prepped for email notification."""
    business = create_business(identifier, legal_type=legal_type, legal_name=LEGAL_NAME)
    filing_template = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    filing_template['filing']['business'] = {'identifier': business.identifier}
    if business.legal_type:
        filing_template['filing']['business']['legalType'] = business.legal_type
        filing_template['filing']['incorporationApplication']['nameRequest']['legalType'] = business.legal_type
    for party in filing_template['filing']['incorporationApplication']['parties']:
        for role in party['roles']:
            if role['roleType'] == 'Completing Party':
                party['officer']['email'] = 'comp_party@email.com'
    filing_template['filing']['incorporationApplication']['contactPoint']['email'] = 'test@test.com'

    temp_identifier = 'Tb31yQIuBw'
    temp_reg = RegistrationBootstrap()
    temp_reg._identifier = temp_identifier
    temp_reg.save()
    filing = create_filing(token=payment_id, filing_json=filing_template,
                           business_id=business.id, bootstrap_id=temp_identifier)
    filing.payment_completion_date = filing.filing_date
    filing.save()
    if option in ['COMPLETED', 'bn']:
        uow = versioning_manager.unit_of_work(session)
        transaction = uow.create_transaction(session)
        filing.transaction_id = transaction.id
        filing.save()
    return filing


def prep_registration_filing(session, identifier, payment_id, option, legal_type, legal_name):
    """Return a new registration filing prepped for email notification."""
    now = datetime.now().strftime('%Y-%m-%d')
    REGISTRATION['business']['naics'] = {
        'naicsCode': '112320',
        'naicsDescription': 'Broiler and other meat-type chicken production'
    }

    gp_registration = copy.deepcopy(FILING_HEADER)
    gp_registration['filing']['header']['name'] = 'registration'
    gp_registration['filing']['registration'] = copy.deepcopy(REGISTRATION)
    gp_registration['filing']['registration']['startDate'] = now
    gp_registration['filing']['registration']['nameRequest']['legalName'] = legal_name
    gp_registration['filing']['registration']['parties'][1]['officer']['email'] = 'party@email.com'

    sp_registration = copy.deepcopy(FILING_HEADER)
    sp_registration['filing']['header']['name'] = 'registration'
    sp_registration['filing']['registration'] = copy.deepcopy(REGISTRATION)
    sp_registration['filing']['registration']['startDate'] = now
    sp_registration['filing']['registration']['nameRequest']['legalType'] = 'SP'
    sp_registration['filing']['registration']['nameRequest']['legalName'] = legal_name
    sp_registration['filing']['registration']['businessType'] = 'SP'
    sp_registration['filing']['registration']['parties'][0]['roles'] = [
        {
            'roleType': 'Completing Party',
            'appointmentDate': '2022-01-01'

        },
        {
            'roleType': 'Proprietor',
            'appointmentDate': '2022-01-01'

        }
    ]
    del sp_registration['filing']['registration']['parties'][1]

    if legal_type == Business.LegalTypes.SOLE_PROP.value:
        filing_template = sp_registration
    elif legal_type == Business.LegalTypes.PARTNERSHIP.value:
        filing_template = gp_registration

    business_id = None
    if option == 'PAID':
        del filing_template['filing']['business']
    elif option == 'COMPLETED':
        business = create_business(identifier, legal_type)
        business.founding_date = datetime.fromisoformat(now)
        business.save()
        business_id = business.id
        filing_template['filing']['business'] = {
            'identifier': business.identifier,
            'legalType': business.legal_type,
            'foundingDate': business.founding_date.isoformat()
        }

    filing = create_filing(token=payment_id, filing_json=filing_template, business_id=business_id)
    filing.payment_completion_date = filing.filing_date
    filing.save()
    if option in ['COMPLETED']:
        uow = versioning_manager.unit_of_work(session)
        transaction = uow.create_transaction(session)
        filing.transaction_id = transaction.id
        filing.save()
    return filing


def prep_dissolution_filing(session, identifier, payment_id, option, legal_type, legal_name, submitter_role):
    """Return a new dissolution filing prepped for email notification."""
    business = create_business(identifier, legal_type, legal_name)
    filing_template = copy.deepcopy(FILING_HEADER)
    filing_template['filing']['header']['name'] = 'dissolution'
    if submitter_role:
        filing_template['filing']['header']['documentOptionalEmail'] = f'{submitter_role}@email.com'

    filing_template['filing']['dissolution'] = copy.deepcopy(DISSOLUTION)
    filing_template['filing']['business'] = {
        'identifier': business.identifier,
        'legalType': legal_type,
        'legalName': legal_name
    }

    for party in filing_template['filing']['dissolution']['parties']:
        for role in party['roles']:
            if role['roleType'] == 'Custodian':
                party['officer']['email'] = 'custodian@email.com'
            elif role['roleType'] == 'Completing Party':
                party['officer']['email'] = 'cp@email.com'

    filing = create_filing(
        token=payment_id,
        filing_json=filing_template,
        business_id=business.id)
    filing.payment_completion_date = filing.filing_date

    user = create_user('test_user')
    filing.submitter_id = user.id
    if submitter_role:
        filing.submitter_roles = submitter_role

    filing.save()
    return filing


def prep_consent_continuation_out_filing(session, identifier, payment_id, legal_type, legal_name, submitter_role):
    """Return a new consent continuation out filing prepped for email notification."""
    business = create_business(identifier, legal_type, legal_name)
    filing_template = copy.deepcopy(FILING_HEADER)
    filing_template['filing']['header']['name'] = 'consentContinuationOut'
    if submitter_role:
        filing_template['filing']['header']['documentOptionalEmail'] = f'{submitter_role}@email.com'

    filing_template['filing']['consentContinuationOut'] = copy.deepcopy(CONSENT_CONTINUATION_OUT)
    filing_template['filing']['business'] = {
        'identifier': business.identifier,
        'legalType': legal_type,
        'legalName': legal_name
    }

    filing = create_filing(
        token=payment_id,
        filing_json=filing_template,
        business_id=business.id)
    filing.payment_completion_date = filing.filing_date

    user = create_user('test_user')
    filing.submitter_id = user.id
    if submitter_role:
        filing.submitter_roles = submitter_role

    filing.save()
    return filing


def prep_continuation_out_filing(session, identifier, payment_id, legal_type, legal_name, submitter_role):
    """Return a new continuation out filing prepped for email notification."""
    business = create_business(identifier, legal_type, legal_name)
    filing_template = copy.deepcopy(FILING_HEADER)
    filing_template['filing']['header']['name'] = 'continuationOut'
    if submitter_role:
        filing_template['filing']['header']['documentOptionalEmail'] = f'{submitter_role}@email.com'

    filing_template['filing']['continuationOut'] = copy.deepcopy(CONTINUATION_OUT)
    filing_template['filing']['business'] = {
        'identifier': business.identifier,
        'legalType': legal_type,
        'legalName': legal_name
    }

    filing = create_filing(
        token=payment_id,
        filing_json=filing_template,
        business_id=business.id)
    filing.payment_completion_date = filing.filing_date

    user = create_user('test_user')
    filing.submitter_id = user.id
    if submitter_role:
        filing.submitter_roles = submitter_role

    filing.save()
    return filing


def prep_restoration_filing(identifier, payment_id, legal_type, legal_name, r_type='fullRestoration'):
    """Return a new restoration filing prepped for email notification.

    @param r_type:
    @param identifier:
    @param payment_id:
    @param legal_type:
    @param legal_name:
    @return:
    """
    business = create_business(identifier, legal_type, legal_name)
    filing_template = copy.deepcopy(FILING_HEADER)
    filing_template['filing']['header']['name'] = 'restoration'
    filing_template['filing']['restoration'] = copy.deepcopy(RESTORATION)
    filing_template['filing']['restoration']['type'] = r_type
    filing_template['filing']['business'] = {
        'identifier': business.identifier,
        'legalType': legal_type,
        'legalName': legal_name
    }

    filing = create_filing(
        token=payment_id,
        filing_json=filing_template,
        business_id=business.id)
    filing.payment_completion_date = filing.filing_date

    user = create_user('test_user')
    filing.submitter_id = user.id

    filing.save()
    return filing


def prep_change_of_registration_filing(session, identifier, payment_id, legal_type, legal_name, submitter_role):
    """Return a new change of registration filing prepped for email notification."""
    business = create_business(identifier, legal_type, legal_name)

    gp_change_of_registration = copy.deepcopy(FILING_HEADER)
    gp_change_of_registration['filing']['header']['name'] = 'changeOfRegistration'
    gp_change_of_registration['filing']['changeOfRegistration'] = copy.deepcopy(CHANGE_OF_REGISTRATION)
    gp_change_of_registration['filing']['changeOfRegistration']['parties'][0]['officer']['email'] = 'party@email.com'

    sp_change_of_registration = copy.deepcopy(FILING_HEADER)
    sp_change_of_registration['filing']['header']['name'] = 'changeOfRegistration'
    sp_change_of_registration['filing']['changeOfRegistration'] = copy.deepcopy(CHANGE_OF_REGISTRATION)
    sp_change_of_registration['filing']['changeOfRegistration']['parties'][0]['roles'] = [
        {
            'roleType': 'Completing Party',
            'appointmentDate': '2022-01-01'

        },
        {
            'roleType': 'Proprietor',
            'appointmentDate': '2022-01-01'

        }
    ]
    sp_change_of_registration['filing']['changeOfRegistration']['parties'][0]['officer']['email'] = 'party@email.com'

    if legal_type == Business.LegalTypes.SOLE_PROP.value:
        filing_template = sp_change_of_registration
    elif legal_type == Business.LegalTypes.PARTNERSHIP.value:
        filing_template = gp_change_of_registration

    filing_template['filing']['business'] = {
        'identifier': business.identifier,
        'legalType': legal_type,
        'legalName': legal_name
    }
    if submitter_role:
        filing_template['filing']['header']['documentOptionalEmail'] = f'{submitter_role}@email.com'

    filing = create_filing(
        token=payment_id,
        filing_json=filing_template,
        business_id=business.id)
    filing.payment_completion_date = filing.filing_date

    user = create_user('test_user')
    filing.submitter_id = user.id
    if submitter_role:
        filing.submitter_roles = submitter_role

    filing.save()
    return filing


def prep_alteration_filing(session, identifier, option, company_name):
    """Return an alteration filing prepped for email notification."""
    business = create_business(identifier, legal_type=Business.LegalTypes.BCOMP.value, legal_name=company_name)
    filing_template = copy.deepcopy(ALTERATION_FILING_TEMPLATE)
    filing_template['filing']['business'] = \
        {'identifier': f'{identifier}', 'legalype': Business.LegalTypes.BCOMP.value, 'legalName': company_name}
    filing = create_filing(filing_json=filing_template, business_id=business.id)
    filing.save()

    return filing


def prep_maintenance_filing(session, identifier, payment_id, status, filing_type, submitter_role=None):
    """Return a new maintenance filing prepped for email notification."""
    business = create_business(identifier, Business.LegalTypes.BCOMP.value, LEGAL_NAME)
    filing_template = copy.deepcopy(FILING_TEMPLATE)
    filing_template['filing']['header']['name'] = filing_type
    filing_template['filing']['business'] = \
        {'identifier': f'{identifier}', 'legalype': Business.LegalTypes.BCOMP.value, 'legalName': LEGAL_NAME}
    filing_template['filing'][filing_type] = copy.deepcopy(FILING_TYPE_MAPPER[filing_type])

    if submitter_role:
        filing_template['filing']['header']['documentOptionalEmail'] = f'{submitter_role}@email.com'
    filing = create_filing(token=payment_id, filing_json=filing_template, business_id=business.id)

    user = create_user('test_user')
    filing.submitter_id = user.id
    if submitter_role:
        filing.submitter_roles = submitter_role

    filing.save()
    if status == 'COMPLETED':
        uow = versioning_manager.unit_of_work(session)
        transaction = uow.create_transaction(session)
        filing.transaction_id = transaction.id
        filing.save()

    return filing


def prep_incorporation_correction_filing(session, business, original_filing_id, payment_id, option):
    """Return a new incorporation correction filing prepped for email notification."""
    filing_template = copy.deepcopy(CORRECTION_INCORPORATION)
    filing_template['filing']['business'] = {'identifier': business.identifier}
    for party in filing_template['filing']['correction']['parties']:
        for role in party['roles']:
            if role['roleType'] == 'Completing Party':
                party['officer']['email'] = 'comp_party@email.com'
    filing_template['filing']['correction']['contactPoint']['email'] = 'test@test.com'
    filing_template['filing']['correction']['correctedFilingId'] = original_filing_id
    filing = create_filing(token=payment_id, filing_json=filing_template, business_id=business.id)
    filing.payment_completion_date = filing.filing_date
    filing.save()
    if option in ['COMPLETED']:
        uow = versioning_manager.unit_of_work(session)
        transaction = uow.create_transaction(session)
        filing.transaction_id = transaction.id
        filing.save()
    return filing


def prep_firm_correction_filing(session, identifier, payment_id, legal_type, legal_name, submitter_role):
    """Return a firm correction filing prepped for email notification."""
    business = create_business(identifier, legal_type, legal_name)

    gp_correction = copy.deepcopy(CORRECTION_REGISTRATION)
    gp_correction['filing']['correction']['parties'][0]['officer']['email'] = 'party@email.com'

    sp_correction = copy.deepcopy(CORRECTION_REGISTRATION)
    sp_correction['filing']['correction']['parties'][0]['officer']['email'] = 'party@email.com'
    sp_correction['filing']['correction']['parties'][0]['roles'] = [
        {
            'roleType': 'Completing Party',
            'appointmentDate': '2022-01-01'

        },
        {
            'roleType': 'Proprietor',
            'appointmentDate': '2022-01-01'

        }
    ]
    sp_correction['filing']['correction']['parties'][0]['officer']['email'] = 'party@email.com'

    if legal_type == Business.LegalTypes.SOLE_PROP.value:
        filing_template = sp_correction
    elif legal_type == Business.LegalTypes.PARTNERSHIP.value:
        filing_template = gp_correction

    filing_template['filing']['business'] = {
        'identifier': business.identifier,
        'legalType': legal_type,
        'legalName': legal_name
    }

    filing = create_filing(
        token=payment_id,
        filing_json=filing_template,
        business_id=business.id)
    filing.payment_completion_date = filing.filing_date

    user = create_user('test_user')
    filing.submitter_id = user.id
    if submitter_role:
        filing.submitter_roles = submitter_role

    filing.save()
    return filing


def prep_cp_special_resolution_filing(identifier, payment_id, legal_type, legal_name, submitter_role=None):
    """Return a new cp special resolution out filing prepped for email notification."""
    business = create_business(identifier, legal_type=legal_type, legal_name=legal_name)
    filing_template = copy.deepcopy(CP_SPECIAL_RESOLUTION_TEMPLATE)
    filing_template['filing']['business'] = \
        {'identifier': f'{identifier}', 'legalype': legal_type, 'legalName': legal_name}
    filing_template['filing']['alteration'] = {
        'business': {
            'identifier': 'BC1234567',
            'legalType': 'BEN'
        },
        'contactPoint': {
            'email': 'joe@email.com'
        },
        'rulesInResolution': True,
        'rulesFileKey': 'cooperative/a8abe1a6-4f45-4105-8a05-822baee3b743.pdf'
    }
    if submitter_role:
        filing_template['filing']['header']['documentOptionalEmail'] = f'{submitter_role}@email.com'
    filing = create_filing(token=payment_id, filing_json=filing_template, business_id=business.id)

    user = create_user('cp_test_user')
    filing.submitter_id = user.id
    if submitter_role:
        filing.submitter_roles = submitter_role
    filing.save()
    return filing


def prep_cp_special_resolution_correction_filing(session, business, original_filing_id,
                                                 payment_id, option, corrected_filing_type):
    """Return a cp special resolution correction filing prepped for email notification."""
    filing_template = copy.deepcopy(FILING_HEADER)
    filing_template['filing']['header']['name'] = 'correction'
    filing_template['filing']['correction'] = copy.deepcopy(CORRECTION_CP_SPECIAL_RESOLUTION)
    filing_template['filing']['business'] = {'identifier': business.identifier}
    filing_template['filing']['correction']['contactPoint']['email'] = 'cp_sr@test.com'
    filing_template['filing']['correction']['correctedFilingId'] = original_filing_id
    filing_template['filing']['correction']['correctedFilingType'] = corrected_filing_type
    filing_template['filing']['correction']['nameRequest'] = {
        'nrNumber': 'NR 8798956',
        'legalName': 'HAULER MEDIA INC.',
        'legalType': 'BC'
    }
    filing = create_filing(token=payment_id, filing_json=filing_template, business_id=business.id)
    filing.payment_completion_date = filing.filing_date
    filing.save()
    if option in ['COMPLETED']:
        uow = versioning_manager.unit_of_work(session)
        transaction = uow.create_transaction(session)
        filing.transaction_id = transaction.id
        filing.save()
    return filing


class Obj:
    """Make a custom object hook used by dict_to_obj."""

    def __init__(self, dict1):
        """Create instance of obj."""
        self.__dict__.update(dict1)


def dict_to_obj(dict1):
    """Convert dict to an object."""
    return json.loads(json.dumps(dict1), object_hook=Obj)


def create_mock_message(message_payload: dict):
    """Return a mock message that can be processed by the queue listener."""
    mock_msg = Mock()
    mock_msg.sequence = randrange(1000)
    mock_msg.data = dict_to_obj(message_payload)
    json_msg_payload = json.dumps(message_payload)
    mock_msg.data.decode = Mock(return_value=json_msg_payload)
    return mock_msg
