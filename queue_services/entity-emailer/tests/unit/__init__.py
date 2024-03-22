# Copyright © 2023 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the "License");
# you may not use this file except in compliance with the License.
# The template for the license can be found here
#    https://opensource.org/license/bsd-3-clause/
#
# Redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
"""The Unit Tests and the helper routines."""
import copy
import json
from contextlib import contextmanager
from datetime import datetime
from random import randrange
from unittest.mock import Mock

from legal_api.models import Filing, LegalEntity, RegistrationBootstrap, User
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
    "annualReport": ANNUAL_REPORT["filing"]["annualReport"],
    "changeOfAddress": CORP_CHANGE_OF_ADDRESS,
    "changeOfDirectors": CHANGE_OF_DIRECTORS,
    "alteration": ALTERATION,
}

LEGAL_NAME = "test business"


def create_user(user_name: str):
    """Return a new user model."""
    user = User()
    user.username = user_name
    user.save()
    return user


def create_legal_entity(identifier, legal_type=None, legal_name=None):
    """Return a test legal entity."""
    legal_entity = LegalEntity()
    legal_entity.identifier = identifier
    legal_entity.legal_type = legal_type
    legal_entity.legal_name = legal_name
    legal_entity.save()
    return legal_entity


def create_filing(
    token=None, filing_json=None, legal_entity_id=None, filing_date=EPOCH_DATETIME, bootstrap_id: str = None
):
    """Return a test filing."""
    filing = Filing()
    if token:
        filing.payment_token = str(token)
    filing.filing_date = filing_date

    if filing_json:
        filing.filing_json = filing_json
    if legal_entity_id:
        filing.legal_entity_id = legal_entity_id
    if bootstrap_id:
        filing.temp_reg = bootstrap_id

    filing.save()
    return filing


def prep_incorp_filing(session, identifier, payment_id, option, legal_type=None):
    """Return a new incorp filing prepped for email notification."""
    legal_entity = create_legal_entity(identifier, legal_type=legal_type, legal_name=LEGAL_NAME)
    filing_template = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    filing_template["filing"]["business"] = {"identifier": legal_entity.identifier}
    if legal_entity.legal_type:
        filing_template["filing"]["business"]["legalType"] = legal_entity.legal_type
        filing_template["filing"]["incorporationApplication"]["nameRequest"]["legalType"] = legal_entity.legal_type
    for party in filing_template["filing"]["incorporationApplication"]["parties"]:
        for role in party["roles"]:
            if role["roleType"] == "Completing Party":
                party["officer"]["email"] = "comp_party@email.com"
    filing_template["filing"]["incorporationApplication"]["contactPoint"]["email"] = "test@test.com"

    temp_identifier = "Tb31yQIuBw"
    temp_reg = RegistrationBootstrap()
    temp_reg._identifier = temp_identifier
    temp_reg.save()
    filing = create_filing(
        token=payment_id, filing_json=filing_template, legal_entity_id=legal_entity.id, bootstrap_id=temp_identifier
    )
    filing.payment_completion_date = filing.filing_date
    filing.save()
    if option in ["COMPLETED", "bn"]:
        uow = versioning_manager.unit_of_work(session)
        transaction = uow.create_transaction(session)
        filing.transaction_id = transaction.id
        filing.save()
    return filing


def prep_registration_filing(session, identifier, payment_id, option, legal_type, legal_name):
    """Return a new registration filing prepped for email notification."""
    now = datetime.now().strftime("%Y-%m-%d")
    REGISTRATION["business"]["naics"] = {
        "naicsCode": "112320",
        "naicsDescription": "Broiler and other meat-type chicken production",
    }

    gp_registration = copy.deepcopy(FILING_HEADER)
    gp_registration["filing"]["header"]["name"] = "registration"
    gp_registration["filing"]["registration"] = copy.deepcopy(REGISTRATION)
    gp_registration["filing"]["registration"]["startDate"] = now
    gp_registration["filing"]["registration"]["nameRequest"]["legalName"] = legal_name
    gp_registration["filing"]["registration"]["parties"][1]["officer"]["email"] = "party@email.com"

    sp_registration = copy.deepcopy(FILING_HEADER)
    sp_registration["filing"]["header"]["name"] = "registration"
    sp_registration["filing"]["registration"] = copy.deepcopy(REGISTRATION)
    sp_registration["filing"]["registration"]["startDate"] = now
    sp_registration["filing"]["registration"]["nameRequest"]["legalType"] = "SP"
    sp_registration["filing"]["registration"]["nameRequest"]["legalName"] = legal_name
    sp_registration["filing"]["registration"]["businessType"] = "SP"
    sp_registration["filing"]["registration"]["parties"][0]["roles"] = [
        {"roleType": "Completing Party", "appointmentDate": "2022-01-01"},
        {"roleType": "Proprietor", "appointmentDate": "2022-01-01"},
    ]
    del sp_registration["filing"]["registration"]["parties"][1]

    if legal_type == LegalEntity.EntityTypes.SOLE_PROP.value:
        filing_template = sp_registration
    elif legal_type == LegalEntity.EntityTypes.PARTNERSHIP.value:
        filing_template = gp_registration

    legal_entity_id = None
    if option == "PAID":
        del filing_template["filing"]["business"]
    elif option == "COMPLETED":
        legal_entity = create_legal_entity(identifier, legal_type)
        legal_entity.founding_date = datetime.fromisoformat(now)
        legal_entity.save()
        legal_entity_id = legal_entity.id
        filing_template["filing"]["business"] = {
            "identifier": legal_entity.identifier,
            "legalType": legal_entity.legal_type,
            "foundingDate": legal_entity.founding_date.isoformat(),
        }

    filing = create_filing(token=payment_id, filing_json=filing_template, legal_entity_id=legal_entity_id)
    filing.payment_completion_date = filing.filing_date
    filing.save()
    if option in ["COMPLETED"]:
        uow = versioning_manager.unit_of_work(session)
        transaction = uow.create_transaction(session)
        filing.transaction_id = transaction.id
        filing.save()
    return filing


def prep_dissolution_filing(session, identifier, payment_id, option, legal_type, legal_name, submitter_role):
    """Return a new dissolution filing prepped for email notification."""
    legal_entity = create_legal_entity(identifier, legal_type, legal_name)
    filing_template = copy.deepcopy(FILING_HEADER)
    filing_template["filing"]["header"]["name"] = "dissolution"
    if submitter_role:
        filing_template["filing"]["header"]["documentOptionalEmail"] = f"{submitter_role}@email.com"

    filing_template["filing"]["dissolution"] = copy.deepcopy(DISSOLUTION)
    filing_template["filing"]["business"] = {
        "identifier": legal_entity.identifier,
        "legalType": legal_type,
        "legalName": legal_name,
    }

    for party in filing_template["filing"]["dissolution"]["parties"]:
        for role in party["roles"]:
            if role["roleType"] == "Custodian":
                party["officer"]["email"] = "custodian@email.com"
            elif role["roleType"] == "Completing Party":
                party["officer"]["email"] = "cp@email.com"

    filing = create_filing(token=payment_id, filing_json=filing_template, legal_entity_id=legal_entity.id)
    filing.payment_completion_date = filing.filing_date

    user = create_user("test_user")
    filing.submitter_id = user.id
    if submitter_role:
        filing.submitter_roles = submitter_role

    filing.save()
    return filing


def prep_consent_continuation_out_filing(session, identifier, payment_id, legal_type, legal_name, submitter_role):
    """Return a new consent continuation out filing prepped for email notification."""
    legal_entity = create_legal_entity(identifier, legal_type, legal_name)
    filing_template = copy.deepcopy(FILING_HEADER)
    filing_template["filing"]["header"]["name"] = "consentContinuationOut"
    if submitter_role:
        filing_template["filing"]["header"]["documentOptionalEmail"] = f"{submitter_role}@email.com"

    filing_template["filing"]["consentContinuationOut"] = copy.deepcopy(CONSENT_CONTINUATION_OUT)
    filing_template["filing"]["business"] = {
        "identifier": legal_entity.identifier,
        "legalType": legal_type,
        "legalName": legal_name,
    }

    filing = create_filing(token=payment_id, filing_json=filing_template, legal_entity_id=legal_entity.id)
    filing.payment_completion_date = filing.filing_date

    user = create_user("test_user")
    filing.submitter_id = user.id
    if submitter_role:
        filing.submitter_roles = submitter_role

    filing.save()
    return filing


def prep_continuation_out_filing(session, identifier, payment_id, legal_type, legal_name, submitter_role):
    """Return a new continuation out filing prepped for email notification."""
    legal_entity = create_legal_entity(identifier, legal_type, legal_name)
    filing_template = copy.deepcopy(FILING_HEADER)
    filing_template["filing"]["header"]["name"] = "continuationOut"
    if submitter_role:
        filing_template["filing"]["header"]["documentOptionalEmail"] = f"{submitter_role}@email.com"

    filing_template["filing"]["continuationOut"] = copy.deepcopy(CONTINUATION_OUT)
    filing_template["filing"]["business"] = {
        "identifier": legal_entity.identifier,
        "legalType": legal_type,
        "legalName": legal_name,
    }

    filing = create_filing(token=payment_id, filing_json=filing_template, legal_entity_id=legal_entity.id)
    filing.payment_completion_date = filing.filing_date

    user = create_user("test_user")
    filing.submitter_id = user.id
    if submitter_role:
        filing.submitter_roles = submitter_role

    filing.save()
    return filing


def prep_restoration_filing(identifier, payment_id, legal_type, legal_name, r_type="fullRestoration"):
    """Return a new restoration filing prepped for email notification.

    @param r_type:
    @param identifier:
    @param payment_id:
    @param legal_type:
    @param legal_name:
    @return:
    """
    legal_entity = create_legal_entity(identifier, legal_type, legal_name)
    filing_template = copy.deepcopy(FILING_HEADER)
    filing_template["filing"]["header"]["name"] = "restoration"
    filing_template["filing"]["restoration"] = copy.deepcopy(RESTORATION)
    filing_template["filing"]["restoration"]["type"] = r_type
    filing_template["filing"]["business"] = {
        "identifier": legal_entity.identifier,
        "legalType": legal_type,
        "legalName": legal_name,
    }

    filing = create_filing(token=payment_id, filing_json=filing_template, legal_entity_id=legal_entity.id)
    filing.payment_completion_date = filing.filing_date

    user = create_user("test_user")
    filing.submitter_id = user.id

    filing.save()
    return filing


def prep_change_of_registration_filing(session, identifier, payment_id, legal_type, legal_name, submitter_role):
    """Return a new change of registration filing prepped for email notification."""
    legal_entity = create_legal_entity(identifier, legal_type, legal_name)

    gp_change_of_registration = copy.deepcopy(FILING_HEADER)
    gp_change_of_registration["filing"]["header"]["name"] = "changeOfRegistration"
    gp_change_of_registration["filing"]["changeOfRegistration"] = copy.deepcopy(CHANGE_OF_REGISTRATION)
    gp_change_of_registration["filing"]["changeOfRegistration"]["parties"][0]["officer"]["email"] = "party@email.com"

    sp_change_of_registration = copy.deepcopy(FILING_HEADER)
    sp_change_of_registration["filing"]["header"]["name"] = "changeOfRegistration"
    sp_change_of_registration["filing"]["changeOfRegistration"] = copy.deepcopy(CHANGE_OF_REGISTRATION)
    sp_change_of_registration["filing"]["changeOfRegistration"]["parties"][0]["roles"] = [
        {"roleType": "Completing Party", "appointmentDate": "2022-01-01"},
        {"roleType": "Proprietor", "appointmentDate": "2022-01-01"},
    ]
    sp_change_of_registration["filing"]["changeOfRegistration"]["parties"][0]["officer"]["email"] = "party@email.com"

    if legal_type == LegalEntity.EntityTypes.SOLE_PROP.value:
        filing_template = sp_change_of_registration
    elif legal_type == LegalEntity.EntityTypes.PARTNERSHIP.value:
        filing_template = gp_change_of_registration

    filing_template["filing"]["business"] = {
        "identifier": legal_entity.identifier,
        "legalType": legal_type,
        "legalName": legal_name,
    }
    if submitter_role:
        filing_template["filing"]["header"]["documentOptionalEmail"] = f"{submitter_role}@email.com"

    filing = create_filing(token=payment_id, filing_json=filing_template, legal_entity_id=legal_entity.id)
    filing.payment_completion_date = filing.filing_date

    user = create_user("test_user")
    filing.submitter_id = user.id
    if submitter_role:
        filing.submitter_roles = submitter_role

    filing.save()
    return filing


def prep_alteration_filing(session, identifier, option, company_name):
    """Return an alteration filing prepped for email notification."""
    legal_entity = create_legal_entity(
        identifier, legal_type=LegalEntity.EntityTypes.BCOMP.value, legal_name=company_name
    )
    filing_template = copy.deepcopy(ALTERATION_FILING_TEMPLATE)
    filing_template["filing"]["business"] = {
        "identifier": f"{identifier}",
        "legalype": LegalEntity.EntityTypes.BCOMP.value,
        "legalName": company_name,
    }
    filing = create_filing(filing_json=filing_template, legal_entity_id=legal_entity.id)
    filing.save()

    return filing


def prep_agm_location_change_filing(identifier, payment_id, legal_type, legal_name):
    """Return a new AGM location change filing prepped for email notification."""
    business = create_legal_entity(identifier, legal_type, legal_name)
    filing_template = copy.deepcopy(FILING_HEADER)
    filing_template["filing"]["header"]["name"] = "agmLocationChange"

    filing_template["filing"]["agmLocationChange"] = copy.deepcopy(AGM_LOCATION_CHANGE)
    filing_template["filing"]["business"] = {
        "identifier": business.identifier,
        "legalType": legal_type,
        "legalName": legal_name,
    }

    filing = create_filing(token=payment_id, filing_json=filing_template, legal_entity_id=business.id)
    filing.payment_completion_date = filing.filing_date

    user = create_user("test_user")
    filing.submitter_id = user.id

    filing.save()
    return filing


def prep_agm_extension_filing(identifier, payment_id, legal_type, legal_name):
    """Return a new AGM extension filing prepped for email notification."""
    business = create_legal_entity(identifier, legal_type, legal_name)
    filing_template = copy.deepcopy(FILING_HEADER)
    filing_template["filing"]["header"]["name"] = "agmExtension"

    filing_template["filing"]["agmExtension"] = copy.deepcopy(AGM_EXTENSION)
    filing_template["filing"]["business"] = {
        "identifier": business.identifier,
        "legalType": legal_type,
        "legalName": legal_name,
    }

    filing = create_filing(token=payment_id, filing_json=filing_template, legal_entity_id=business.id)
    filing.payment_completion_date = filing.filing_date

    user = create_user("test_user")
    filing.submitter_id = user.id

    filing.save()
    return filing


def prep_maintenance_filing(session, identifier, payment_id, status, filing_type, submitter_role=None):
    """Return a new maintenance filing prepped for email notification."""
    legal_entity = create_legal_entity(identifier, LegalEntity.EntityTypes.BCOMP.value, LEGAL_NAME)
    filing_template = copy.deepcopy(FILING_TEMPLATE)
    filing_template["filing"]["header"]["name"] = filing_type
    filing_template["filing"]["business"] = {
        "identifier": f"{identifier}",
        "legalype": LegalEntity.EntityTypes.BCOMP.value,
        "legalName": LEGAL_NAME,
    }
    filing_template["filing"][filing_type] = copy.deepcopy(FILING_TYPE_MAPPER[filing_type])

    if submitter_role:
        filing_template["filing"]["header"]["documentOptionalEmail"] = f"{submitter_role}@email.com"
    filing = create_filing(token=payment_id, filing_json=filing_template, legal_entity_id=legal_entity.id)

    user = create_user("test_user")
    filing.submitter_id = user.id
    if submitter_role:
        filing.submitter_roles = submitter_role

    filing.save()
    if status == "COMPLETED":
        uow = versioning_manager.unit_of_work(session)
        transaction = uow.create_transaction(session)
        filing.transaction_id = transaction.id
        filing.save()

    return filing


def prep_incorporation_correction_filing(session, legal_entity, original_filing_id, payment_id, option):
    """Return a new incorporation correction filing prepped for email notification."""
    filing_template = copy.deepcopy(CORRECTION_INCORPORATION)
    filing_template["filing"]["business"] = {"identifier": legal_entity.identifier}
    for party in filing_template["filing"]["correction"]["parties"]:
        for role in party["roles"]:
            if role["roleType"] == "Completing Party":
                party["officer"]["email"] = "comp_party@email.com"
    filing_template["filing"]["correction"]["contactPoint"]["email"] = "test@test.com"
    filing_template["filing"]["correction"]["correctedFilingId"] = original_filing_id
    filing = create_filing(token=payment_id, filing_json=filing_template, legal_entity_id=legal_entity.id)
    filing.payment_completion_date = filing.filing_date
    filing.save()
    if option in ["COMPLETED"]:
        uow = versioning_manager.unit_of_work(session)
        transaction = uow.create_transaction(session)
        filing.transaction_id = transaction.id
        filing.save()
    return filing


def prep_firm_correction_filing(session, identifier, payment_id, legal_type, legal_name, submitter_role):
    """Return a firm correction filing prepped for email notification."""
    legal_entity = create_legal_entity(identifier, legal_type, legal_name)

    gp_correction = copy.deepcopy(CORRECTION_REGISTRATION)
    gp_correction["filing"]["correction"]["parties"][0]["officer"]["email"] = "party@email.com"

    sp_correction = copy.deepcopy(CORRECTION_REGISTRATION)
    sp_correction["filing"]["correction"]["parties"][0]["officer"]["email"] = "party@email.com"
    sp_correction["filing"]["correction"]["parties"][0]["roles"] = [
        {"roleType": "Completing Party", "appointmentDate": "2022-01-01"},
        {"roleType": "Proprietor", "appointmentDate": "2022-01-01"},
    ]
    sp_correction["filing"]["correction"]["parties"][0]["officer"]["email"] = "party@email.com"

    if legal_type == LegalEntity.EntityTypes.SOLE_PROP.value:
        filing_template = sp_correction
    elif legal_type == LegalEntity.EntityTypes.PARTNERSHIP.value:
        filing_template = gp_correction

    filing_template["filing"]["business"] = {
        "identifier": legal_entity.identifier,
        "legalType": legal_type,
        "legalName": legal_name,
    }

    filing = create_filing(token=payment_id, filing_json=filing_template, legal_entity_id=legal_entity.id)
    filing.payment_completion_date = filing.filing_date

    user = create_user("test_user")
    filing.submitter_id = user.id
    if submitter_role:
        filing.submitter_roles = submitter_role

    filing.save()
    return filing


def prep_cp_special_resolution_filing(identifier, payment_id, legal_type, legal_name, submitter_role=None):
    """Return a new cp special resolution out filing prepped for email notification."""
    legal_entity = create_legal_entity(identifier, legal_type=legal_type, legal_name=legal_name)
    filing_template = copy.deepcopy(CP_SPECIAL_RESOLUTION_TEMPLATE)
    filing_template["filing"]["business"] = {
        "identifier": f"{identifier}",
        "legalype": legal_type,
        "legalName": legal_name,
    }
    filing_template["filing"]["alteration"] = {
        "business": {"identifier": "BC1234567", "legalType": "BEN"},
        "contactPoint": {"email": "joe@email.com"},
        "rulesInResolution": True,
        "rulesFileKey": "cooperative/a8abe1a6-4f45-4105-8a05-822baee3b743.pdf",
    }
    if submitter_role:
        filing_template["filing"]["header"]["documentOptionalEmail"] = f"{submitter_role}@email.com"
    filing = create_filing(token=payment_id, filing_json=filing_template, legal_entity_id=legal_entity.id)

    user = create_user("cp_test_user")
    filing.submitter_id = user.id
    if submitter_role:
        filing.submitter_roles = submitter_role
    filing.save()
    return filing


def prep_cp_special_resolution_correction_filing(
    session, legal_entity, original_filing_id, payment_id, option, corrected_filing_type
):
    """Return a cp special resolution correction filing prepped for email notification."""
    filing_template = copy.deepcopy(FILING_HEADER)
    filing_template["filing"]["header"]["name"] = "correction"
    filing_template["filing"]["correction"] = copy.deepcopy(CORRECTION_CP_SPECIAL_RESOLUTION)
    filing_template["filing"]["business"] = {"identifier": legal_entity.identifier}
    filing_template["filing"]["correction"]["contactPoint"]["email"] = "cp_sr@test.com"
    filing_template["filing"]["correction"]["correctedFilingId"] = original_filing_id
    filing_template["filing"]["correction"]["correctedFilingType"] = corrected_filing_type
    filing_template["filing"]["correction"]["nameRequest"] = {
        "nrNumber": "NR 8798956",
        "legalName": "HAULER MEDIA INC.",
        "legalType": "BC",
        "requestType": "CHG",
    }
    filing = create_filing(token=payment_id, filing_json=filing_template, legal_entity_id=legal_entity.id)
    filing.payment_completion_date = filing.filing_date
    # Triggered from the filer.
    filing._meta_data = {"correction": {"uploadNewRules": True, "toLegalName": True}}
    filing.save()
    if option in ["COMPLETED"]:
        uow = versioning_manager.unit_of_work(session)
        transaction = uow.create_transaction(session)
        filing.transaction_id = transaction.id
        filing.save()
    return filing


def prep_cp_special_resolution_correction_upload_memorandum_filing(
    session, business, original_filing_id, payment_id, option, corrected_filing_type
):
    """Return a cp special resolution correction filing prepped for email notification."""
    filing_template = copy.deepcopy(FILING_HEADER)
    filing_template["filing"]["header"]["name"] = "correction"
    filing_template["filing"]["correction"] = copy.deepcopy(CORRECTION_CP_SPECIAL_RESOLUTION)
    filing_template["filing"]["business"] = {"identifier": business.identifier}
    filing_template["filing"]["correction"]["contactPoint"]["email"] = "cp_sr@test.com"
    filing_template["filing"]["correction"]["correctedFilingId"] = original_filing_id
    filing_template["filing"]["correction"]["correctedFilingType"] = corrected_filing_type
    del filing_template["filing"]["correction"]["resolution"]
    filing_template["filing"]["correction"]["memorandumFileKey"] = "28f73dc4-8e7c-4c89-bef6-a81dff909ca6.pdf"
    filing_template["filing"]["correction"]["memorandumFileName"] = "test.pdf"
    filing = create_filing(token=payment_id, filing_json=filing_template, legal_entity_id=business.id)
    filing.payment_completion_date = filing.filing_date
    # Triggered from the filer.
    filing._meta_data = {"correction": {"uploadNewMemorandum": True}}
    filing.save()
    if option in ["COMPLETED"]:
        uow = versioning_manager.unit_of_work(session)
        transaction = uow.create_transaction(session)
        filing.transaction_id = transaction.id
        filing.save()
    return filing


def prep_amalgamation_filing(session, identifier, payment_id, option, legal_name):
    """Return a new incorp filing prepped for email notification."""
    business = create_legal_entity(identifier, legal_type=LegalEntity.EntityTypes.BCOMP.value, legal_name=legal_name)
    filing_template = copy.deepcopy(FILING_HEADER)
    filing_template["filing"]["header"]["name"] = "amalgamationApplication"

    filing_template["filing"]["amalgamationApplication"] = copy.deepcopy(AMALGAMATION_APPLICATION)
    filing_template["filing"]["amalgamationApplication"]["nameRequest"] = {
        "identifier": business.identifier,
        "legalType": LegalEntity.EntityTypes.BCOMP.value,
        "legalName": legal_name,
    }
    filing_template["filing"]["business"] = {"identifier": business.identifier}
    for party in filing_template["filing"]["amalgamationApplication"]["parties"]:
        for role in party["roles"]:
            if role["roleType"] == "Completing Party":
                party["officer"]["email"] = "comp_party@email.com"
    filing_template["filing"]["amalgamationApplication"]["contactPoint"]["email"] = "test@test.com"

    temp_identifier = "Tb31yQIuBw"
    temp_reg = RegistrationBootstrap()
    temp_reg._identifier = temp_identifier
    temp_reg.save()
    filing = create_filing(
        token=payment_id, filing_json=filing_template, business_id=business.id, bootstrap_id=temp_identifier
    )
    filing.payment_completion_date = filing.filing_date
    filing.save()
    if option == Filing.Status.COMPLETED.value:
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


@contextmanager
def nested_session(session):
    try:
        sess = session.begin_nested()
        yield sess
        sess.rollback()
    except:  # noqa: E722
        pass
    finally:
        pass
