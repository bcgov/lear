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
from pathlib import Path
from unittest.mock import patch

import pytest
from flask import current_app
from registry_schemas.example_data import (
    ALTERATION_FILING_TEMPLATE,
    ANNUAL_REPORT,
    CHANGE_OF_ADDRESS,
    CHANGE_OF_DIRECTORS,
    CHANGE_OF_DIRECTORS_MAILING,
    CHANGE_OF_NAME,
    CORP_CHANGE_OF_ADDRESS,
    CORRECTION_COMBINED_AR,
    DISSOLUTION,
    FILING_HEADER,
    INCORPORATION_FILING_TEMPLATE,
    SPECIAL_RESOLUTION,
    TRANSITION_FILING_TEMPLATE,
)

from legal_api.models import db  # noqa:I001
from legal_api.models.db import versioning_manager
from legal_api.reports.report import Report  # noqa:I001
from legal_api.services import VersionedBusinessDetailsService  # noqa:I001
from tests.unit.models import factory_business, factory_completed_filing  # noqa:E501,I001


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
        filing_json['specialResolution'] = SPECIAL_RESOLUTION
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


def set_addresses(report):
    """Assert _set_addresses works as expected."""
    filing_json = report._filing.filing_json

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
        ('BEN CER', 'BC1234567', 'BEN', 'certificate', 'incorporationApplication', INCORPORATION_FILING_TEMPLATE),
        ('BEN TRANS', 'BC1234567', 'BEN', 'transition', 'transition', TRANSITION_FILING_TEMPLATE),
    ]
)
def test_get_pdf(session, test_name, identifier, entity_type, report_type, filing_type, template):
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
        set_addresses(report)

    if report._business.legal_type != 'CP':
        set_tax_id(report)

    filename = report._get_report_filename()
    assert filename
    template = report._get_template()
    assert template


def test_alteration_name_change(session):
    """Assert alteration name change filings can be returned as a PDF."""
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

    # new legal_name can be retrieved from the versioned business (numbered company case)
    business_revision = \
        VersionedBusinessDetailsService.get_business_revision_after_filing(numbered_company_filing.id, business.id)
    assert business_revision['legalName'] == numbered_company_name
    numbered_company_report = create_alteration_report(numbered_company_filing, business, report_type)
    numbered_company_filename = numbered_company_report._get_report_filename()
    assert numbered_company_filename
    numbered_company_template = numbered_company_report._get_template()
    assert numbered_company_template
    numbered_company_template_data = numbered_company_report._get_template_data()
    assert numbered_company_template_data['toLegalName'] == numbered_company_name


def update_business_legal_name(business, legal_name):
    """Update business legal name."""
    uow = versioning_manager.unit_of_work(db.session)
    uow.create_transaction(db.session)
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
