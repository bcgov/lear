# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
# an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
"""Produces a PDF output based on templates and JSON messages."""
import base64
import copy
import json
import os
from contextlib import suppress
from datetime import datetime
from http import HTTPStatus
from pathlib import Path

import pycountry
import requests
from flask import current_app, jsonify

from legal_api.models import Business
from legal_api.services import VersionedBusinessDetailsService
from legal_api.utils.auth import jwt
from legal_api.utils.legislation_datetime import LegislationDatetime


class Report:  # pylint: disable=too-few-public-methods
    # TODO review pylint warning and alter as required
    """Service to create report outputs."""

    def __init__(self, filing):
        """Create the Report instance."""
        self._filing = filing
        self._business = None
        self._report_key = None

    def get_pdf(self, report_type=None):
        """Render a pdf for the report."""
        self._report_key = report_type if report_type else self._filing.filing_type
        if self._filing.business_id:
            self._business = Business.find_by_internal_id(self._filing.business_id)
        headers = {
            'Authorization': 'Bearer {}'.format(jwt.get_token_auth_header()),
            'Content-Type': 'application/json'
        }
        data = {
            'reportName': self._get_report_filename(),
            'template': "'" + base64.b64encode(bytes(self._get_template(), 'utf-8')).decode() + "'",
            'templateVars': self._get_template_data()
        }
        response = requests.post(url=current_app.config.get('REPORT_SVC_URL'), headers=headers, data=json.dumps(data))

        if response.status_code != HTTPStatus.OK:
            return jsonify(message=str(response.content)), response.status_code
        return response.content, response.status_code

    def _get_report_filename(self):
        filing_date = str(self._filing.filing_date)[:19]
        legal_entity_number = self._business.identifier if self._business else\
            self._filing.filing_json['filing']['business']['identifier']
        description = ReportMeta.reports[self._report_key]['filingDescription']
        return '{}_{}_{}.pdf'.format(legal_entity_number, filing_date, description).replace(' ', '_')

    def _get_template(self):
        try:
            template_path = current_app.config.get('REPORT_TEMPLATE_PATH')
            template_code = Path(f'{template_path}/{self._get_template_filename()}').read_text()
            # substitute template parts
            template_code = self._substitute_template_parts(template_code)
        except Exception as err:
            current_app.logger.error(err)
            raise err
        return template_code

    @staticmethod
    def _substitute_template_parts(template_code):
        """Substitute template parts in main template.

        Template parts are marked by [[partname.html]] in templates.

        This functionality is restricted by:
        - markup must be exactly [[partname.html]] and have no extra spaces around file name
        - template parts can only be one level deep, ie: this rudimentary framework does not handle nested template
        parts. There is no recursive search and replace.

        :param template_code: string
        :return: template_code string, modified.
        """
        template_path = current_app.config.get('REPORT_TEMPLATE_PATH')
        template_parts = [
            'bc-annual-report/businessDetails',
            'bc-annual-report/legalObligations',
            'bc-address-change/addresses',
            'bc-address-change/businessDetails',
            'bc-director-change/businessDetails',
            'bc-director-change/directors',
            'certificate-of-incorporation/logo',
            'certificate-of-incorporation/registrarSignature',
            'certificate-of-incorporation/seal',
            'certificate-of-incorporation/style',
            'common/addresses',
            'common/shareStructure',
            'common/style',
            'incorporation-application/benefitCompanyStmt',
            'incorporation-application/businessDetails',
            'incorporation-application/completingParty',
            'incorporation-application/directors',
            'incorporation-application/effectiveDate',
            'incorporation-application/incorporator',
            'incorporation-application/nameRequest',
            'notice-of-articles/benefitCompanyStmt',
            'notice-of-articles/businessDetails',
            'notice-of-articles/directors',
            'notice-of-articles/resolutionDates',
            'notice-of-articles/restrictions',
            'addresses',
            'certification',
            'directors',
            'dissolution',
            'footer',
            'legalNameChange',
            'logo',
            'macros',
            'resolution',
            'style'
        ]

        # substitute template parts - marked up by [[filename]]
        for template_part in template_parts:
            template_part_code = Path(f'{template_path}/template-parts/{template_part}.html').read_text()
            template_code = template_code.replace('[[{}.html]]'.format(template_part), template_part_code)

        return template_code

    def _get_template_filename(self):
        if ReportMeta.reports[self._report_key].get('hasDifferentTemplates', False):
            file_name = ReportMeta.reports[self._report_key][self._business.legal_type]['fileName']
        else:
            file_name = ReportMeta.reports[self._report_key]['fileName']
        return '{}.html'.format(file_name)

    def _get_template_data(self):  # pylint: disable=too-many-branches
        if self._report_key == 'noa':
            filing = VersionedBusinessDetailsService.get_company_details_revision(self._filing.id, self._business.id)
            self._format_noa_data(filing)
        else:
            filing = copy.deepcopy(self._filing.filing_json['filing'])
            filing['header']['filingId'] = self._filing.id
            if self._filing.filing_type == 'incorporationApplication':
                self._format_incorporation_data(filing)
            else:
                # set registered office address from either the COA filing or status quo data in AR filing
                with suppress(KeyError):
                    self._set_addresses(filing)
                # set director list from either the COD filing or status quo data in AR filing
                with suppress(KeyError):
                    self._set_directors(filing)

        self._set_dates(filing)
        self._set_description(filing)
        self._set_tax_id(filing)
        self._set_meta_info(filing)
        return filing

    def _set_tax_id(self, filing):
        if self._business:
            filing['taxId'] = self._business.tax_id

    def _set_description(self, filing):
        if self._business:
            filing['entityDescription'] = ReportMeta.entity_description[self._business.legal_type]

    def _set_dates(self, filing):
        # Filing Date
        filing_datetime = LegislationDatetime.as_legislation_timezone(self._filing.filing_date)
        hour = filing_datetime.strftime('%I').lstrip('0')
        filing['filing_date_time'] = filing_datetime.strftime(f'%B %-d, %Y at {hour}:%M %p Pacific Time')
        # Effective Date
        effective_date = filing_datetime if self._filing.effective_date is None \
            else LegislationDatetime.as_legislation_timezone(self._filing.effective_date)
        effective_hour = effective_date.strftime('%I').lstrip('0')
        filing['effective_date_time'] = effective_date.strftime(f'%B %-d, %Y at {effective_hour}:%M %p Pacific Time')
        filing['effective_date'] = effective_date.strftime('%B %-d, %Y')
        # Recognition Date
        if self._business:
            recognition_datetime = LegislationDatetime.as_legislation_timezone(self._business.founding_date)
            recognition_hour = recognition_datetime.strftime('%I').lstrip('0')
            filing['recognition_date_time'] = \
                recognition_datetime.strftime(f'%B %-d, %Y at {recognition_hour}:%M %p Pacific Time')
        # For Annual Report - Set AGM date as the effective date
        if self._filing.filing_type == 'annualReport':
            agm_date_str = filing.get('annualReport', {}).get('annualGeneralMeetingDate', None)
            if agm_date_str:
                agm_date = datetime.fromisoformat(agm_date_str)
                filing['agm_date'] = agm_date.strftime('%B %-d, %Y')
                # for AR, the effective date is the AGM date
                filing['effective_date'] = agm_date.strftime('%B %-d, %Y')
            else:
                filing['agm_date'] = 'No AGM'

    def _set_directors(self, filing):
        if filing.get('changeOfDirectors'):
            filing['listOfDirectors'] = filing['changeOfDirectors']
        else:
            filing['listOfDirectors'] = {
                'directors': filing['annualReport']['directors']
            }
        # create helper lists of appointed and ceased directors
        directors = self._format_directors(filing['listOfDirectors']['directors'])
        filing['listOfDirectors']['directorsAppointed'] = [el for el in directors if 'appointed' in el['actions']]
        filing['listOfDirectors']['directorsCeased'] = [el for el in directors if 'ceased' in el['actions']]

    def _format_directors(self, directors):
        for director in directors:
            with suppress(KeyError):
                self._format_address(director['deliveryAddress'])
                self._format_address(director['mailingAddress'])
        return directors

    def _set_addresses(self, filing):
        if filing.get('changeOfAddress'):
            if filing.get('changeOfAddress').get('offices'):
                filing['registeredOfficeAddress'] = filing['changeOfAddress']['offices']['registeredOffice']
                if filing['changeOfAddress']['offices'].get('recordsOffice', None):
                    filing['recordsOfficeAddress'] = filing['changeOfAddress']['offices']['recordsOffice']
                    filing['recordsOfficeAddress']['deliveryAddress'] = \
                        self._format_address(filing['recordsOfficeAddress']['deliveryAddress'])
                    filing['recordsOfficeAddress']['mailingAddress'] = \
                        self._format_address(filing['recordsOfficeAddress']['mailingAddress'])
            else:
                filing['registeredOfficeAddress'] = filing['changeOfAddress']
        else:
            if filing.get('annualReport', {}).get('deliveryAddress'):
                filing['registeredOfficeAddress'] = {
                    'deliveryAddress': filing['annualReport']['deliveryAddress'],
                    'mailingAddress': filing['annualReport']['mailingAddress']
                }
            else:
                filing['registeredOfficeAddress'] = {
                    'deliveryAddress': filing['annualReport']['offices']['registeredOffice']['deliveryAddress'],
                    'mailingAddress': filing['annualReport']['offices']['registeredOffice']['mailingAddress']
                }
        delivery_address = filing['registeredOfficeAddress']['deliveryAddress']
        mailing_address = filing['registeredOfficeAddress']['mailingAddress']
        filing['registeredOfficeAddress']['deliveryAddress'] = self._format_address(delivery_address)
        filing['registeredOfficeAddress']['mailingAddress'] = self._format_address(mailing_address)

    @staticmethod
    def _format_address(address):
        country = address['addressCountry']
        country = pycountry.countries.search_fuzzy(country)[0].name
        address['addressCountry'] = country
        return address

    def _format_incorporation_data(self, filing):
        self._format_address(filing['incorporationApplication']['offices']['registeredOffice']['deliveryAddress'])
        self._format_address(filing['incorporationApplication']['offices']['registeredOffice']['mailingAddress'])
        self._format_address(filing['incorporationApplication']['offices']['recordsOffice']['deliveryAddress'])
        self._format_address(filing['incorporationApplication']['offices']['recordsOffice']['mailingAddress'])
        self._format_directors(filing['incorporationApplication']['parties'])
        # create helper lists
        filing['listOfTranslations'] = filing['incorporationApplication'].get('nameTranslations', {})\
            .get('new', [])
        filing['offices'] = filing['incorporationApplication']['offices']
        filing['shareClasses'] = filing['incorporationApplication']['shareClasses']

    def _format_noa_data(self, filing):
        filing['header'] = {}
        filing['header']['filingId'] = self._filing.id

    def _set_meta_info(self, filing):
        filing['environment'] = f'{self._get_environment()} FILING #{self._filing.id}'.lstrip()
        # Get source
        filing['source'] = self._filing.source
        # Appears in the Description section of the PDF Document Properties as Title.
        filing['meta_title'] = '{} on {}'.format(
            self._filing.FILINGS[self._filing.filing_type]['title'], filing['filing_date_time'])

        # Appears in the Description section of the PDF Document Properties as Subject.
        if self._report_key == 'noa':
            filing['meta_subject'] = '{} ({})'.format(self._business.legal_name, self._business.identifier)
        else:
            legal_name = self._filing.filing_json['filing']['business'].get('legalName', 'NA')
            filing['meta_subject'] = '{} ({})'.format(
                legal_name,
                self._filing.filing_json['filing']['business']['identifier'])

    @staticmethod
    def _get_environment():
        namespace = os.getenv('POD_NAMESPACE', '').lower()
        if namespace.endswith('dev'):
            return 'DEV'
        if namespace.endswith('test'):
            return 'TEST'
        return ''


class ReportMeta:  # pylint: disable=too-few-public-methods
    """Helper class to maintain the report meta information."""

    reports = {
        'certificate': {
            'filingDescription': 'Certificate of Incorporation',
            'fileName': 'certificateOfIncorporation'
        },
        'incorporationApplication': {
            'filingDescription': 'Incorporation Application',
            'fileName': 'incorporationApplication'
        },
        'noa': {
            'filingDescription': 'Notice of Articles',
            'fileName': 'noticeOfArticles'
        },
        'changeOfAddress': {
            'hasDifferentTemplates': True,
            'filingDescription': 'Change of Address',
            'BC': {
                'fileName': 'bcAddressChange'
            },
            'CP': {
                'fileName': 'changeOfAddress'
            }
        },
        'changeOfDirectors': {
            'hasDifferentTemplates': True,
            'filingDescription': 'Change of Directors',
            'BC': {
                'fileName': 'bcDirectorChange'
            },
            'CP': {
                'fileName': 'changeOfDirectors'
            }
        },
        'annualReport': {
            'hasDifferentTemplates': True,
            'filingDescription': 'Annual Report',
            'BC': {
                'fileName': 'bcAnnualReport'
            },
            'CP': {
                'fileName': 'annualReport'
            }
        },
        'changeOfName': {
            'filingDescription': 'Change of Name',
            'fileName': 'changeOfName'
        },
        'specialResolution': {
            'filingDescription': 'Special Resolution',
            'fileName': 'specialResolution'
        },
        'voluntaryDissolution': {
            'filingDescription': 'Voluntary Dissolution',
            'fileName': 'voluntaryDissolution'
        }
    }

    entity_description = {
        'CP': 'cooperative',
        'BC': 'BC Benefit Company'
    }
