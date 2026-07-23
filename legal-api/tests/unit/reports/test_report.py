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

"""Test-Suite to ensure that the Report class is working as expected."""
import copy
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from flask import current_app

from business_common.utils.legislation_datetime import LegislationDatetime
from business_model.models import Business, PartyRole, db
from business_model.models.db import VersioningProxy
from legal_api.exceptions import BusinessException
from legal_api.reports.document_service import DocumentService
from legal_api.reports.report import Report
from registry_schemas.example_data import (
    AGM_LOCATION_CHANGE,
    ALTERATION_FILING_TEMPLATE,
    ANNUAL_REPORT,
    CHANGE_OF_ADDRESS,
    CHANGE_OF_DIRECTORS,
    CHANGE_OF_DIRECTORS_MAILING,
    CHANGE_OF_LIQUIDATORS,
    CHANGE_OF_NAME,
    CORP_CHANGE_OF_ADDRESS,
    CORRECTION_COMBINED_AR,
    DISSOLUTION,
    FILING_HEADER,
    NOTICE_OF_WITHDRAWAL,
    RESTORATION,
    INCORPORATION_FILING_TEMPLATE,
    SPECIAL_RESOLUTION,
    TRANSITION_FILING_TEMPLATE,
)
from tests.unit.models import factory_address, factory_business, factory_business_office, factory_completed_filing, factory_party_role, factory_pending_filing
from legal_api.reports.utils import ColinService


def create_report(identifier, entity_type, report_type, filing_type, template):
    """Create an instance of the Report class."""
    if template.get('filing'):
        filing_json = copy.deepcopy(template)
    else:
        filing_json = copy.deepcopy(FILING_HEADER)
        filing_json['filing'][f'{filing_type}'] = copy.deepcopy(template)
    filing_json['filing']['business']['identifier'] = identifier
    filing_json['filing']['business']['legalType'] = entity_type
    filing_json['filing']['header']['name'] = filing_type

    business = factory_business(identifier=identifier, entity_type=entity_type)
    if report_type == 'correction':
        original_filing_json = copy.deepcopy(filing_json)
        original_filing_json['filing']['header']['name'] = filing_json['filing']['correction']['correctedFilingType']
        del original_filing_json['filing']['correction']
        original_filing = factory_completed_filing(business, original_filing_json)
        filing_json['filing']['correction']['correctedFilingId'] = original_filing.id
    if report_type == 'specialResolution' and filing_type != 'specialResolution':
        # coop dissolutions carry the resolution in a specialResolution section under the filing
        filing_json['filing']['specialResolution'] = SPECIAL_RESOLUTION
    filing = factory_completed_filing(business, filing_json)

    report = Report(filing)
    report._business = business
    report._report_key = report_type
    if report._report_key == 'correction':
        report._report_key = report._filing.filing_json['filing']['correction']['correctedFilingType']

    return report


def populate_business_info_to_filing(report):
    """Assert _populate_business_info_to_filing works as expected."""
    report._populate_business_info_to_filing(report._filing, report._business)
    filing_json = report._filing.filing_json
    assert filing_json['filing']['business']['formatted_founding_date_time']
    assert filing_json['filing']['business']['formatted_founding_date']


def set_dates(report):
    """Assert _set_dates works as expected."""
    filing_json = report._filing.filing_json
    report._set_dates(filing_json)
    assert filing_json['filing_date_time']
    assert filing_json['effective_date_time']
    assert filing_json['effective_date']
    assert filing_json['recognition_date_time']
    # TODO: figure out why this fails and improve test/code
    # if report._report_key == 'annualReport':
    #     assert filing_json['agm_date']
    # if report_type == 'correction':
    #     assert filing_json['original_filing_date_time']


def substitute_template_parts(report):
    """Assert _substitute_template_parts works as expected."""
    template_path = current_app.config.get('REPORT_TEMPLATE_PATH')
    template_code = Path(f'{template_path}/{report._get_template_filename()}').read_text()
    # substitute template parts
    template_code = report._substitute_template_parts(template_code)
    assert template_code


def set_description(report):
    """Assert _set_description works as expected."""
    filing_json = report._filing.filing_json
    report._set_description(filing_json)
    assert filing_json.get('entityDescription')


def set_registrar_info(report):
    """Assert _set_registrar_info works as expected."""
    filing_json = report._filing.filing_json
    report._set_registrar_info(filing_json)
    assert filing_json.get('registrarInfo')


def set_tax_id(report):
    """Assert _set_tax_id works as expected."""
    filing_json = report._filing.filing_json
    report._set_tax_id(filing_json)
    assert filing_json.get('taxId')


def set_addresses(report, mocker):
    """Assert _set_addresses works as expected."""
    filing_json = report._filing.filing_json
    
    previous_filing_json = copy.deepcopy(FILING_HEADER)
    previous_filing_json['filing']['header']['name'] = 'changeOfAddress'
    previous_filing_json['filing']['business']['identifier'] = 'BC1234567'
    previous_filing_json['filing']['business']['legalType'] = 'BC'
    previous_filing_json['filing']['changeOfAddress'] = {}
    previous_filing = factory_completed_filing(report._business, previous_filing_json, filing_date=datetime(2020, 1, 1))

    mocker.patch('business_model.models.Filing.get_previous_completed_filing', return_value=previous_filing)
    mocker.patch('legal_api.services.VersionedBusinessDetailsService.get_office_revision', return_value={
        'registeredOffice': {
            'mailingAddress': {
                'streetAddress': 'Old Mailing Street',
                'addressCity': 'Victoria',
                'addressRegion': 'BC',
                'addressCountry': 'CA',
                'postalCode': 'V8W1P5'
            },
            'deliveryAddress': {
                'streetAddress': 'Old Delivery Street',
                'addressCity': 'Victoria',
                'addressRegion': 'BC',
                'addressCountry': 'CA',
                'postalCode': 'V8W1P4'
            }
        },
        'recordsOffice': {
            'mailingAddress': {
                'streetAddress': 'Old Mailing Street',
                'addressCity': 'Victoria',
                'addressRegion': 'BC',
                'addressCountry': 'CA',
                'postalCode': 'V8W1P5'
            },
            'deliveryAddress': {
                'streetAddress': 'Old Delivery Street',
                'addressCity': 'Victoria',
                'addressRegion': 'BC',
                'addressCountry': 'CA',
                'postalCode': 'V8W1P4'
            }
        }
    })

    with suppress(KeyError):
        with patch.object(report, '_format_address', return_value=None):
            report._set_addresses(filing_json['filing'])

    assert filing_json['filing'].get('registeredOfficeAddress')
    if report._business.legal_type == 'BEN' and report._report_key == 'changeOfAddress':
        assert filing_json['filing'].get('recordsOfficeAddress')


def set_meta_info(report):
    """Assert _set_meta_info works as expected."""
    filing_json = report._filing.filing_json
    report._set_meta_info(filing_json)
    assert filing_json.get('environment')
    assert filing_json.get('source')
    assert filing_json.get('meta_title')
    assert filing_json.get('meta_subject')


@pytest.mark.parametrize(
    'test_name, identifier, entity_type, report_type, filing_type, template',
    [
        ('CP AR', 'CP1234567', 'CP', 'annualReport', 'annualReport', ANNUAL_REPORT),
        ('CP COA', 'CP1234567', 'CP', 'changeOfAddress', 'changeOfAddress', CHANGE_OF_ADDRESS),
        ('CP COD', 'CP1234567', 'CP', 'changeOfDirectors', 'changeOfDirectors', CHANGE_OF_DIRECTORS),
        ('CP COR combined AR', 'CP1234567', 'CP', 'correction', 'correction', CORRECTION_COMBINED_AR),
        ('CP CON', 'CP1234567', 'CP', 'changeOfName', 'changeOfName', CHANGE_OF_NAME),
        ('CP SR', 'CP1234567', 'CP', 'specialResolution', 'specialResolution', SPECIAL_RESOLUTION),
        ('CP SR', 'CP1234567', 'CP', 'specialResolutionApplication', 'specialResolution', SPECIAL_RESOLUTION),
        ('CP DISSOLUTION', 'CP1234567', 'CP', 'dissolution', 'dissolution', DISSOLUTION),
        ('CP DISSOLUTION', 'CP1234567', 'CP', 'specialResolution', 'dissolution', DISSOLUTION),
        ('BEN DISSOLUTION', 'BC1234567', 'BEN', 'dissolution', 'dissolution', DISSOLUTION),
        ('BC DISSOLUTION', 'BC1234567', 'BC', 'dissolution', 'dissolution', DISSOLUTION),
        ('CC DISSOLUTION', 'BC2345678', 'CC', 'dissolution', 'dissolution', DISSOLUTION),
        ('ULC DISSOLUTION', 'BC1234567', 'ULC', 'dissolution', 'dissolution', DISSOLUTION),
        ('CP DISSOLUTION', 'CP1234567', 'CP', 'certificateOfDissolution', 'dissolution', DISSOLUTION),
        ('BEN AR', 'BC1234567', 'BEN', 'annualReport', 'annualReport', ANNUAL_REPORT),
        ('BEN COA', 'BC1234567', 'BEN', 'changeOfAddress', 'changeOfAddress', CORP_CHANGE_OF_ADDRESS),
        ('BEN COD', 'BC1234567', 'BEN', 'changeOfDirectors', 'changeOfDirectors', CHANGE_OF_DIRECTORS_MAILING),
        ('BEN INC', 'BC1234567', 'BEN', 'incorporationApplication', 'incorporationApplication',
         INCORPORATION_FILING_TEMPLATE),
        ('BEN CER', 'BC1234567', 'BEN', 'certificateOfIncorporation', 'incorporationApplication', INCORPORATION_FILING_TEMPLATE),
        ('BEN TRANP', 'BC1234567', 'BEN', 'transition', 'transition', TRANSITION_FILING_TEMPLATE),
    ]
)
def test_get_pdf(session, mocker, test_name, identifier, entity_type, report_type, filing_type, template):
    """Assert all filings can be returned as a PDF."""
    # TODO: add checks on set_directors, noa
    # setup
    report = create_report(identifier=identifier, entity_type=entity_type, report_type=report_type,
                           filing_type=filing_type, template=template)

    # verify
    populate_business_info_to_filing(report)
    set_dates(report)
    substitute_template_parts(report)
    set_description(report)
    set_registrar_info(report)
    set_meta_info(report)

    if report_type in ['annualReport', 'changeOfAddress']:
        set_addresses(report, mocker)

    if report._business.legal_type != 'CP':
        set_tax_id(report)

    filename = report._get_report_filename()
    assert filename
    template = report._get_template()
    assert template


def test_special_resolution_sourced_from_dissolution_filing(session):
    """Assert the special resolution report for a coop dissolution sources the resolution from the specialResolution section (#32963).

    Before the fix the resolution was read from the (empty) correction section, leaving the resolution/signing
    dates unformatted and the resolution content missing.
    """
    identifier = 'CP1234567'
    business = factory_business(identifier=identifier, entity_type='CP')

    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['header']['name'] = 'dissolution'
    filing_json['filing']['business']['identifier'] = identifier
    filing_json['filing']['business']['legalType'] = 'CP'
    filing_json['filing']['dissolution'] = copy.deepcopy(DISSOLUTION)
    filing_json['filing']['dissolution']['dissolutionType'] = 'voluntary'
    filing_json['filing']['specialResolution'] = copy.deepcopy(SPECIAL_RESOLUTION)
    filing = factory_completed_filing(business, filing_json)

    report = Report(filing)
    report._business = business
    report._report_key = 'specialResolution'

    filing_data = copy.deepcopy(filing.filing_json['filing'])
    filing_data['header']['filingId'] = filing.id
    report._format_special_resolution(filing_data)

    # dates come from the specialResolution section and are formatted (not left as raw ISO strings)
    assert filing_data['specialResolution']['resolutionDate'] == 'January 10, 2021'
    assert filing_data['specialResolution']['signingDate'] == 'January 10, 2021'


def test_set_directors_flags_address_changed_without_officer_id(session, mocker):
    """Assert addressChanged flags are set using previous filing lookup by name."""
    business = factory_business(identifier='BC1234567', entity_type='BC')

    previous_filing_json = copy.deepcopy(FILING_HEADER)
    previous_filing_json['filing']['header']['name'] = 'changeOfDirectors'
    previous_filing_json['filing']['business']['identifier'] = 'BC1234567'
    previous_filing_json['filing']['business']['legalType'] = 'BC'
    previous_filing_json['filing']['changeOfDirectors'] = {'directors': []}
    factory_completed_filing(business, previous_filing_json, filing_date=datetime(2020, 1, 1))

    current_filing_json = copy.deepcopy(FILING_HEADER)
    current_filing_json['filing']['header']['name'] = 'changeOfDirectors'
    current_filing_json['filing']['business']['identifier'] = 'BC1234567'
    current_filing_json['filing']['business']['legalType'] = 'BC'
    current_filing_json['filing']['changeOfDirectors'] = {
        'directors': [
            {
                'officer': {
                    'firstName': 'Jane',
                    'middleInitial': 'A',
                    'lastName': 'Smith'
                },
                'actions': ['addressChanged'],
                'mailingAddress': {
                    'streetAddress': 'New Mailing Street',
                    'addressCity': 'Victoria',
                    'addressRegion': 'BC',
                    'addressCountry': 'CA',
                    'postalCode': 'V8W1P6'
                },
                'deliveryAddress': {
                    'streetAddress': 'New Delivery Street',
                    'addressCity': 'Victoria',
                    'addressRegion': 'BC',
                    'addressCountry': 'CA',
                    'postalCode': 'V8W1P7'
                }
            }
        ]
    }
    filing = factory_completed_filing(business, current_filing_json, filing_date=datetime(2020, 1, 2))
    report = Report(filing)
    report._business = business
    report._report_key = 'changeOfDirectors'

    previous_director = {
        'id': '123',
        'officer': {
            'firstName': 'Jane',
            'middleInitial': 'A',
            'lastName': 'Smith'
        },
        'cessationDate': None
    }
    mocker.patch('legal_api.services.VersionedBusinessDetailsService.get_party_role_revision', return_value=[previous_director])
    mocker.patch('legal_api.services.VersionedBusinessDetailsService.get_party_revision', return_value=object())
    mocker.patch('legal_api.services.VersionedBusinessDetailsService.party_revision_json', return_value={
        'mailingAddress': {
            'streetAddress': 'Old Mailing Street',
            'addressCity': 'Victoria',
            'addressRegion': 'BC',
            'addressCountry': 'CA',
            'postalCode': 'V8W1P5'
        },
        'deliveryAddress': {
            'streetAddress': 'Old Delivery Street',
            'addressCity': 'Victoria',
            'addressRegion': 'BC',
            'addressCountry': 'CA',
            'postalCode': 'V8W1P4'
        }
    })

    report._set_directors(filing.filing_json['filing'])

    director = filing.filing_json['filing']['listOfDirectors']['directors'][0]
    assert director['mailingAddress']['changed'] is True
    assert director['deliveryAddress']['changed'] is True


def test_alteration_name_change(session, monkeypatch):
    """Assert alteration name change filings can be returned as a PDF."""
    # Create a mock flags object with is_on method
    from unittest.mock import Mock
    mock_flags = Mock()
    mock_flags.is_on.return_value = False
    mock_flags.value.return_value = []
    
    # Patch the flags instance in the report module
    import legal_api.reports.report
    monkeypatch.setattr(legal_api.reports.report, 'flags', mock_flags)
    numbered_company_name = '1234567 B.C. Ltd.'
    named_company_name = 'New Name Ltd.'
    identifier = 'BC1234567'
    entity_type = 'BEN'
    report_type = 'certificateOfNameChange'

    # An existing business
    business = factory_business(identifier=identifier, entity_type=entity_type)

    # changes its name to a named company
    named_company_filing = filing_named_company(business, ALTERATION_FILING_TEMPLATE, named_company_name)
    update_business_legal_name(business, named_company_name)
    named_company_report = create_alteration_report(named_company_filing, business, report_type)
    named_company_report_filename = named_company_report._get_report_filename()
    assert named_company_report_filename
    named_company_report_template = named_company_report._get_template()
    assert named_company_report_template
    named_company_report_template_data = named_company_report._get_template_data()
    assert named_company_report_template_data['toLegalName'] == named_company_name

    # changes its name to a numbered company
    numbered_company_filing = filing_numbered_company(business, ALTERATION_FILING_TEMPLATE, numbered_company_name)
    update_business_legal_name(business, numbered_company_name)

    # new legal_name can be retrieved from the business (numbered company case)
    business_new = Business.find_by_internal_id(business.id)
    assert business_new.legal_name == numbered_company_name
    numbered_company_report = create_alteration_report(numbered_company_filing, business, report_type)
    numbered_company_filename = numbered_company_report._get_report_filename()
    assert numbered_company_filename
    numbered_company_template = numbered_company_report._get_template()
    assert numbered_company_template
    numbered_company_template_data = numbered_company_report._get_template_data()
    assert numbered_company_template_data['toLegalName'] == numbered_company_name


def update_business_legal_name(business, legal_name):
    """Update business legal name."""
    VersioningProxy.get_transaction_id(db.session())
    business.legal_name = legal_name
    business.save()


def filing_named_company(business, template, legal_name):
    """Create a filing for a name change with for named company."""
    filing_json = copy.deepcopy(template)
    filing_json['filing']['alteration']['nameRequest']['legalName'] = legal_name
    filing = factory_completed_filing(business, filing_json)
    filing._meta_data = {
        'alteration': {
            'fromLegalName': business.legal_name,
            'toLegalName': legal_name
        }
    }
    filing.save()
    return filing


def filing_numbered_company(business, template, legal_name):
    """Create a filing for a name change with for numbered company."""
    filing_json = copy.deepcopy(template)
    del filing_json['filing']['alteration']['nameRequest']['legalName']
    del filing_json['filing']['alteration']['nameRequest']['nrNumber']
    filing = factory_completed_filing(business, filing_json)
    filing._meta_data = {
        'alteration': {
            'fromLegalName': business.legal_name,
            'toLegalName': legal_name
        }
    }
    filing.save()
    return filing


def create_alteration_report(filing, business, report_type):
    """Create a report for alteration."""
    report = Report(filing)
    report._business = business
    report._report_key = report_type
    populate_business_info_to_filing(report)
    set_dates(report)
    substitute_template_parts(report)
    set_description(report)
    set_registrar_info(report)
    set_meta_info(report)
    return report


@pytest.mark.parametrize(
        'test_name, identifier, entity_type, filing_template, filing_type, formatted_filing_type',
        [
            ('BC agmLocationChange', 'BC1234567', 'BC', AGM_LOCATION_CHANGE, 'agmLocationChange', 'AGM Location Change'),
            ('BC alteration', 'BC1234567', 'BC', ALTERATION_FILING_TEMPLATE, 'alteration', 'Alteration'),
            ('BC changeOfAddress', 'BC1234567', 'BC', CHANGE_OF_ADDRESS, 'changeOfAddress', 'Address Change'),
            ('BC changeOfDirectors', 'BC1234567', 'BC', CHANGE_OF_DIRECTORS, 'changeOfDirectors', 'Director Change'),
            ('BC dissolution', 'BC1234567', 'BC', DISSOLUTION, 'dissolution', 'Voluntary Dissolution'),
            ('BC restoration', 'BC1234567', 'BC', RESTORATION, 'restoration', 'Full Restoration Application'),
            ('BEN agmLocationChange', 'BC1234567', 'BEN', AGM_LOCATION_CHANGE, 'agmLocationChange', 'AGM Location Change'),
            ('BEN alteration', 'BC1234567', 'BEN', ALTERATION_FILING_TEMPLATE, 'alteration', 'Alteration'),
            ('BEN changeOfAddress', 'BC1234567', 'BEN', CHANGE_OF_ADDRESS, 'changeOfAddress', 'Address Change'),
            ('BEN changeOfDirectors', 'BC1234567', 'BEN', CHANGE_OF_DIRECTORS, 'changeOfDirectors', 'Director Change'),
            ('BEN dissolution', 'BC1234567', 'BEN', DISSOLUTION, 'dissolution', 'Voluntary Dissolution'),
            ('BEN restoration', 'BC1234567', 'BEN', RESTORATION, 'restoration', 'Full Restoration Application'),
            ('ULC agmLocationChange', 'BC1234567', 'ULC', AGM_LOCATION_CHANGE, 'agmLocationChange', 'AGM Location Change'),
            ('ULC alteration', 'BC1234567', 'ULC', ALTERATION_FILING_TEMPLATE, 'alteration', 'Alteration'),
            ('ULC changeOfAddress', 'BC1234567', 'ULC', CHANGE_OF_ADDRESS, 'changeOfAddress', 'Address Change'),
            ('ULC changeOfDirectors', 'BC1234567', 'ULC', CHANGE_OF_DIRECTORS, 'changeOfDirectors', 'Director Change'),
            ('ULC dissolution', 'BC1234567', 'ULC', DISSOLUTION, 'dissolution', 'Voluntary Dissolution'),
            ('ULC restoration', 'BC1234567', 'ULC', RESTORATION, 'restoration', 'Full Restoration Application'),
            ('CC agmLocationChange', 'BC1234567', 'CC', AGM_LOCATION_CHANGE, 'agmLocationChange', 'AGM Location Change'),
            ('CC alteration', 'BC1234567', 'CC', ALTERATION_FILING_TEMPLATE, 'alteration', 'Alteration'),
            ('CC changeOfAddress', 'BC1234567', 'CC', CHANGE_OF_ADDRESS, 'changeOfAddress', 'Address Change'),
            ('CC changeOfDirectors', 'BC1234567', 'CC', CHANGE_OF_DIRECTORS, 'changeOfDirectors', 'Director Change'),
            ('CC dissolution', 'BC1234567', 'CC', DISSOLUTION, 'dissolution', 'Voluntary Dissolution'),
            ('CC restoration', 'BC1234567', 'CC', RESTORATION, 'restoration', 'Full Restoration Application'),
            ('C agmLocationChange', 'C1234567', 'C', AGM_LOCATION_CHANGE, 'agmLocationChange', 'AGM Location Change'),
            ('C alteration', 'C1234567', 'C', ALTERATION_FILING_TEMPLATE, 'alteration', 'Alteration'),
            ('C changeOfAddress', 'C1234567', 'C', CHANGE_OF_ADDRESS, 'changeOfAddress', 'Address Change'),
            ('C changeOfDirectors', 'C1234567', 'C', CHANGE_OF_DIRECTORS, 'changeOfDirectors', 'Director Change'),
            ('C dissolution', 'C1234567', 'C', DISSOLUTION, 'dissolution', 'Voluntary Dissolution'),
            ('C restoration', 'C1234567', 'C', RESTORATION, 'restoration', 'Full Restoration Application'),
            ('CUL agmLocationChange', 'C1234567', 'CUL', AGM_LOCATION_CHANGE, 'agmLocationChange', 'AGM Location Change'),
            ('CUL alteration', 'C1234567', 'CUL', ALTERATION_FILING_TEMPLATE, 'alteration', 'Alteration'),
            ('CUL changeOfAddress', 'C1234567', 'CUL', CHANGE_OF_ADDRESS, 'changeOfAddress', 'Address Change'),
            ('CUL changeOfDirectors', 'C1234567', 'CUL', CHANGE_OF_DIRECTORS, 'changeOfDirectors', 'Director Change'),
            ('CUL dissolution', 'C1234567', 'CUL', DISSOLUTION, 'dissolution', 'Voluntary Dissolution'),
            ('CUL restoration', 'C1234567', 'CUL', RESTORATION, 'restoration', 'Full Restoration Application'),
            ('CBEN agmLocationChange', 'C1234567', 'CBEN', AGM_LOCATION_CHANGE, 'agmLocationChange', 'AGM Location Change'),
            ('CBEN alteration', 'C1234567', 'CBEN', ALTERATION_FILING_TEMPLATE, 'alteration', 'Alteration'),
            ('CBEN changeOfAddress', 'C1234567', 'CBEN', CHANGE_OF_ADDRESS, 'changeOfAddress', 'Address Change'),
            ('CBEN changeOfDirectors', 'C1234567', 'CBEN', CHANGE_OF_DIRECTORS, 'changeOfDirectors', 'Director Change'),
            ('CBEN dissolution', 'C1234567', 'CBEN', DISSOLUTION, 'dissolution', 'Voluntary Dissolution'),
            ('CBEN restoration', 'C1234567', 'CBEN', RESTORATION, 'restoration', 'Full Restoration Application'),
            ('CCC agmLocationChange', 'C1234567', 'CCC', AGM_LOCATION_CHANGE, 'agmLocationChange', 'AGM Location Change'),
            ('CCC alteration', 'C1234567', 'CCC', ALTERATION_FILING_TEMPLATE, 'alteration', 'Alteration'),
            ('CCC changeOfAddress', 'C1234567', 'CCC', CHANGE_OF_ADDRESS, 'changeOfAddress', 'Address Change'),
            ('CCC changeOfDirectors', 'C1234567', 'CCC', CHANGE_OF_DIRECTORS, 'changeOfDirectors', 'Director Change'),
            ('CCC dissolution', 'C1234567', 'CCC', DISSOLUTION, 'dissolution', 'Voluntary Dissolution'),
            ('CCC restoration', 'C1234567', 'CCC', RESTORATION, 'restoration', 'Full Restoration Application')
        ]
)
def test_notice_of_withdraw_format_data(session, test_name, identifier, entity_type, filing_template, filing_type, formatted_filing_type):
    """Test the data passed to NoW report template - existing business"""
    # create a business
    test_business = factory_business(identifier=identifier, entity_type=entity_type)
    
    # file a FE filing
    today = datetime.now(UTC).date()
    future_effective_date = today + timedelta(days=5)
    future_effective_date = future_effective_date.isoformat()
    withdrawn_json = copy.deepcopy(FILING_HEADER)
    withdrawn_json['filing']['header']['name'] = filing_type
    withdrawn_json['filing']['business']['legalType'] = entity_type
    withdrawn_json['filing'][filing_type] = copy.deepcopy(filing_template)
    withdrawn_filing = factory_pending_filing(test_business, withdrawn_json)
    withdrawn_filing.effective_date = future_effective_date
    withdrawn_filing.payment_completion_date = today.isoformat()
    withdrawn_filing.save()
    withdrawn_filing_id = withdrawn_filing.id

    # file a NoW filing
    now_json = copy.deepcopy(FILING_HEADER)
    now_json['filing']['header']['name'] = 'noticeOfWithdrawal'
    now_json['filing']['business']['legalType'] = 'BC'
    now_json['filing']['noticeOfWithdrawal'] = copy.deepcopy(NOTICE_OF_WITHDRAWAL)
    now_json['filing']['noticeOfWithdrawal']['filingId'] = withdrawn_filing_id

    # verify formatted NoW data for report template
    formatted_now_json = copy.deepcopy(now_json['filing'])
    report_instance = Report({})
    expected_withdrawn_filing_effective_date = LegislationDatetime.as_legislation_timezone(withdrawn_filing.effective_date)
    expected_withdrawn_filing_effective_date = LegislationDatetime.format_as_report_string(expected_withdrawn_filing_effective_date)
    report_instance._format_notice_of_withdrawal_data(formatted_now_json)
    assert formatted_now_json['withdrawnFilingType'] == formatted_filing_type
    assert formatted_now_json['withdrawnFilingEffectiveDate'] == expected_withdrawn_filing_effective_date
    assert formatted_now_json['noticeOfWithdrawal']['filingId'] == withdrawn_filing_id


def test_document_service_not_create_document(session, mock_doc_service, mock_bearer_token):
    filing = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    report = create_report(identifier='BC9999999', entity_type='BC', report_type='annualReport',
                           filing_type='incorporationApplication', template=filing)
    assert report
    document_service = DocumentService()
    try:
        document_service.get_document(report._filing.id,
                                      'annualReport',
                                      '3113')
        # Expectation is that the above call SHOULD fail in this case as document was not created
        assert False
    except BusinessException as err:
        assert err.status_code == HTTPStatus.NOT_FOUND

@pytest.mark.parametrize(
    'test_name, identifier, entity_type, expected_is_corp',
    [
        # Corporation types - should be True
        ('BC corp', 'BC1234567', 'BC', True),
        ('BEN corp', 'BC1234567', 'BEN', True),
        ('CC corp', 'BC1234567', 'CC', True),
        ('ULC corp', 'BC1234567', 'ULC', True),
        ('C continuation', 'C1234567', 'C', True),
        ('CBEN continuation', 'C1234567', 'CBEN', True),
        ('CCC continuation', 'C1234567', 'CCC', True),
        ('CUL continuation', 'C1234567', 'CUL', True),
        # Non-corporation types - should be False
        ('CP cooperative', 'CP1234567', 'CP', False),
        ('SP sole prop', 'FM1234567', 'SP', False),
        ('GP partnership', 'FM1234567', 'GP', False),
    ]
)
def test_set_corp_flag(session, test_name, identifier, entity_type, expected_is_corp):
    """Assert _set_corp_flag correctly identifies corporation vs non-corporation types."""
    report = create_report(
        identifier=identifier,
        entity_type=entity_type,
        report_type='annualReport',
        filing_type='annualReport',
        template=ANNUAL_REPORT
    )
    report._populate_business_info_to_filing(report._filing, report._business)

    filing = report._filing.filing_json['filing']
    report._set_corp_flag(filing)

    assert filing['business']['isCorp'] == expected_is_corp, \
        f'{test_name}: expected isCorp={expected_is_corp} for legalType={entity_type}'


@pytest.mark.parametrize('test_name, submitter_role, login_source, expected_certified_by', [
    ('staff_uses_header', 'staff', 'IDIR', 'Header Name'),
    ('api_user_uses_header', None, 'API_GW', 'Header Name'),
    ('public_user_uses_submitter', None, 'BCSC', 'Submitter Name'),
])
def test_set_completing_party_header_certified_by(session, test_name, submitter_role,
                                                  login_source, expected_certified_by):
    """Staff and API users use the header certifiedBy; API users are identified by the jwt loginSource."""
    from business_model.models import User
    from legal_api.services import flags
    from registry_schemas.example_data import INCORPORATION_FILING_TEMPLATE

    template = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    template['filing']['header']['certifiedBy'] = 'Header Name'
    report = create_report(
        identifier='BC1234567',
        entity_type='BEN',
        report_type='incorporationApplication',
        filing_type='incorporationApplication',
        template=template
    )
    submitter = User()
    submitter.firstname = 'Submitter'
    submitter.lastname = 'Name'
    submitter.login_source = login_source
    report._filing.submitter_roles = submitter_role
    report._filing.filing_submitter = submitter

    filing = report._filing.filing_json['filing']
    filing['flags'] = {}

    with patch.object(flags, 'value', return_value=['incorporationApplication-completingParty']):
        report._set_completing_party(filing)

    assert filing['flags']['incorporationApplication_completingParty'] is True
    assert filing['header']['certifiedBy'] == expected_certified_by


def _create_previous_liquidation_report(business):
    lr_filing_json = copy.deepcopy(FILING_HEADER)
    lr_filing_json['filing']['header']['name'] = 'changeOfLiquidators'
    lr_filing_json['filing']['business']['identifier'] = business.identifier
    lr_filing_json['filing']['changeOfLiquidators'] = {'type': 'liquidationReport'}
    factory_completed_filing(
        business=business,
        data_dict=lr_filing_json,
        filing_date=datetime(2026, 5, 15, 10, 0, 0),
        filing_type='changeOfLiquidators',
        filing_sub_type='liquidationReport'
    )

def _get_col_filing_json(business, col_data):
    return {
        'filing': {
            'header': {
                'name': 'changeOfLiquidators',
                'date': '2026-06-10T12:00:00+00:00',
                'effectiveDate': '2026-06-10T12:00:00+00:00'
            },
            'business': {
                'identifier': business.identifier,
                'legalType': business.legal_type
            },
            'changeOfLiquidators': col_data
        }
    }

def _create_existing_liquidator(session, business):
    liquidator = factory_party_role(
        delivery_address=factory_address('123 Existing St', 'delivery'),
        mailing_address=factory_address('123 Existing St', 'mailing'),
        appointment_date=datetime(2025, 5, 15, 10, 0, 0),
        cessation_date=None,
        officer={
            'firstName': 'EXISTING LIQUIDATOR',
            'lastName': '',
            'middleInitial': '',
            'partyType': 'person',
            'organizationName': ''
        },
        role_type=PartyRole.RoleTypes.LIQUIDATOR
    )
    liquidator.business_id = business.id
    session.add(liquidator)
    session.commit()

    return liquidator

def test_format_appoint_liquidator_data(session):
    """Assert _format_liquidator_data correctly formats an appointLiquidator filing."""
    business = factory_business(identifier='BC1234567', entity_type='BC')
    _create_previous_liquidation_report(business)
    _create_existing_liquidator(session, business)

    col = copy.deepcopy(CHANGE_OF_LIQUIDATORS)
    col['type'] = 'appointLiquidator'
    col['courtOrder'] = {
        'hasPlanOfArrangement': True,
        'fileNumber': '12345678'
    }

    current_filing_json = _get_col_filing_json(business, col)
    current_filing = factory_completed_filing(business, current_filing_json, filing_date=datetime(2026, 1, 2))

    report = Report(current_filing)
    report._business = business

    filing_data = current_filing_json['filing']
    report._format_liquidator_data(filing_data)

    assert filing_data['reportTitle'] == 'Notice to Appoint Liquidators'
    assert filing_data['reportDateAndTimeTitle'] == 'Appointed Date and Time:'
    assert filing_data['lastReportDate'] == 'May 15, 2026'
    assert filing_data['hasReceivers'] is False
    assert filing_data['hasPoa'] is True
    assert filing_data['courtOrderNumber'] == '12345678'

    rels = filing_data.get('relationships', {})
    assert 'appointed' in rels
    assert 'effectiveDate' in rels
    assert 'ceased' not in rels

    appointed_items = rels['appointed']['items']
    assert len(appointed_items) == 2

    first_liquidator = appointed_items[0]
    assert first_liquidator['entity']['familyName'] == 'Miller'
    assert first_liquidator['entity']['givenName'] == 'Phillip Tandy'

    assert 'mailingAddress' in first_liquidator
    assert 'deliveryAddress' in first_liquidator

    second_liquidator = appointed_items[1]
    assert second_liquidator['entity']['businessName'] == 'Test Business'

    effective_items = rels['effectiveDate']['items']
    existing_liquidator_found = any(
        item['entity'].get('givenName') == 'EXISTING LIQUIDATOR'
        for item in effective_items
    )
    assert existing_liquidator_found is True

def test_format_cease_liquidator_data(session):
    """Assert _format_liquidator_data correctly formats a ceaseLiquidator filing."""
    business = factory_business(identifier='BC1234567', entity_type='BC')
    _create_previous_liquidation_report(business)
    _create_existing_liquidator(session, business)

    col = copy.deepcopy(CHANGE_OF_LIQUIDATORS)
    col['type'] = 'ceaseLiquidator'

    for rel in col['relationships']:
        for role in rel['roles']:
            role['cessationDate'] = '2026-01-02'

    current_filing_json = _get_col_filing_json(business, col)
    current_filing = factory_completed_filing(business, current_filing_json, filing_date=datetime(2026, 1, 2))

    report = Report(current_filing)
    report._business = business

    filing_data = current_filing_json['filing']
    report._format_liquidator_data(filing_data)

    assert filing_data['reportTitle'] == 'Notice to Cease Liquidators'
    assert filing_data['reportDateAndTimeTitle'] == 'Ceased Date and Time:'
    assert filing_data['lastReportDate'] == 'May 15, 2026'
    assert filing_data['hasReceivers'] is False
    assert filing_data['hasPoa'] is False
    assert filing_data['courtOrderNumber'] is False

    rels = filing_data.get('relationships', {})
    assert 'appointed' not in rels
    assert 'effectiveDate' in rels
    assert 'ceased' in rels

    ceased_items = rels['ceased']['items']
    assert len(ceased_items) == 2

    first_liquidator = ceased_items[0]
    assert first_liquidator['entity']['familyName'] == 'Miller'
    assert first_liquidator['entity']['givenName'] == 'Phillip Tandy'

    assert 'mailingAddress' in first_liquidator
    assert 'deliveryAddress' in first_liquidator

    second_liquidator = ceased_items[1]
    assert second_liquidator['entity']['businessName'] == 'Test Business'

    effective_items = rels['effectiveDate']['items']
    existing_liquidator_found = any(
        item['entity'].get('givenName') == 'EXISTING LIQUIDATOR'
        for item in effective_items
    )
    assert existing_liquidator_found is True

def test_format_intent_liquidator_data(session):
    """Assert _format_liquidator_data correctly formats a intentToLiquidate filing."""
    business = factory_business(identifier='BC1234567', entity_type='BC')

    receiver = factory_party_role(
        delivery_address=factory_address('delivery street', 'delivery'),
        mailing_address=factory_address('mailing street', 'mailing'),
        appointment_date=datetime(2026, 5, 15, 10, 0, 0),
        cessation_date=None,
        officer={
            'firstName': 'first',
            'lastName': 'last',
            'middleInitial': 'mid',
            'partyType': 'person',
            'organizationName': ''
        },
        role_type=PartyRole.RoleTypes.RECEIVER
    )

    receiver.business_id = business.id
    session.add(receiver)
    session.commit()

    col = copy.deepcopy(CHANGE_OF_LIQUIDATORS)
    col['type'] = 'intentToLiquidate'

    current_filing_json = _get_col_filing_json(business, col)
    current_filing = factory_completed_filing(business, current_filing_json, filing_date=datetime(2026, 1, 2))

    report = Report(current_filing)
    report._business = business

    filing_data = current_filing_json['filing']
    report._format_liquidator_data(filing_data)

    assert filing_data['reportTitle'] == 'Statement of Intent to Liquidate'
    assert filing_data['reportDateAndTimeTitle'] == 'Summary Date and Time:'
    assert 'lastReportDate' not in filing_data
    assert filing_data['hasReceivers'] is True
    assert filing_data['hasPoa'] is False
    assert filing_data['courtOrderNumber'] is False

    rels = filing_data.get('relationships', {})
    assert 'appointed' in rels
    assert 'effectiveDate' not in rels
    assert 'ceased' not in rels

    appointed_items = rels['appointed']['items']
    assert len(appointed_items) == 2

    assert 'recordsOffice' in filing_data

def test_format_change_address_liquidator_data(session, mocker):
    """Assert _format_liquidator_data correctly formats a changeAddressLiquidator filing."""
    business = factory_business(identifier='BC1234567', entity_type='BC')
    _create_previous_liquidation_report(business)

    factory_business_office(business, "liquidationRecordsOffice")
    liquidator = factory_party_role(
        delivery_address=factory_address('delivery street', 'delivery'),
        mailing_address=factory_address('mailing street', 'mailing'),
        appointment_date=datetime(2024, 5, 15, 10, 0, 0),
        cessation_date=None,
        officer={
            'firstName': 'first',
            'lastName': 'last',
            'middleInitial': 'mid',
            'partyType': 'person',
            'organizationName': ''
        },
        role_type=PartyRole.RoleTypes.LIQUIDATOR
    )

    liquidator.business_id = business.id
    session.add(liquidator)
    session.commit()

    col = {
        'type': 'changeAddressLiquidator',
        'changeOfLiquidatorsDate': '2025-05-15',
        'relationships': [
            {
                'entity': {
                    'givenName': 'Phillip Tandy',
                    'familyName': 'Miller',
                    'alternateName': 'Phil Miller',
                    'identifier': f"{liquidator.id}"
                },
                'deliveryAddress': {
                    'streetAddress': 'CHANGED',
                    'addressCity': 'delivery_address city',
                    'addressCountry': 'CA',
                    'postalCode': 'H0H0H0',
                    'addressRegion': 'BC'
                },
                'mailingAddress': {
                    'streetAddress': 'CHANGED',
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
            'liquidationRecordsOffice': {
                'deliveryAddress': {
                    'streetAddress': 'CHANGED',
                    'addressCity': 'delivery_address city',
                    'addressCountry': 'CA',
                    'postalCode': 'H0H0H0',
                    'addressRegion': 'BC'
                },
                'mailingAddress': {
                    'streetAddress': 'CHANGED',
                    'addressCity': 'mailing_address city',
                    'addressCountry': 'CA',
                    'postalCode': 'H0H0H0',
                    'addressRegion': 'BC'
                }
            }
        }
    }

    mocker.patch('legal_api.services.VersionedBusinessDetailsService.get_office_revision', return_value={
        'liquidationRecordsOffice': {
            'deliveryAddress': {
                'streetAddress': 'OLD',
                'addressCity': 'delivery_address city',
                'addressCountry': 'CA',
                'postalCode': 'H0H0H0',
                'addressRegion': 'BC'
            },
            'mailingAddress': {
                'streetAddress': 'OLD',
                'addressCity': 'mailing_address city',
                'addressCountry': 'CA',
                'postalCode': 'H0H0H0',
                'addressRegion': 'BC'
            }
        }
    })
    mocker.patch('legal_api.services.VersionedBusinessDetailsService.get_party_revision', return_value=object())
    mocker.patch('legal_api.services.VersionedBusinessDetailsService.party_revision_json', return_value={
        'mailingAddress': {
            'streetAddress': 'Old Mailing Street',
            'addressCity': 'Victoria',
            'addressRegion': 'BC',
            'addressCountry': 'CA',
            'postalCode': 'V8W1P5'
        },
        'deliveryAddress': {
            'streetAddress': 'Old Delivery Street',
            'addressCity': 'Victoria',
            'addressRegion': 'BC',
            'addressCountry': 'CA',
            'postalCode': 'V8W1P4'
        }
    })

    current_filing_json = _get_col_filing_json(business, col)
    current_filing = factory_completed_filing(business, current_filing_json, filing_date=datetime(2026, 1, 2))

    report = Report(current_filing)
    report._business = business

    filing_data = current_filing_json['filing']
    report._format_liquidator_data(filing_data)

    assert filing_data['reportTitle'] == 'Liquidators Change of Address'
    assert filing_data['reportDateAndTimeTitle'] == 'Change Date and Time:'
    assert filing_data['lastReportDate'] == 'May 15, 2026'
    assert filing_data['hasReceivers'] is False
    assert filing_data['hasPoa'] is False
    assert filing_data['courtOrderNumber'] is False

    rels = filing_data.get('relationships', {})
    assert 'appointed' not in rels
    assert 'effectiveDate' in rels
    assert 'ceased' not in rels

    effective = rels['effectiveDate']['items']
    assert len(effective) == 1
    changed_rel = effective[0]
    assert changed_rel['mailingAddress']['changed'] is True
    assert changed_rel['deliveryAddress']['changed'] is True

    assert 'recordsOffice' in filing_data
    assert filing_data['recordsOffice']['mailingAddress']['changed'] is True
    assert filing_data['recordsOffice']['deliveryAddress']['changed'] is True

# ---------------------------------------------------------------------------
# Tests for Report._set_amalgamating_businesses
# ---------------------------------------------------------------------------

def _make_report_with_amalgamating_businesses(amalgamating_businesses_list, session,
                                               identifier='BC9900001', entity_type='BC'):
    """Return a Report instance whose filing_json contains the given amalgamatingBusinesses list."""
    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['header']['name'] = 'amalgamationApplication'
    filing_json['filing']['business']['identifier'] = identifier
    filing_json['filing']['business']['legalType'] = entity_type
    filing_json['filing']['amalgamationApplication'] = {
        'amalgamatingBusinesses': amalgamating_businesses_list,
        'type': 'regular',
        'courtApproval': False,
    }

    business = factory_business(identifier=identifier, entity_type=entity_type)
    filing = factory_completed_filing(business, filing_json)

    report = Report(filing)
    report._business = business
    report._report_key = 'amalgamationApplication'
    return report


@pytest.mark.parametrize(
    'test_name, foreign_jurisdiction, foreign_region, colin_status, colin_jurisdiction, expected_id, expected_jurisdiction',
    [
        ('expro-on', 'CA', 'BC', HTTPStatus.OK, 'ON', 'A1234567', 'Ontario'),
        ('expro-federal', 'CA', 'BC', HTTPStatus.OK, 'FD', 'A1234567', 'Federal'),
        ('a-prefix-colin-404', 'US', 'WA', HTTPStatus.NOT_FOUND, None, 'N/A', 'United States'),
    ],
    ids=[
        '_set_amalgamating_businesses: expro ON',
        '_set_amalgamating_businesses: expro FD federal',
        '_set_amalgamating_businesses: A-prefix colin 404 stays N/A',
    ]
)
def test_set_amalgamating_businesses_foreign(
        session, monkeypatch, test_name,
        foreign_jurisdiction, foreign_region,
        colin_status, colin_jurisdiction,
        expected_id, expected_jurisdiction):
    """Assert that _set_amalgamating_businesses correctly formats foreign and expro entries."""
    foreign_identifier = 'A1234567'
    foreign_name = 'Foreign Expro Corp'

    amalgamating_businesses = [
        {
            'identifier': foreign_identifier,
            'legalName': foreign_name,
            'foreignJurisdiction': {
                'country': foreign_jurisdiction,
                'region': foreign_region,
            },
        }
    ]

    report = _make_report_with_amalgamating_businesses(amalgamating_businesses, session)

    colin_call_count = {'count': 0}

    def mock_colin(id_):
        colin_call_count['count'] += 1
        resp = MagicMock()
        resp.status_code = colin_status
        resp.json.return_value = {'business': {'jurisdiction': colin_jurisdiction}}
        return resp

    monkeypatch.setattr(ColinService, 'query_business', mock_colin)

    filing = report._filing.filing_json['filing']
    report._set_amalgamating_businesses(filing)

    ting_businesses = filing.get('amalgamatingBusinesses', [])
    assert len(ting_businesses) == 1
    entry = ting_businesses[0]

    assert entry['legalName'] == foreign_name
    assert entry['identifier'] == expected_id
    assert entry['jurisdiction'] == expected_jurisdiction


def test_set_amalgamating_businesses_bc_domestic(session, monkeypatch):
    """Assert that _set_amalgamating_businesses correctly formats a domestic BC ting business."""
    bc_identifier = 'BC8887776'
    bc_legal_name = 'Ting Corp Ltd.'

    amalgamating_businesses = [
        {
            'identifier': bc_identifier,
            # No legalName key: domestic businesses trigger the ting_business path
        }
    ]

    report = _make_report_with_amalgamating_businesses(amalgamating_businesses, session)

    # Provide a mock ting_business from _get_versioned_amalgamating_business
    ting_mock = MagicMock()
    ting_mock._identifier = bc_identifier  # pylint: disable=protected-access
    ting_mock.legal_name = bc_legal_name
    report._get_versioned_amalgamating_business = lambda id_: ting_mock

    # COLIN must not be called for domestic businesses
    monkeypatch.setattr(ColinService, 'query_business',
                        lambda id_: (_ for _ in ()).throw(AssertionError('COLIN must not be called for domestic businesses')))

    filing = report._filing.filing_json['filing']
    report._set_amalgamating_businesses(filing)

    ting_businesses = filing.get('amalgamatingBusinesses', [])
    assert len(ting_businesses) == 1
    entry = ting_businesses[0]

    assert entry['legalName'] == bc_legal_name
    assert entry['identifier'] == bc_identifier
    assert entry['jurisdiction'] == 'British Columbia'


def test_set_amalgamating_businesses_foreign_non_a_prefix(session, monkeypatch):
    """Assert that a foreign business with a non-A identifier is not treated as expro and COLIN is not called."""
    foreign_identifier = 'UK9876543'
    foreign_name = 'UK Corp'

    amalgamating_businesses = [
        {
            'identifier': foreign_identifier,
            'legalName': foreign_name,
            'foreignJurisdiction': {'country': 'GB', 'region': None},
        }
    ]

    report = _make_report_with_amalgamating_businesses(amalgamating_businesses, session)

    colin_call_count = {'count': 0}

    def mock_colin_no_call(id_):
        colin_call_count['count'] += 1
        return MagicMock()

    monkeypatch.setattr(ColinService, 'query_business', mock_colin_no_call)

    filing = report._filing.filing_json['filing']
    report._set_amalgamating_businesses(filing)

    ting_businesses = filing.get('amalgamatingBusinesses', [])
    assert len(ting_businesses) == 1
    entry = ting_businesses[0]

    assert entry['identifier'] == 'N/A'
    assert entry['legalName'] == foreign_name
    assert entry['jurisdiction'] == 'United Kingdom'
    assert colin_call_count['count'] == 0


@pytest.mark.parametrize('filing_type,expected_report_type', [
    ('dissolution', 'FILING-2'),
    ('specialResolution', 'FILING'),
])
def test_special_resolution_drs_report_type(session, filing_type, expected_report_type):
    """Assert a special resolution accompanying another filing uses a distinct DRS report type (#34299).

    When stored with the same FILING report type as the filing's own report, the DRS-first lookup
    serves whichever of the two documents was stored first.
    """
    identifier = 'CP1234567'
    business = factory_business(identifier=identifier, entity_type='CP')

    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['header']['name'] = filing_type
    filing_json['filing']['business']['identifier'] = identifier
    filing_json['filing']['business']['legalType'] = 'CP'
    if filing_type == 'dissolution':
        filing_json['filing']['dissolution'] = copy.deepcopy(DISSOLUTION)
        filing_json['filing']['dissolution']['dissolutionType'] = 'voluntary'
    filing_json['filing']['specialResolution'] = copy.deepcopy(SPECIAL_RESOLUTION)
    filing = factory_completed_filing(business, filing_json)

    report = Report(filing)
    report._report_key = 'specialResolution'
    report._document_service = MagicMock()
    report._document_service.get_filing_report_by_filing_id.return_value = (b'pdf', HTTPStatus.OK)

    response = report._get_report()

    report._document_service.get_filing_report_by_filing_id.assert_called_once_with(
        identifier, filing.id, expected_report_type)
    assert response.status_code == HTTPStatus.OK
