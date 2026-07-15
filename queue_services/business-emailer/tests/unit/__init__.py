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

from business_model.models import Batch, Business, Filing, Furnishing, Party, PartyRole, RegistrationBootstrap, User
from business_model.models.db import VersioningProxy
from registry_schemas.example_data import (
    AGM_EXTENSION,
    AGM_LOCATION_CHANGE,
    ALTERATION,
    ALTERATION_FILING_TEMPLATE,
    AMALGAMATION_APPLICATION,
    AMALGAMATION_OUT,
    ANNUAL_REPORT,
    CHANGE_OF_RECEIVERS,
    CHANGE_OF_DIRECTORS,
    CHANGE_OF_LIQUIDATORS,
    CHANGE_OF_REGISTRATION,
    CONSENT_AMALGAMATION_OUT,
    CONSENT_CONTINUATION_OUT,
    CONTINUATION_IN_FILING_TEMPLATE,
    CONTINUATION_OUT,
    CORP_CHANGE_OF_ADDRESS,
    CORRECTION_CP_SPECIAL_RESOLUTION,
    CORRECTION_INCORPORATION,
    CORRECTION_REGISTRATION,
    DISSOLUTION,
    FILING_HEADER,
    FILING_TEMPLATE,
    INCORPORATION_FILING_TEMPLATE,
    NOTICE_OF_WITHDRAWAL,
    REGISTRATION,
    RESTORATION,
    SPECIAL_RESOLUTION,
)

from tests.unit.helpers import generate_temp_filing
from tests import EPOCH_DATETIME


AMALGAMATION_APPLICATION_TEMPLATE = copy.deepcopy(FILING_TEMPLATE)
AMALGAMATION_APPLICATION_TEMPLATE['filing']['header']['name'] = 'amalgamationApplication'
AMALGAMATION_APPLICATION_TEMPLATE['filing']['amalgamationApplication'] = copy.deepcopy(AMALGAMATION_APPLICATION)
REGISTRATION_TEMPLATE = copy.deepcopy(FILING_TEMPLATE)
REGISTRATION_TEMPLATE['filing']['header']['name'] = 'registration'
REGISTRATION_TEMPLATE['filing']['registration'] = copy.deepcopy(REGISTRATION)

BOOTSTRAP_TYPE_MAPPER = {
    'amalgamationApplication': AMALGAMATION_APPLICATION_TEMPLATE,
    'continuationIn': CONTINUATION_IN_FILING_TEMPLATE,
    'incorporationApplication': INCORPORATION_FILING_TEMPLATE,
    'registration': REGISTRATION_TEMPLATE,
}

# NB: These do not include the header or business in their templates
FILING_TYPE_MAPPER = {
    'alteration': ALTERATION,
    'annualReport': ANNUAL_REPORT['filing']['annualReport'],
    'changeOfAddress': CORP_CHANGE_OF_ADDRESS,
    'changeOfDirectors': CHANGE_OF_DIRECTORS,
    'changeOfRegistration': CHANGE_OF_REGISTRATION,
    'dissolution': DISSOLUTION,
    'restoration': RESTORATION,
    'specialResolution': SPECIAL_RESOLUTION
}

CORRECTION_TYPE_MAPPER = {
    'incorporationApplication': CORRECTION_INCORPORATION['filing']['correction'],
    'registration': CORRECTION_REGISTRATION['filing']['correction'],
    'specialResolution': CORRECTION_CP_SPECIAL_RESOLUTION
}

COMP_PARTY_EMAIL = 'comp_party@email.com'
CONTACT_POINT = 'contact@point.com'
LEGAL_NAME = 'test business'
PARTY_EMAIL_1 = 'party1@email.com'
PARTY_EMAIL_2 = 'party2@email.com'


def _prep_parties_for_filing(filing_template: dict, filing_type: str, legal_type: str):
    """Update the parties in the filing template with expected data."""
    if filing_template['filing'][filing_type].get('parties'):
        filing_template['filing'][filing_type]['parties'] = filing_template['filing'][filing_type]['parties'][:2]
        for index, party in enumerate(filing_template['filing'][filing_type]['parties']):
            for role in party['roles']:
                if legal_type not in ['SP', 'GP'] and role['roleType'] == 'Completing Party':
                    party['officer']['email'] = COMP_PARTY_EMAIL
                    break
                elif index == 0:
                    party['officer']['email'] = PARTY_EMAIL_1
                else:
                    party['officer']['email'] = PARTY_EMAIL_2
        if legal_type == 'SP':
            filing_template['filing'][filing_type]['parties'] = filing_template['filing'][filing_type]['parties'][:1]
            filing_template['filing'][filing_type]['parties'][0]['roles'] = [
                {
                    'roleType': 'Completing Party',
                    'appointmentDate': '2022-01-01'

                },
                {
                    'roleType': 'Proprietor',
                    'appointmentDate': '2022-01-01'

                }
            ]

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


def create_filing(token=None, filing_json=None, business_id=None,
                  filing_date=EPOCH_DATETIME, bootstrap_id: str = None, meta_data=None):
    """Return a test filing."""
    filing = Filing()
    if token:
        filing.payment_token = str(token)
    filing._payment_completion_date = filing_date
    filing.filing_date = filing_date
    filing.effective_date = filing_date

    if filing_json:
        filing.filing_json = filing_json
    if meta_data:
        filing._meta_data = meta_data
    if business_id:
        filing.business_id = business_id
    if bootstrap_id:
        filing.temp_reg = bootstrap_id

    filing.save()
    return filing


def prep_bootstrap_filing(session, filing_type, identifier, legal_type, option, legal_name=None, filing_sub_type=None, parties=None):
    """Return a new bootstrap filing prepped for email notification."""
    if not filing_sub_type and filing_type == 'amalgamationApplication':
        filing_sub_type = 'regular'

    filing_template = copy.deepcopy(BOOTSTRAP_TYPE_MAPPER[filing_type])
    filing_template['filing']['business'] = {
        'legalType': legal_type
    }
    filing_template['filing'][filing_type]['nameRequest'] = {'legalType': legal_type}
    filing_template['filing'][filing_type]['contactPoint'] = {'email': CONTACT_POINT}

    if legal_name:
        filing_template['filing'][filing_type]['nameRequest']['legalName'] = legal_name
    
    if filing_sub_type:
        sub_type_key = Filing.FILING_SUB_TYPE_KEYS.get(filing_type, 'type')
        filing_template['filing'][filing_type][sub_type_key] = filing_sub_type
    
    _prep_parties_for_filing(filing_template, filing_type, legal_type)
    
    if filing_type == 'registration':
        filing_template['filing']['business']['naics'] = {
            'naicsCode': '112320',
            'naicsDescription': 'Broiler and other meat-type chicken production'
        }
        filing_template['filing']['registration']['startDate'] = datetime.now().strftime('%Y-%m-%d')
        if legal_type != 'GP':
            filing_template['filing']['registration']['businessType'] = legal_type

    if legal_type == 'CP':
        filing_template['filing'][filing_type]['cooperative'] = {
            'cooperativeAssociationType': 'CP',
            'rulesFileKey': 'rulekey1234',
            'memorandumFileKey': 'memkey1234'
        }
    temp_identifier = generate_temp_filing()
    filing_template['filing']['business']['identifier'] = temp_identifier
    filing = create_filing(token='1', filing_json=filing_template, bootstrap_id=temp_identifier)
    filing._filing_sub_type = filing_sub_type
    filing.payment_completion_date = filing.filing_date

    if option in ['COMPLETED', 'bn', 'mras']:
        legal_name = legal_name or f'{identifier[2:]} B.C. Ltd.'
        business = create_business(identifier, legal_type=legal_type, legal_name=legal_name, parties=parties)
        filing.business_id = business.id
        transaction_id = VersioningProxy.get_transaction_id(session())
        filing.transaction_id = transaction_id

    filing.save()
    return filing
    

def prep_incorp_filing(session, identifier, option, legal_type='BC', legal_name=LEGAL_NAME):
    """Return a new incorp filing prepped for email notification."""
    return prep_bootstrap_filing(session, 'incorporationApplication', identifier, legal_type, option, legal_name=legal_name)


def prep_registration_filing(session, identifier, option, legal_type, legal_name, parties=None):
    """Return a new registration filing prepped for email notification."""
    return prep_bootstrap_filing(session, 'registration', identifier, legal_type, option, legal_name=legal_name, parties=parties)


def prep_consent_amalgamation_out_filing(session, identifier, payment_id, legal_type, legal_name, submitter_role):
    """Return a new consent amalgamation out filing prepped for email notification."""
    business = create_business(identifier, legal_type, legal_name)
    filing_template = copy.deepcopy(FILING_HEADER)
    filing_template['filing']['header']['name'] = 'consentAmalgamationOut'
    if submitter_role:
        filing_template['filing']['header']['documentOptionalEmail'] = f'{submitter_role}@email.com'

    filing_template['filing']['consentAmalgamationOut'] = copy.deepcopy(CONSENT_AMALGAMATION_OUT)
    filing_template['filing']['business'] = {
        'identifier': business.identifier,
        'legalType': legal_type,
        'legalName': legal_name
    }
    test_meta_data = {
        'consentAmalgamationOut': {
            'expiry': '2025-10-31T06:59:00+00:00',
            'region': 'AB',
            'country': 'CA'
        }
    }

    filing = create_filing(
        token=payment_id,
        filing_json=filing_template,
        business_id=business.id,
        meta_data=test_meta_data)
    filing.payment_completion_date = filing.filing_date

    user = create_user('test_user')
    filing.submitter_id = user.id
    if submitter_role:
        filing.submitter_roles = submitter_role

    filing.save()
    return filing


def prep_amalgamation_out_filing(session, identifier, payment_id, legal_type, legal_name, submitter_role):
    """Return a new amalgamation out filing prepped for email notification."""
    business = create_business(identifier, legal_type, legal_name)
    filing_template = copy.deepcopy(FILING_HEADER)
    filing_template['filing']['header']['name'] = 'amalgamationOut'
    if submitter_role:
        filing_template['filing']['header']['documentOptionalEmail'] = f'{submitter_role}@email.com'

    filing_template['filing']['amalgamationOut'] = copy.deepcopy(AMALGAMATION_OUT)
    filing_template['filing']['business'] = {
        'identifier': business.identifier,
        'legalType': legal_type,
        'legalName': legal_name
    }
    test_meta_data = {
        'amalgamationOut': {
            'amalgamationOutDate': '2025-04-29',
            'legalName': 'test business',
            'region': None,
            'country': 'AL'
        }
    }

    filing = create_filing(
        token=payment_id,
        filing_json=filing_template,
        business_id=business.id,
        meta_data=test_meta_data)
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


def prep_change_of_registration_filing(session, identifier, payment_id, legal_type,
                                       legal_name, submitter_role, parties=None):
    """Return a new change of registration filing prepped for email notification."""
    return prep_maintenance_filing(session, identifier, payment_id, 'COMPLETED', 'changeOfRegistration', None, submitter_role, legal_type, parties)


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


def prep_maintenance_filing(session, identifier, payment_id, status, filing_type,
                            filing_sub_type=None, submitter_role=None, legal_type=None, parties=None, template_overrides={}):
    """Return a new maintenance filing prepped for email notification."""
    if not legal_type:
        legal_type = Business.LegalTypes.COOP.value if identifier.startswith('CP') else Business.LegalTypes.BCOMP.value
    business = create_business(identifier, legal_type, LEGAL_NAME, parties)
    filing_template = copy.deepcopy(FILING_TEMPLATE)
    filing_template['filing']['header']['name'] = filing_type
    filing_template['filing']['business'] = {
        'identifier': identifier,
        'legalType': legal_type,
        'legalName': business.legal_name
    }
    filing_template['filing'][filing_type] = copy.deepcopy(FILING_TYPE_MAPPER[filing_type])
    filing_template['filing'][filing_type]['contactPoint'] = {'email': CONTACT_POINT}
    _prep_parties_for_filing(filing_template, filing_type, legal_type)

    if filing_sub_type:
        sub_type_key = Filing.FILING_SUB_TYPE_KEYS.get(filing_type, 'type')
        filing_template['filing'][filing_type][sub_type_key] = filing_sub_type

    if submitter_role:
        filing_template['filing']['header']['documentOptionalEmail'] = f'{submitter_role}@email.com'
    
    filing_template['filing'] = {
        **filing_template['filing'],
        # add any extra data or overwrite as required
        **template_overrides
    }

    filing = create_filing(token=payment_id, filing_json=filing_template, business_id=business.id)

    user = create_user('test_user')
    filing.submitter_id = user.id
    if submitter_role:
        filing.submitter_roles = submitter_role

    filing.save()
    if status == 'COMPLETED':
        transaction_id = VersioningProxy.get_transaction_id(session())
        filing.transaction_id = transaction_id
        filing.save()

    return filing


def prep_special_resolution_filing(session, identifier='CP1234567', submitter_role=None, has_name_change=False, has_rule_change=False):
    """Return a new special resolution out filing prepped for email notification."""
    filing_template_overrides = {}
    if has_name_change:
        filing_template_overrides['changeOfName'] = {
            'nameRequest': {
                'nrNumber': 'NR 8798956',
                'legalName': 'HAULER MEDIA INC.',
                'legalType': 'BC'
            }   
        }
    if has_rule_change:
        filing_template_overrides['alteration'] = {
            'rulesInResolution': True,
            'rulesFileKey': 'cooperative/a8abe1a6-4f45-4105-8a05-822baee3b743.pdf'
        }
    return prep_maintenance_filing(session, identifier, '1', 'COMPLETED', 'specialResolution', None, submitter_role, template_overrides=filing_template_overrides)


def prep_correction_filing(session,
                           business: Business,
                           original_filing_id: int,
                           original_filing_type: str,
                           status: str,
                           has_name_change=False,
                           has_rule_change=False,
                           has_memorandum_change=False):
    """Return a correction filing prepped for email notification."""
    filing_template = copy.deepcopy(FILING_HEADER)
    filing_template['filing']['header']['name'] = 'correction'
    filing_template['filing']['correction'] = copy.deepcopy(CORRECTION_TYPE_MAPPER[original_filing_type])
    filing_template['filing']['business'] = {'identifier': business.identifier}
    filing_template['filing']['correction']['contactPoint']['email'] = CONTACT_POINT
    filing_template['filing']['correction']['correctedFilingId'] = original_filing_id
    filing_template['filing']['correction']['correctedFilingType'] = original_filing_type
    # Update the parties (schema examples do not reflect a real payload for the correction case)
    filing_template['filing']['correction']['parties'] = filing_template['filing']['correction']['parties'][:1]
    # Remove completing party role (examples contain it as an extra role, but the real payload does not)
    filing_template['filing']['correction']['parties'][0]['roles'] = [
        role for role in filing_template['filing']['correction']['parties'][0]['roles']
        if role['roleType'] != 'Completing Party'
    ]
    # Add completing party as a separate party with no email
    filing_template['filing']['correction']['parties'].append({
        'officer': {
            'firstName': 'Completing',
            'lastName': 'Party',
            'partyType': 'person'
        },
        'mailingAddress': {
            'streetAddress': 'mailing_address - address line one',
            'addressCity': 'mailing_address city',
            'addressCountry': 'CA',
            'postalCode': 'H0H0H0',
            'addressRegion': 'BC'
        },
        'roles': [
            {
                'roleType': 'Completing Party',
                'appointmentDate': datetime.now().strftime('%Y-%m-%d')
            }
        ]
    })

    _prep_parties_for_filing(filing_template, 'correction', business.legal_type)

    filing_template['filing']['correction']['nameRequest'] = {
        'nrNumber': 'NR 8798956',
        'legalName': 'HAULER MEDIA INC.',
        'legalType': business.legal_type,
        'requestTypeCd': 'CHG'
    }
    filing_template['filing']['correction']['rulesFileKey'] = 'ruleskey1234'
    filing_template['filing']['correction']['memorandumFileKey'] = 'memkey1234'

    if not has_name_change:
        del filing_template['filing']['correction']['nameRequest']
    if not has_rule_change:
        del filing_template['filing']['correction']['rulesFileKey']
    if not has_memorandum_change:
        del filing_template['filing']['correction']['memorandumFileKey']

    filing = create_filing(token='1', filing_json=filing_template, business_id=business.id)

    filing.save()
    if status == 'COMPLETED':
        transaction_id = VersioningProxy.get_transaction_id(session())
        filing.transaction_id = transaction_id
        filing.save()

    return filing


def prep_intent_to_liquidate_filing(session, identifier, payment_id, legal_type, legal_name, submitter_role):
    """Return a new intent to liquidate filing prepped for email notification."""
    business = create_business(identifier, legal_type, legal_name)
    filing_template = copy.deepcopy(FILING_HEADER)
    filing_template['filing']['header']['name'] = 'changeOfLiquidators'
    if submitter_role:
        filing_template['filing']['header']['documentOptionalEmail'] = f'{submitter_role}@email.com'

    filing_template['filing']['changeOfLiquidators'] = copy.deepcopy(CHANGE_OF_LIQUIDATORS)
    # Override liquidation date to be after founding date
    future_date = (datetime.utcnow() + timedelta(days=30)).strftime('%Y-%m-%d')
    filing_template['filing']['intentToLiquidate']['dateOfCommencementOfLiquidation'] = future_date
    filing_template['filing']['business'] = {
        'identifier': business.identifier,
        'legalType': legal_type,
        'legalName': legal_name
    }
    test_meta_data = {
        'intentToLiquidate': {
            'dateOfCommencementOfLiquidation': future_date
        }
    }

    filing = create_filing(
        token=payment_id,
        filing_json=filing_template,
        business_id=business.id,
        meta_data=test_meta_data)
    filing.payment_completion_date = filing.filing_date

    user = create_user('test_user')
    filing.submitter_id = user.id
    if submitter_role:
        filing.submitter_roles = submitter_role

    filing.save()
    return filing


def prep_cease_receiver_filing(identifier, payment_id, legal_type, legal_name):
    """Return a new Cease Receiver filing prepped for email notification."""
    business = create_business(identifier, legal_type, legal_name)
    filing_template = copy.deepcopy(FILING_HEADER)
    filing_template['filing']['header']['name'] = 'changeOfReceivers'
    filing_template['filing']['changeOfReceivers'] = copy.deepcopy(CHANGE_OF_RECEIVERS)
    filing_template['filing']['changeOfReceivers']['type'] = 'ceaseReceiver'
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


def prep_appoint_receiver_filing(identifier, payment_id, legal_type, legal_name):
    """Return a new Appoint Receiver filing prepped for email notification."""
    business = create_business(identifier, legal_type, legal_name)
    filing_template = copy.deepcopy(FILING_HEADER)
    filing_template['filing']['header']['name'] = 'changeOfReceivers'

    filing_template['filing']['appointReceiver'] = copy.deepcopy(CHANGE_OF_RECEIVERS)
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


def prep_notice_of_withdraw_filing(
        identifier,
        payment_id,
        legal_type,
        legal_name,
        business_id,
        withdrawn_filing):
    """Return a new Notice of Withdrawal filing prepped for email notification."""
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


def create_future_effective_filing(
        identifier,
        legal_type,
        legal_name,
        filing_type,
        filing_json,
        is_temp,
        business_id=None):
    """Create a future effective filing."""
    filing_template = copy.deepcopy(FILING_HEADER)
    filing_template['filing']['header']['name'] = filing_type
    future_effective_date = EPOCH_DATETIME + timedelta(days=5)
    future_effective_date = future_effective_date.isoformat()

    if is_temp:
        del filing_template['filing']['business']
        new_business_filing_json = copy.deepcopy(filing_json)
        new_business_filing_json['nameRequest']['legalType'] = legal_type
        new_business_filing_json['nameRequest']['legalName'] = legal_name
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
