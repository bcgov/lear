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
"""The Test Suite to ensure that the worker is operating correctly for change of liquidators."""
import copy
import datetime
from datetime import datetime, timezone
import random

from business_model.models import Address, Business, Filing, Office, OfficeType, PartyRole, Party
from registry_schemas.example_data import FILING_TEMPLATE

from business_filer.common.filing_message import FilingMessage
from business_filer.services.filer import process_filing
from tests.unit import create_business, create_filing
from tests.unit.filing_processors.filing_components.test_offices import LIQUIDATION_RECORDS_OFFICE
from tests.unit.test_filer import check_drs_publish

CHANGE_OF_LIQUIDATORS_INTENT = {
    'type': 'intentToLiquidate',
    'relationships': [
        {
            'entity': {
                'givenName': 'Phillip Tandy',
                'familyName': 'Miller',
                'alternateName': 'Phil Miller'
            },
            'deliveryAddress': {
                'streetAddress': 'delivery_address - address line one',
                'addressCity': 'delivery_address city',
                'addressCountry': 'CA',
                'postalCode': 'H0H0H0',
                'addressRegion': 'BC'
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
                    'appointmentDate': '2018-01-01',
                    'roleType': 'Liquidator'
                }
            ]
        },
        {
            'entity': {
                'businessName': 'Test Business',
            },
            'deliveryAddress': {
                'streetAddress': 'delivery_address - address line one',
                'addressCity': 'delivery_address city',
                'addressCountry': 'CA',
                'postalCode': 'H0H0H0',
                'addressRegion': 'BC'
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
                    'roleType': 'Liquidator'
                }
            ]
        }
    ],
    'offices': {
        **LIQUIDATION_RECORDS_OFFICE
    }
}

def _assert_party_roles_addresses(party_roles, party_id, expected_delivery, expected_mailing):
        assert len(party_roles) == 2

        for role in party_roles:
            if role.party_id == party_id:
                delivery = role.party.delivery_address
                mailing = role.party.mailing_address
                
                assert delivery.address_type == 'delivery'
                assert delivery.street == expected_delivery['streetAddress']
                
                assert mailing.address_type == 'mailing'
                assert mailing.street == expected_mailing['streetAddress']
                return
    
def _assert_office_addresses(offices, expected_office):
    # Should have registered office and liquidations office
    assert len(offices) == 2

    has_liquidation_office = False
    for office in offices:
        if office.office_type == OfficeType.LIQUIDATION:
            has_liquidation_office = True
            officeAddresses: list[Address] = office.addresses.all()
            assert len(officeAddresses) == 2
            expected_delivery_street = expected_office['deliveryAddress']['streetAddress']
            expected_mailing_street = expected_office['mailingAddress']['streetAddress']
            for address in officeAddresses:
                if address.address_type == Address.DELIVERY:
                    assert address.street == expected_delivery_street
                else:
                    assert address.address_type == Address.MAILING
                    assert address.street == expected_mailing_street
    assert has_liquidation_office

def _assert_common_data(business: Business, filing: Filing, expected_date, expected_lr_year, expected_next_lr_yr):
    """Assert the expected common data was updated by the liquidation filing processing."""
    assert filing.transaction_id
    assert filing.business_id == business.id
    assert filing.status == Filing.Status.COMPLETED.value
    assert business.in_liquidation == True
    assert business.in_liquidation_date == expected_date
    assert business.last_lr_year == expected_lr_year
    assert business.next_lr_min_date.year == expected_next_lr_yr

def _get_liquidation_filing(sub_type: str, effective_date: datetime, identifier = 'BC1234567'):
    """Return a valid change of liquidators filing for the sub type."""
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing = copy.deepcopy(FILING_TEMPLATE)
    filing['filing']['header']['name'] = 'changeOfLiquidators'
    filing['filing']['header']['effectiveDate'] = effective_date.isoformat()
    filing['filing']['business']['identifier'] = identifier
    filing['filing']['business']['legalType'] = 'BC'
    filing['filing']['changeOfLiquidators'] = copy.deepcopy(CHANGE_OF_LIQUIDATORS_INTENT)
    return filing, payment_id, identifier
    

def test_process_col_filing(app, session, mocker):
    """Assert that all COL filings can be applied to the model correctly."""
    # NOTE: this is actually in 2023 pacific time
    expected_in_liquidation_date = datetime(2024, 1, 1, 1, 0, 0, tzinfo=timezone.utc)
    drs_publish_mock = mocker.patch('business_filer.services.gcp_queue.publish', return_value=None)
    filing, payment_id, identifier = _get_liquidation_filing('intentToLiquidate', expected_in_liquidation_date)
    business = create_business(identifier)

    filing_rec = create_filing(payment_id, filing, business.id)
    filing_rec.effective_date = expected_in_liquidation_date
    filing_rec.save()

    # setup
    filing_msg = FilingMessage(filing_identifier=filing_rec.id)

    # TEST
    process_filing(filing_msg)

    # Get modified data
    intent_filing: Filing = Filing.find_by_id(filing_rec.id)
    business: Business = Business.find_by_internal_id(business.id)

    # assert changes
    _assert_common_data(business, intent_filing, expected_in_liquidation_date, None, 2024)
    check_drs_publish(drs_publish_mock, app, business, intent_filing, '')
    drs_publish_mock.reset_mock()

    party_roles: list[PartyRole] = business.party_roles.all()
    assert len(party_roles) == 2
    for role in party_roles:
        assert role.appointment_date
        assert not role.cessation_date
        assert role.role == PartyRole.RoleTypes.LIQUIDATOR.value
    
    offices: list[Office] = business.offices.all()
    _assert_office_addresses(offices, filing['filing']['changeOfLiquidators']['offices']['liquidationRecordsOffice'])

    # Test cease liquidator

    party_id_1 = party_roles[0].party_id
    party_id_2 = party_roles[1].party_id
    filing['filing']['changeOfLiquidators'] = {
        'type': 'ceaseLiquidator',
        'relationships': [
            {
                'entity': {
                    'identifier': party_id_1
                },
                'roles': [
                    {
                        'roleType': 'Liquidator',
                        # NOTE: will be overriden by filing effective date
                        'cessationDate': '2025-03-04'
                    }
                ]
            }
        ]
    }
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    effective_date = datetime(2025, 10, 10, 10, 0, 0, tzinfo=timezone.utc)

    filing_rec = create_filing(payment_id, filing, business.id)
    filing_rec.effective_date = effective_date
    filing_rec.save()
    filing_msg = FilingMessage(filing_identifier=filing_rec.id)

    # TEST
    process_filing(filing_msg)

    # Get modified data
    cease_filing: Filing = Filing.find_by_id(filing_rec.id)
    business: Business = Business.find_by_internal_id(business.id)

    # assert changes
    _assert_common_data(business, cease_filing, expected_in_liquidation_date, None, 2024)
    check_drs_publish(drs_publish_mock, app, business, cease_filing, '')
    drs_publish_mock.reset_mock()

    party_roles: list[PartyRole] = business.party_roles.all()
    assert len(party_roles) == 2

    for role in party_roles:
        if role.party_id == party_id_1:
            assert role.cessation_date == cease_filing.effective_date
        else:
            assert role.party_id == party_id_2
            assert role.cessation_date is None

    # Test change address liquidators - relationships and offices submitted
    base_address = {
        'streetAddressAdditional': '',
        'addressCity': 'Vancouver',
        'addressRegion': 'BC',
        'addressCountry': 'CA',
        'postalCode': 'V0N4Y8',
        'deliveryInstructions': ''
    }

    new_address_delivery = {**base_address, 'streetAddress': 'Changed Delivery'}
    new_address_mailing  = {**base_address, 'streetAddress': 'Changed Mailing'}
    new_office = {
        'deliveryAddress': {**base_address, 'streetAddress': 'Changed Office Delivery'},
        'mailingAddress':  {**base_address, 'streetAddress': 'Changed Office Mailing'}
    }
    filing['filing']['changeOfLiquidators'] = {
        'type': 'changeAddressLiquidator',
        'relationships': [
            {
                'entity': {
                    'identifier': party_id_2
                },
                'deliveryAddress': new_address_delivery,
                'mailingAddress': new_address_mailing
            }
        ],
        'offices': {
            'liquidationRecordsOffice': new_office
        }
    }
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    effective_date = datetime(2025, 10, 10, 10, 0, 0, tzinfo=timezone.utc)
    filing_rec = create_filing(payment_id, filing, business.id)
    filing_rec.effective_date = effective_date
    filing_rec.save()
    
    # setup
    filing_msg = FilingMessage(filing_identifier=filing_rec.id)

    # TEST
    process_filing(filing_msg)

    # Get modified data
    change_address_filing: Filing = Filing.find_by_id(filing_rec.id)
    business: Business = Business.find_by_internal_id(business.id)

    # assert changes
    _assert_common_data(business, change_address_filing, expected_in_liquidation_date, None, 2024)
    check_drs_publish(drs_publish_mock, app, business, change_address_filing, '')
    drs_publish_mock.reset_mock()

    party_roles: list[PartyRole] = business.party_roles.all()
    _assert_party_roles_addresses(party_roles, party_id_2, new_address_delivery, new_address_mailing)
    
    offices: list[Office] = business.offices.all()
    _assert_office_addresses(offices, new_office)
    
    # Test change address liquidators - no offices submitted

    new_address_delivery_no_offices = {**base_address, 'streetAddress': 'Changed Delivery No Offices'}
    new_address_mailing_no_offices  = {**base_address, 'streetAddress': 'Changed Mailing No Offices'}
    
    filing['filing']['changeOfLiquidators'] = {
        'type': 'changeAddressLiquidator',
        'relationships': [
            {
                'entity': {
                    'identifier': party_id_2
                },
                'deliveryAddress': new_address_delivery_no_offices,
                'mailingAddress': new_address_mailing_no_offices
            }
        ],
        # No offices in payload
        # 'offices': {}
    }
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    effective_date = datetime(2025, 10, 10, 10, 0, 0, tzinfo=timezone.utc)
    filing_rec = create_filing(payment_id, filing, business.id)
    filing_rec.effective_date = effective_date
    filing_rec.save()
    
    # setup
    filing_msg = FilingMessage(filing_identifier=filing_rec.id)

    # TEST
    process_filing(filing_msg)

    # Get modified data
    change_address_filing: Filing = Filing.find_by_id(filing_rec.id)
    business: Business = Business.find_by_internal_id(business.id)

    # assert changes
    _assert_common_data(business, change_address_filing, expected_in_liquidation_date, None, 2024)
    check_drs_publish(drs_publish_mock, app, business, change_address_filing, '')
    drs_publish_mock.reset_mock()

    party_roles: list[PartyRole] = business.party_roles.all()
    _assert_party_roles_addresses(party_roles, party_id_2, new_address_delivery_no_offices, new_address_mailing_no_offices)
    
    offices: list[Office] = business.offices.all()
    # Will still have offices from the previous changeAddressLiquidator filing
    _assert_office_addresses(offices, new_office)

    # Test change address liquidators - no relationships submitted

    new_office_no_rels = {
        'deliveryAddress': {**base_address, 'streetAddress': 'Changed Delivery No Relationships'},
        'mailingAddress': {**base_address, 'streetAddress': 'Changed Mailing No Relationships'}
    }

    filing['filing']['changeOfLiquidators'] = {
        'type': 'changeAddressLiquidator',
        'offices': {
            'liquidationRecordsOffice': new_office_no_rels
        },
        # No relationships in payload
        # 'relationships': []
    }
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    effective_date = datetime(2025, 10, 10, 10, 0, 0, tzinfo=timezone.utc)
    filing_rec = create_filing(payment_id, filing, business.id)
    filing_rec.effective_date = effective_date
    filing_rec.save()
    
    # setup
    filing_msg = FilingMessage(filing_identifier=filing_rec.id)

    # TEST
    process_filing(filing_msg)

    # Get modified data
    change_address_filing: Filing = Filing.find_by_id(filing_rec.id)
    business: Business = Business.find_by_internal_id(business.id)

    # assert changes
    _assert_common_data(business, change_address_filing, expected_in_liquidation_date, None, 2024)
    check_drs_publish(drs_publish_mock, app, business, change_address_filing, '')
    drs_publish_mock.reset_mock()

    # Will still have party address values from the previous changeAddressLiquidator filing
    party_roles: list[PartyRole] = business.party_roles.all()
    _assert_party_roles_addresses(party_roles, party_id_2, new_address_delivery_no_offices, new_address_mailing_no_offices)
    
    offices: list[Office] = business.offices.all()
    _assert_office_addresses(offices, new_office_no_rels)

    # Test appoint liquidators
    new_relationship = {
        'entity': {
            'givenName': 'New Guy',
            'familyName': 'Test'
        },
        'deliveryAddress': {
            'streetAddress': 'delivery_address - address line one',
            'addressCity': 'delivery_address city',
            'addressCountry': 'CA',
            'postalCode': 'H0H0H0',
            'addressRegion': 'BC'
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
                'roleType': 'Liquidator'
            }
        ]
    }
    new_document_id = '12345677'
    filing['filing']['changeOfLiquidators'] = {
        'type': 'appointLiquidator',
        'documentId': new_document_id,
        'relationships': [
            new_relationship
        ]
    }
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    effective_date = datetime(2025, 10, 10, 10, 0, 0, tzinfo=timezone.utc)
    filing_rec = create_filing(payment_id, filing, business.id)
    filing_rec.effective_date = effective_date
    filing_rec.save()
    
    # setup
    filing_msg = FilingMessage(filing_identifier=filing_rec.id)

    # TEST
    process_filing(filing_msg)

    # Get modified data
    appoint_filing: Filing = Filing.find_by_id(filing_rec.id)
    business: Business = Business.find_by_internal_id(business.id)

    # assert changes
    _assert_common_data(business, appoint_filing, expected_in_liquidation_date, None, 2024)
    check_drs_publish(drs_publish_mock, app, business, appoint_filing, new_document_id)
    drs_publish_mock.reset_mock()

    party_roles: list[PartyRole] = business.party_roles.all()

    assert len(party_roles) == 3

    for role in party_roles:
        party: Party = role.party
        delivery_address: Address = role.party.delivery_address
        mailing_address: Address = role.party.mailing_address

        if role.party_id not in [party_id_1, party_id_2]:
            # new relationship
            assert party.first_name == new_relationship['entity']['givenName'].upper()
            assert party.last_name == new_relationship['entity']['familyName'].upper()
            assert delivery_address.address_type == 'delivery'
            assert delivery_address.street == new_relationship['deliveryAddress']['streetAddress']
            assert mailing_address.address_type == 'mailing'
            assert mailing_address.street == new_relationship['mailingAddress']['streetAddress']
    
    # liquidation report
    expected_last_lr_year = 2024

    filing['filing']['changeOfLiquidators'] = {
        'type': 'liquidationReport',
    }
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    effective_date = datetime(2025, 11, 10, 10, 0, 0, tzinfo=timezone.utc)

    filing_rec = create_filing(payment_id, filing, business.id)
    filing_rec.effective_date = effective_date
    filing_rec.save()
    filing_msg = FilingMessage(filing_identifier=filing_rec.id)

    # TEST
    process_filing(filing_msg)
    
    # Get modified data
    lr_filing_1: Filing = Filing.find_by_id(filing_rec.id)
    business: Business = Business.find_by_internal_id(business.id)

    # assert changes
    _assert_common_data(business, lr_filing_1, expected_in_liquidation_date, expected_last_lr_year, 2025)
    check_drs_publish(drs_publish_mock, app, business, lr_filing_1, '')
    drs_publish_mock.reset_mock()
    
    # 2nd liquidation report
    second_expected_last_lr_year = expected_last_lr_year + 1
    filing['filing']['changeOfLiquidators'] = {
        'type': 'liquidationReport',
    }
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    effective_date = datetime(2025, 11, 10, 10, 0, 0, tzinfo=timezone.utc)

    filing_rec = create_filing(payment_id, filing, business.id)
    filing_rec.effective_date = effective_date
    filing_rec.save()
    filing_msg = FilingMessage(filing_identifier=filing_rec.id)

    # TEST
    process_filing(filing_msg)
    
    # Get modified data
    lr_filing_2: Filing = Filing.find_by_id(filing_rec.id)
    business: Business = Business.find_by_internal_id(business.id)

    # assert changes
    _assert_common_data(business, lr_filing_2, expected_in_liquidation_date, second_expected_last_lr_year, 2026)
    check_drs_publish(drs_publish_mock, app, business, lr_filing_2, '')
    drs_publish_mock.reset_mock()


def test_process_col_filing_initiated_with_appoint(app, session, mocker):
    """Assert that appointLiquidator filings can put the business into liquidation and can include liquidation office."""
    expected_in_liquidation_date = datetime(2023, 10, 10, 10, 0, 0, tzinfo=timezone.utc)
    filing, payment_id, identifier = _get_liquidation_filing('appointLiquidator', expected_in_liquidation_date)
    drs_publish_mock = mocker.patch('business_filer.services.gcp_queue.publish', return_value=None)

    business = create_business(identifier)

    filing_rec = create_filing(payment_id, filing, business.id)
    filing_rec.effective_date = expected_in_liquidation_date
    filing_rec.save()

    # setup
    filing_msg = FilingMessage(filing_identifier=filing_rec.id)

    # TEST
    process_filing(filing_msg)

    # Get modified data
    appoint_filing: Filing = Filing.find_by_id(filing_rec.id)
    business: Business = Business.find_by_internal_id(business.id)

    # assert changes
    _assert_common_data(business, appoint_filing, expected_in_liquidation_date, None, 2024)
    check_drs_publish(drs_publish_mock, app, business, appoint_filing, '')
    drs_publish_mock.reset_mock()

    party_roles: list[PartyRole] = business.party_roles.all()
    assert len(party_roles) == 2
    for role in party_roles:
        assert role.appointment_date
        assert not role.cessation_date
        assert role.role == PartyRole.RoleTypes.LIQUIDATOR.value
    
    offices: list[Office] = business.offices.all()
    # NOTE: will have a registered office too
    assert len(offices) == 2
    _assert_office_addresses(offices, filing['filing']['changeOfLiquidators']['offices']['liquidationRecordsOffice'])
