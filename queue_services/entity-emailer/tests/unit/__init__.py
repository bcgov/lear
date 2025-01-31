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
from datetime import datetime, timedelta
from random import randrange
from unittest.mock import Mock

from legal_api.models import Batch, Business, Filing, Furnishing, Party, PartyRole, RegistrationBootstrap, User
from legal_api.models.db import versioning_manager
from registry_schemas.example_data import (
    AGM_EXTENSION,
    AGM_LOCATION_CHANGE,
    ALTERATION,
    ALTERATION_FILING_TEMPLATE,
    AMALGAMATION_APPLICATION,
    ANNUAL_REPORT,
    CHANGE_OF_DIRECTORS,
    CHANGE_OF_REGISTRATION,
    CONSENT_CONTINUATION_OUT,
    CONTINUATION_IN_FILING_TEMPLATE,
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
    NOTICE_OF_WITHDRAWAL,
    REGISTRATION,
    RESTORATION,
)

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


def create_business(identifier, legal_type=None, legal_name=None, parties=None):
    """Return a test business."""
    business = Business()
    business.identifier = identifier
    business.legal_type = legal_type
    business.legal_name = legal_name

    for party in (parties or []):
        if business.legal_type == Business.LegalTypes.SOLE_PROP:
            proprietor_role = create_party_role(None, None, party, None, None, PartyRole.RoleTypes.PROPRIETOR)
            business.party_roles.append(proprietor_role)
        elif legal_type == Business.LegalTypes.PARTNERSHIP:
            partner_role = create_party_role(None, None, party, None, None, PartyRole.RoleTypes.PARTNER)
            business.party_roles.append(partner_role)

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


def prep_dissolution_filing(session, identifier, payment_id, option, legal_type,
                            legal_name, submitter_role, parties=None):
    """Return a new dissolution filing prepped for email notification."""
    business = create_business(identifier, legal_type, legal_name, parties)
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


def prep_change_of_registration_filing(session, identifier, payment_id, legal_type,
                                       legal_name, submitter_role, parties=None):
    """Return a new change of registration filing prepped for email notification."""
    business = create_business(identifier, legal_type, legal_name, parties)

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


def prep_agm_location_change_filing(identifier, payment_id, legal_type, legal_name):
    """Return a new AGM location change filing prepped for email notification."""
    business = create_business(identifier, legal_type, legal_name)
    filing_template = copy.deepcopy(FILING_HEADER)
    filing_template['filing']['header']['name'] = 'agmLocationChange'

    filing_template['filing']['agmLocationChange'] = copy.deepcopy(AGM_LOCATION_CHANGE)
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


def prep_agm_extension_filing(identifier, payment_id, legal_type, legal_name):
    """Return a new AGM extension filing prepped for email notification."""
    business = create_business(identifier, legal_type, legal_name)
    filing_template = copy.deepcopy(FILING_HEADER)
    filing_template['filing']['header']['name'] = 'agmExtension'

    filing_template['filing']['agmExtension'] = copy.deepcopy(AGM_EXTENSION)
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


def prep_firm_correction_filing(session, identifier, payment_id, legal_type, legal_name, submitter_role, parties=None):
    """Return a firm correction filing prepped for email notification."""
    business = create_business(identifier, legal_type, legal_name, parties)

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
        'legalType': 'BC',
        'requestType': 'CHG'
    }
    filing = create_filing(token=payment_id, filing_json=filing_template, business_id=business.id)
    filing.payment_completion_date = filing.filing_date
    # Triggered from the filer.
    filing._meta_data = {'correction': {'uploadNewRules': True, 'toLegalName': True}}
    filing.save()
    if option in ['COMPLETED']:
        uow = versioning_manager.unit_of_work(session)
        transaction = uow.create_transaction(session)
        filing.transaction_id = transaction.id
        filing.save()
    return filing


def prep_cp_special_resolution_correction_upload_memorandum_filing(session, business,
                                                                   original_filing_id,
                                                                   payment_id, option,
                                                                   corrected_filing_type):
    """Return a cp special resolution correction filing prepped for email notification."""
    filing_template = copy.deepcopy(FILING_HEADER)
    filing_template['filing']['header']['name'] = 'correction'
    filing_template['filing']['correction'] = copy.deepcopy(CORRECTION_CP_SPECIAL_RESOLUTION)
    filing_template['filing']['business'] = {'identifier': business.identifier}
    filing_template['filing']['correction']['contactPoint']['email'] = 'cp_sr@test.com'
    filing_template['filing']['correction']['correctedFilingId'] = original_filing_id
    filing_template['filing']['correction']['correctedFilingType'] = corrected_filing_type
    del filing_template['filing']['correction']['resolution']
    filing_template['filing']['correction']['memorandumFileKey'] = '28f73dc4-8e7c-4c89-bef6-a81dff909ca6.pdf'
    filing_template['filing']['correction']['memorandumFileName'] = 'test.pdf'
    filing = create_filing(token=payment_id, filing_json=filing_template, business_id=business.id)
    filing.payment_completion_date = filing.filing_date
    # Triggered from the filer.
    filing._meta_data = {'correction': {'uploadNewMemorandum': True}}
    filing.save()
    if option in ['COMPLETED']:
        uow = versioning_manager.unit_of_work(session)
        transaction = uow.create_transaction(session)
        filing.transaction_id = transaction.id
        filing.save()
    return filing


def prep_amalgamation_filing(session, identifier, payment_id, option, legal_name):
    """Return a new incorp filing prepped for email notification."""
    business = create_business(identifier, legal_type=Business.LegalTypes.BCOMP.value, legal_name=legal_name)
    filing_template = copy.deepcopy(FILING_HEADER)
    filing_template['filing']['header']['name'] = 'amalgamationApplication'

    filing_template['filing']['amalgamationApplication'] = copy.deepcopy(AMALGAMATION_APPLICATION)
    filing_template['filing']['amalgamationApplication']['nameRequest'] = {
        'identifier': business.identifier,
        'legalType': Business.LegalTypes.BCOMP.value,
        'legalName': legal_name
    }
    filing_template['filing']['business'] = {'identifier': business.identifier}
    for party in filing_template['filing']['amalgamationApplication']['parties']:
        for role in party['roles']:
            if role['roleType'] == 'Completing Party':
                party['officer']['email'] = 'comp_party@email.com'
    filing_template['filing']['amalgamationApplication']['contactPoint']['email'] = 'test@test.com'

    temp_identifier = 'Tb31yQIuBw'
    temp_reg = RegistrationBootstrap()
    temp_reg._identifier = temp_identifier
    temp_reg.save()
    filing = create_filing(token=payment_id, filing_json=filing_template,
                           business_id=business.id, bootstrap_id=temp_identifier)
    filing.payment_completion_date = filing.filing_date
    filing.save()
    if option in [Filing.Status.COMPLETED.value, 'bn']:
        uow = versioning_manager.unit_of_work(session)
        transaction = uow.create_transaction(session)
        filing.transaction_id = transaction.id
        filing.save()
    return filing


def prep_continuation_in_filing(session, identifier, payment_id, option):
    """Return a new incorp filing prepped for email notification."""
    business = create_business(identifier, legal_type=Business.LegalTypes.BCOMP_CONTINUE_IN.value)
    filing_template = copy.deepcopy(CONTINUATION_IN_FILING_TEMPLATE)
    if business.legal_type:
        filing_template['filing']['continuationIn']['nameRequest']['legalType'] = business.legal_type
    for party in filing_template['filing']['continuationIn']['parties']:
        for role in party['roles']:
            if role['roleType'] == 'Completing Party':
                party['officer']['email'] = 'comp_party@email.com'
    filing_template['filing']['continuationIn']['contactPoint']['email'] = 'test@test.com'

    temp_identifier = 'Tb31yQIuBw'
    temp_reg = RegistrationBootstrap()
    temp_reg._identifier = temp_identifier
    temp_reg.save()
    filing = create_filing(token=payment_id, filing_json=filing_template,
                           business_id=business.id, bootstrap_id=temp_identifier)
    filing.payment_completion_date = filing.filing_date
    filing.save()
    if option in [Filing.Status.COMPLETED.value, 'bn']:
        uow = versioning_manager.unit_of_work(session)
        transaction = uow.create_transaction(session)
        filing.transaction_id = transaction.id
        filing.save()
    return filing


def prep_notice_of_withdraw_filing(identifier, payment_id, legal_type, legal_name, business_id, withdrawn_filing:Filing):
    """Return a new Notice of Withdrawal filing prepped for email notification"""
    filing_template = copy.deepcopy(FILING_HEADER)
    filing_template['filing']['header']['name'] = 'noticeOfWithdrawal'

    filing_template['filing']['noticeOfWithdrawal'] = copy.deepcopy(NOTICE_OF_WITHDRAWAL)
    filing_template['filing']['noticeOfWithdrawal']['filingId'] = withdrawn_filing.id
    filing_template['filing']['business'] = {
        'identifier': identifier,
        'legalType': legal_type,
        'legalName': legal_name
    }

    # create NoW filing
    filing = create_filing(
        token=payment_id,
        filing_json=filing_template,
        business_id=business_id,
    )
    # populate NoW related properties
    filing.withdrawn_filing_id = withdrawn_filing.id
    filing.save()
    withdrawn_filing.withdrawal_pending = True
    withdrawn_filing.save()

    return filing


def create_future_effective_filing(identifier, legal_type, legal_name, filing_type, filing_json, is_temp, business_id=None):
    filing_template = copy.deepcopy(FILING_HEADER)
    filing_template['filing']['header']['name'] = filing_type
    future_effective_date = EPOCH_DATETIME + timedelta(days=5)
    future_effective_date = future_effective_date.isoformat()

    if is_temp:
        del filing_template['filing']['business']
        new_business_filing_json = copy.deepcopy(filing_json)
        new_business_filing_json['nameRequest']['legalType'] = legal_type
        filing_template['filing'][filing_type] = new_business_filing_json
        filing_template['filing'][filing_type]['contactPoint']['email'] = 'recipient@email.com'
    else:
        filing_template['filing']['business']['identifier'] = identifier
        filing_template['filing']['business'] = {
            'identifier': identifier,
            'legalType': legal_type,
            'legalName': legal_name
        }
        fe_filing_json = copy.deepcopy(filing_json)
        filing_template['filing'][filing_type] = fe_filing_json
    
    fe_filing = Filing()
    fe_filing.filing_date = EPOCH_DATETIME
    fe_filing.filing_json = filing_template
    fe_filing.save()
    fe_filing.payment_token = '123'
    fe_filing.payment_completion_date = EPOCH_DATETIME.isoformat()
    if is_temp:
        fe_filing.temp_reg = identifier
    else:
        fe_filing.business_id = business_id
    fe_filing.effective_date = future_effective_date
    fe_filing.save()

    return fe_filing


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


def create_batch():
    """Return a test batch."""
    batch = Batch()
    batch.batch_type = Batch.BatchType.INVOLUNTARY_DISSOLUTION
    batch.status = Batch.BatchStatus.PROCESSING
    batch.save()
    return batch


def create_furnishing(session, business=None, batch_id=None,
                      email='test@test.com', furnishing_name='DISSOLUTION_COMMENCEMENT_NO_AR'):
    """Return a test furnishing."""
    furnishing = Furnishing()
    furnishing.furnishing_type = 'EMAIL'
    furnishing.furnishing_name = furnishing_name
    furnishing.status = Furnishing.FurnishingStatus.QUEUED
    furnishing.email = email
    if business:
        furnishing.business_id = business.id
        furnishing.business_identifier = business.identifier
    else:
        business = create_business(identifier='BC123232', legal_type='BC', legal_name='Test Business')
        furnishing.business_id = business.id
        furnishing.business_identifier = business.identifier
    if not batch_id:
        batch = create_batch()
        furnishing.batch_id = batch.id
    else:
        furnishing.batch_id = batch_id
    furnishing.save()
    return furnishing


def create_party_role(delivery_address, mailing_address, officer, appointment_date, cessation_date, role_type):
    """Create a role."""
    party = Party(
        first_name=officer['firstName'],
        last_name=officer['lastName'],
        middle_initial=officer['middleInitial'],
        party_type=officer['partyType'],
        organization_name=officer['organizationName']
    )
    party.delivery_address = delivery_address
    party.mailing_address = mailing_address
    party.save()
    party_role = PartyRole(
        role=role_type.value,
        appointment_date=appointment_date,
        cessation_date=cessation_date,
        party_id=party.id
    )
    return party_role
