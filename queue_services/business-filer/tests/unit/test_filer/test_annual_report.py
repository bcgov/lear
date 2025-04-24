# Copyright © 2025 Province of British Columbia
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
from business_model.models import Business, Filing, PartyRole, User
# from legal_api.resources.v1.business import DirectorResource
from registry_schemas.example_data import (
    ANNUAL_REPORT,
    CHANGE_OF_ADDRESS,
    CONTINUATION_IN_FILING_TEMPLATE,
    CORRECTION_AR,
    FILING_HEADER,
    INCORPORATION_FILING_TEMPLATE,
)

from business_filer.exceptions import QueueException
from business_filer.filing_processors.filing_components import business_info, business_profile, create_party, create_role
from business_filer.services.filer import process_filing
from tests.unit import (
    COMBINED_FILING,
    create_business,
    create_filing,
    create_user,
)
from business_filer.common.filing_message import FilingMessage


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
    # assert DirectorResource._get_director(business, director_ceased_id)[0]['director']['cessationDate'] is not None


def test_process_combined_filing(app, session, mocker):
    """Assert that an AR filling can be applied to the model correctly."""
    # mock out the email sender and event publishing
    mocker.patch('business_filer.services.publish_event.PublishEvent.publish_email_message', return_value=None)
    mocker.patch('business_filer.services.publish_event.PublishEvent.publish_event', return_value=None)

    # vars
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    identifier = 'CP1234567'
    business = create_business(identifier, legal_type='CP')
    agm_date = datetime.date.fromisoformat(COMBINED_FILING['filing']['annualReport'].get('annualGeneralMeetingDate'))
    ar_date = datetime.date.fromisoformat(COMBINED_FILING['filing']['annualReport'].get('annualReportDate'))
    new_delivery_address = COMBINED_FILING['filing']['changeOfAddress']['offices']['registeredOffice']['deliveryAddress']  # noqa: E501; line too long by 1 char
    new_mailing_address = COMBINED_FILING['filing']['changeOfAddress']['offices']['registeredOffice']['mailingAddress']
    end_date = datetime.datetime.now(datetime.timezone.utc).date()
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
    filing_msg = FilingMessage(filing_identifier=filing_id)

    # TEST
    process_filing(filing_msg)

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


def test_process_filing_completed(app, session, mocker):
    """Assert that an AR filling status is set to completed once processed."""
    # vars
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    identifier = 'CP1234567'

    # mock out the email sender and event publishing
    mocker.patch('business_filer.services.publish_event.PublishEvent.publish_email_message', return_value=None)
    mocker.patch('business_filer.services.publish_event.PublishEvent.publish_event', return_value=None)

    # setup
    business = create_business(identifier, legal_type='CP')
    business_id = business.id
    filing_id = (create_filing(payment_id, ANNUAL_REPORT, business.id)).id
    filing_msg = FilingMessage(filing_identifier=filing_id)

    # TEST
    process_filing(filing_msg)

    # Get modified data
    filing = Filing.find_by_id(filing_id)
    business = Business.find_by_internal_id(business_id)

    # check it out
    assert filing.business_id == business_id
    assert filing.status == Filing.Status.COMPLETED.value
    assert filing.transaction_id
    assert business.last_agm_date
    assert business.last_ar_date
