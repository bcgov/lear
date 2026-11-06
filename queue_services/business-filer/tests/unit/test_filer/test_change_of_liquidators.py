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
from datetime import datetime, timezone, UTC
from freezegun import freeze_time
import random
import pytest

from business_model.models import Address, BatchProcessing, Business, Filing, Office, OfficeType, PartyRole, Party
from business_model.utils.legislation_datetime import LegislationDatetime
from registry_schemas.example_data import FILING_TEMPLATE

from business_filer.common.filing_message import FilingMessage
from business_filer.services.filer import process_filing
from business_filer.filing_meta import FilingMeta
from tests.unit import create_business, create_filing, factory_batch, factory_batch_processing
from tests.unit.filing_processors.filing_components.test_offices import LIQUIDATION_RECORDS_OFFICE
from business_filer.filing_processors.change_of_liquidators import _init_liquidation
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

def _get_liquidation_filing(sub_type: str, effective_date: datetime, col_date: str | None = None, identifier = 'BC1234567'):
    """Return a valid change of liquidators filing for the sub type."""
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing = copy.deepcopy(FILING_TEMPLATE)
    filing['filing']['header']['name'] = 'changeOfLiquidators'
    filing['filing']['header']['effectiveDate'] = effective_date.isoformat()
    filing['filing']['business']['identifier'] = identifier
    filing['filing']['business']['legalType'] = 'BC'

    col_payload = copy.deepcopy(CHANGE_OF_LIQUIDATORS_INTENT)
    col_payload['type'] = sub_type
    if col_date:
        col_payload['changeOfLiquidatorsDate'] = col_date
    else:
        col_payload.pop('changeOfLiquidatorsDate', None)

    filing['filing']['changeOfLiquidators'] = col_payload
    return filing, payment_id, identifier
    

def test_process_col_filing(app, session, mocker):
    """Assert that all COL filings can be applied to the model correctly."""
    effective_date = datetime(2024, 1, 1, 12, 30, 0, tzinfo=timezone.utc)
    col_date_str = '2024-01-01'
    expected_in_liquidation_date = LegislationDatetime.as_utc_timezone_from_legislation_date_str(col_date_str)

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
    _assert_common_data(business, intent_filing, expected_in_liquidation_date, None, 2025)
    assert intent_filing.meta_data["changeOfLiquidators"] == {
        "commencementDate": LegislationDatetime.as_legislation_timezone(expected_in_liquidation_date).date().isoformat()
    }
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
    _assert_common_data(business, cease_filing, expected_in_liquidation_date, None, 2025)
    assert "changeOfLiquidators" not in cease_filing.meta_data
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
    _assert_common_data(business, change_address_filing, expected_in_liquidation_date, None, 2025)
    assert "changeOfLiquidators" not in change_address_filing.meta_data
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
    _assert_common_data(business, change_address_filing, expected_in_liquidation_date, None, 2025)
    assert "changeOfLiquidators" not in change_address_filing.meta_data
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
    _assert_common_data(business, change_address_filing, expected_in_liquidation_date, None, 2025)
    assert "changeOfLiquidators" not in change_address_filing.meta_data
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
    _assert_common_data(business, appoint_filing, expected_in_liquidation_date, None, 2025)
    assert "changeOfLiquidators" not in appoint_filing.meta_data
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
    expected_last_lr_year = 2025

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
    _assert_common_data(business, lr_filing_1, expected_in_liquidation_date, expected_last_lr_year, 2026)
    expected_lr_date_1 = LegislationDatetime.as_legislation_timezone(business.founding_date).date().replace(year=expected_last_lr_year).isoformat()
    assert lr_filing_1.meta_data["changeOfLiquidators"] == {
        "liquidationReportDate": expected_lr_date_1,
        "liquidationReportYear": expected_last_lr_year,
    }
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
    _assert_common_data(business, lr_filing_2, expected_in_liquidation_date, second_expected_last_lr_year, 2027)
    expected_lr_date_2 = LegislationDatetime.as_legislation_timezone(business.founding_date).date().replace(year=second_expected_last_lr_year).isoformat()
    assert lr_filing_2.meta_data["changeOfLiquidators"] == {
        "liquidationReportDate": expected_lr_date_2,
        "liquidationReportYear": second_expected_last_lr_year,
    }
    check_drs_publish(drs_publish_mock, app, business, lr_filing_2, '')
    drs_publish_mock.reset_mock()

    # Test cease liquidator after liquidation reports exist
    filing['filing']['changeOfLiquidators'] = {
        'type': 'ceaseLiquidator',
        'relationships': [
            {
                'entity': {
                    'identifier': party_id_2
                },
                'roles': [
                    {
                        'roleType': 'Liquidator',
                        'cessationDate': '2025-11-12'
                    }
                ]
            }
        ]
    }
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    effective_date = datetime(2025, 11, 12, 10, 0, 0, tzinfo=timezone.utc)

    filing_rec = create_filing(payment_id, filing, business.id)
    filing_rec.effective_date = effective_date
    filing_rec.save()
    filing_msg = FilingMessage(filing_identifier=filing_rec.id)

    process_filing(filing_msg)

    cease_filing_with_lr: Filing = Filing.find_by_id(filing_rec.id)
    expected_prior_lr_effective_date = LegislationDatetime.as_legislation_timezone(lr_filing_2.effective_date).date().isoformat()
    assert cease_filing_with_lr.meta_data["changeOfLiquidators"] == {
        "lastLiquidationReportDate": expected_prior_lr_effective_date,
    }
    drs_publish_mock.reset_mock()


def test_process_col_filing_initiated_with_appoint(app, session, mocker):
    """Assert that appointLiquidator filings can put the business into liquidation and can include liquidation office."""
    effective_date = datetime(2023, 10, 10, 15, 45, 0, tzinfo=timezone.utc)
    col_date_str = '2023-10-10'
    expected_in_liquidation_date = LegislationDatetime.as_utc_timezone_from_legislation_date_str(col_date_str)

    filing, payment_id, identifier = _get_liquidation_filing('appointLiquidator', expected_in_liquidation_date, col_date_str)
    drs_publish_mock = mocker.patch('business_filer.services.gcp_queue.publish', return_value=None)

    business = create_business(identifier)

    filing_rec = create_filing(payment_id, filing, business.id)
    filing_rec.effective_date = effective_date
    filing_rec.save()
    
    # create batch and batch_processing
    batch_status = 'PROCESSING'
    batch = factory_batch(status=batch_status)
    batch_processing = factory_batch_processing(batch_id=batch.id, identifier=identifier, business_id=business.id, status=batch_status)

    # setup
    filing_msg = FilingMessage(filing_identifier=filing_rec.id)

    # TEST
    process_filing(filing_msg)

    # Get modified data
    appoint_filing: Filing = Filing.find_by_id(filing_rec.id)
    business: Business = Business.find_by_internal_id(business.id)

    # assert changes
    _assert_common_data(business, appoint_filing, expected_in_liquidation_date, None, 2024)
    assert appoint_filing.meta_data["changeOfLiquidators"] == {
        "commencementDate": LegislationDatetime.as_legislation_timezone(expected_in_liquidation_date).date().isoformat()
    }
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
    
    assert batch_processing.status == BatchProcessing.BatchProcessingStatus.WITHDRAWN.value
    assert batch_processing.notes == 'Moved into liquidation'


@pytest.mark.parametrize(
    'test_name, col_date, app_date, frozen_now, expected_legislation_date_str, expected_utc_dt',
    [
        (
            'col_date during historical PST',
            '2024-01-15',
            datetime(2024, 1, 20, 18, 45, 0, tzinfo=UTC),
            '2024-01-22 12:00:00',
            '2024-01-15',
            datetime(2024, 1, 15, 8, 0, 0, tzinfo=UTC),
        ),
        (
            'col_date during PDT',
            '2024-06-20',
            datetime(2024, 6, 25, 22, 15, 0, tzinfo=UTC),
            '2024-06-26 12:00:00',
            '2024-06-20',
            datetime(2024, 6, 20, 7, 0, 0, tzinfo=UTC),
        ),
        (
            'col_date post Nov 1 2026',
            '2026-11-15',
            datetime(2026, 11, 20, 18, 45, 0, tzinfo=UTC),
            '2026-11-22 12:00:00',
            '2026-11-15',
            datetime(2026, 11, 15, 7, 0, 0, tzinfo=UTC),
        ),
        (
            'Fallback to application_date during historical PST',
            None,
            datetime(2024, 1, 15, 20, 30, 0, tzinfo=UTC),
            '2024-01-22 12:00:00',
            '2024-01-15',
            datetime(2024, 1, 15, 8, 0, 0, tzinfo=UTC),
        ),
        (
            'Fallback to application_date across UTC midnight',
            None,
            datetime(2024, 7, 16, 2, 30, 0, tzinfo=UTC),
            '2024-07-20 12:00:00',
            '2024-07-15',
            datetime(2024, 7, 15, 7, 0, 0, tzinfo=UTC),
        ),
        (
            'Fallback to application_date post Nov 1 2026',
            None,
            datetime(2026, 11, 5, 18, 30, 0, tzinfo=UTC),
            '2026-11-10 12:00:00',
            '2026-11-05',
            datetime(2026, 11, 5, 7, 0, 0, tzinfo=UTC),
        ),
        (
            'Fallback to datetime.now(UTC) during historical PST',
            None,
            None,
            '2024-02-10 14:00:00',
            '2024-02-10',
            datetime(2024, 2, 10, 8, 0, 0, tzinfo=UTC),
        ),
        (
            'Fallback to datetime.now(UTC) across UTC midnight',
            None,
            None,
            '2024-08-01 04:00:00',
            '2024-07-31',
            datetime(2024, 7, 31, 7, 0, 0, tzinfo=UTC),
        ),
        (
            'Fallback to datetime.now(UTC) post Nov 1 2026',
            None,
            None,
            '2026-11-10 14:00:00',
            '2026-11-10',
            datetime(2026, 11, 10, 7, 0, 0, tzinfo=UTC),
        ),
    ]
)
def test_init_liquidation_date(
    session,
    mocker,
    test_name,
    col_date,
    app_date,
    frozen_now,
    expected_legislation_date_str,
    expected_utc_dt,
):
    """Assert business.in_liquidation_date is normalized to start-of-day Pacific converted to UTC."""
    mocker.patch(
        'business_filer.common.services.InvoluntaryDissolutionService.get_in_dissolution_batch_processing',
        return_value=None
    )

    business = Business()
    business.state = Business.State.ACTIVE

    filing_meta = FilingMeta()
    filing_meta.application_date = app_date

    filing_json = {
        'filing': {
            'changeOfLiquidators': {}
        }
    }
    if col_date:
        filing_json['filing']['changeOfLiquidators']['changeOfLiquidatorsDate'] = col_date

    with freeze_time(frozen_now, tz_offset=0):
        _init_liquidation(business, filing_meta, filing_json)

    assert business.in_liquidation is True

    assert business.in_liquidation_date == expected_utc_dt

    local_legislation_dt = LegislationDatetime.as_legislation_timezone(business.in_liquidation_date)
    assert local_legislation_dt.strftime('%Y-%m-%d') == expected_legislation_date_str
    assert local_legislation_dt.hour == 0
    assert local_legislation_dt.minute == 0
    assert local_legislation_dt.second == 0
    assert local_legislation_dt.microsecond == 0


def test_liquidation_report_feb_29_founding_date(app, session, mocker):
    """Assert that a liquidationReport filing handles a business founded on Feb 29 (leap year)."""
    drs_publish_mock = mocker.patch('business_filer.services.gcp_queue.publish', return_value=None)
    identifier = 'BC9999999'

    # Business founded on leap day 2020-02-29
    business = create_business(identifier)
    business.founding_date = datetime(2020, 2, 29, 12, 0, 0, tzinfo=UTC)
    business.in_liquidation = True
    business.in_liquidation_date = datetime(2024, 3, 1, 8, 0, 0, tzinfo=UTC)
    business.last_lr_year = None
    business.save()

    filing = copy.deepcopy(FILING_TEMPLATE)
    filing['filing']['header']['name'] = 'changeOfLiquidators'
    filing['filing']['business']['identifier'] = identifier
    filing['filing']['changeOfLiquidators'] = {
        'type': 'liquidationReport',
    }

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    effective_date = datetime(2025, 4, 1, 10, 0, 0, tzinfo=timezone.utc)
    filing_rec = create_filing(payment_id, filing, business.id)
    filing_rec.effective_date = effective_date
    filing_rec.save()

    filing_msg = FilingMessage(filing_identifier=filing_rec.id)
    process_filing(filing_msg)

    processed_filing: Filing = Filing.find_by_id(filing_rec.id)
    updated_business: Business = Business.find_by_internal_id(business.id)

    assert updated_business.last_lr_year == 2025
    assert processed_filing.meta_data["changeOfLiquidators"] == {
        "liquidationReportDate": "2025-03-01",
        "liquidationReportYear": 2025,
    }
