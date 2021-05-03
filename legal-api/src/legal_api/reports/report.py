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
import re
from contextlib import suppress
from datetime import datetime
from http import HTTPStatus
from pathlib import Path

import pycountry
import requests
from flask import current_app, jsonify

from legal_api.models import Business, Filing
from legal_api.reports.registrar_meta import RegistrarInfo
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
        if self._report_key == 'correction':
            self._report_key = self._filing.filing_json['filing']['correction']['correctedFilingType']
        elif self._report_key == 'alteration':
            self._report_key = 'alterationNotice'
        if self._filing.business_id:
            self._business = Business.find_by_internal_id(self._filing.business_id)
            Report._populate_business_info_to_filing(self._filing, self._business)
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
        legal_entity_number = self._business.identifier if self._business else \
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
            'bc-annual-report/legalObligations',
            'bc-address-change/addresses',
            'bc-director-change/directors',
            'certificate-of-name-change/style',
            'common/certificateLogo',
            'common/certificateRegistrarSignature',
            'common/certificateSeal',
            'common/certificateStyle',
            'common/addresses',
            'common/shareStructure',
            'common/correctedOnCertificate',
            'common/style',
            'common/businessDetails',
            'common/directors',
            'incorporation-application/benefitCompanyStmt',
            'incorporation-application/completingParty',
            'incorporation-application/effectiveDate',
            'incorporation-application/incorporator',
            'incorporation-application/nameRequest',
            'common/benefitCompanyStmt',
            'notice-of-articles/directors',
            'notice-of-articles/restrictions',
            'common/resolutionDates',
            'alteration-notice/businessTypeChange',
            'common/effectiveDate',
            'common/legalNameChange',
            'common/nameTranslation',
            'alteration-notice/companyProvisions',
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
            if self._report_key == 'incorporationApplication':
                self._format_incorporation_data(filing)
            elif self._report_key == 'alterationNotice':
                self._format_alteration_data(filing)
            else:
                # set registered office address from either the COA filing or status quo data in AR filing
                with suppress(KeyError):
                    self._set_addresses(filing)
                # set director list from either the COD filing or status quo data in AR filing
                with suppress(KeyError):
                    self._set_directors(filing)

            if self._report_key == 'transition':
                self._format_transition_data(filing)

            # since we reset _report_key with correction type
            if filing['header']['name'] == 'correction':
                self._format_with_diff_data(filing)

            # name change from named company to numbered company case
            if self._report_key in ('certificateOfNameChange', 'alterationNotice') and 'nameRequest' in \
                    filing['alteration'] and 'legalName' not in filing['alteration']['nameRequest']:
                versioned_business = \
                    VersionedBusinessDetailsService.get_business_revision_after_filing(self._filing.id,
                                                                                       self._business.id)
                filing['alteration']['nameRequest']['legalName'] = versioned_business['legalName']

        filing['header']['reportType'] = self._report_key

        if (filing['header']['reportType'] == 'alterationNotice'
            and filing['previousLegalType'] != 'BEN'
            and filing['business']['legalType'] == 'BEN'
            ) or (
            filing['header']['reportType'] == 'noa'
            and filing['business']['legalType'] == 'BEN'
        ):
            filing['isBenefitCompanyStmt'] = True

        self._set_dates(filing)
        self._set_description(filing)
        self._set_tax_id(filing)
        self._set_meta_info(filing)
        self._set_registrar_info(filing)
        return filing

    def _set_registrar_info(self, filing):
        if filing.get('correction'):
            original_filing = Filing.find_by_id(filing.get('correction').get('correctedFilingId'))
            original_registrar = {**RegistrarInfo.get_registrar_info(original_filing.effective_date)}
            filing['registrarInfo'] = original_registrar
            current_registrar = {**RegistrarInfo.get_registrar_info(self._filing.effective_date)}
            if original_registrar['name'] != current_registrar['name']:
                filing['currentRegistrarInfo'] = current_registrar
        else:
            filing['registrarInfo'] = {**RegistrarInfo.get_registrar_info(self._filing.effective_date)}

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
        if filing.get('correction'):
            original_filing = Filing.find_by_id(filing.get('correction').get('correctedFilingId'))
            original_filing_datetime = LegislationDatetime.as_legislation_timezone(original_filing.filing_date)
            original_filing_hour = original_filing_datetime.strftime('%I').lstrip('0')
            filing['original_filing_date_time'] = original_filing_datetime. \
                strftime(f'%B %-d, %Y at {original_filing_hour}:%M %p Pacific Time')

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

    @staticmethod
    def _populate_business_info_to_filing(filing: Filing, business: Business):
        founding_datetime = LegislationDatetime.as_legislation_timezone(business.founding_date)
        hour = founding_datetime.strftime('%I')
        if filing.transaction_id:
            business_json = VersionedBusinessDetailsService.get_business_revision(filing.transaction_id, business)
        else:
            business_json = business.json()
        business_json['formatted_founding_date_time'] = \
            founding_datetime.strftime(f'%B %-d, %Y at {hour}:%M %p Pacific Time')
        business_json['formatted_founding_date'] = founding_datetime.strftime('%B %-d, %Y')
        filing.filing_json['filing']['business'] = business_json
        filing.filing_json['filing']['header']['filingId'] = filing.id

    def _format_transition_data(self, filing):
        filing.update(filing['transition'])
        self._format_directors(filing['parties'])
        if filing.get('shareStructure', {}).get('shareClasses', None):
            filing['shareClasses'] = filing['shareStructure']['shareClasses']

    def _format_incorporation_data(self, filing):
        self._format_address(filing['incorporationApplication']['offices']['registeredOffice']['deliveryAddress'])
        self._format_address(filing['incorporationApplication']['offices']['registeredOffice']['mailingAddress'])
        self._format_address(filing['incorporationApplication']['offices']['recordsOffice']['deliveryAddress'])
        self._format_address(filing['incorporationApplication']['offices']['recordsOffice']['mailingAddress'])
        self._format_directors(filing['incorporationApplication']['parties'])
        # create helper lists
        filing['listOfTranslations'] = filing['incorporationApplication'].get('nameTranslations', [])
        filing['offices'] = filing['incorporationApplication']['offices']
        filing['parties'] = filing['incorporationApplication']['parties']
        if filing['incorporationApplication'].get('shareClasses', None):
            filing['shareClasses'] = filing['incorporationApplication']['shareClasses']
        else:
            filing['shareClasses'] = filing['incorporationApplication']['shareStructure']['shareClasses']

    def _format_alteration_data(self, filing):
        # Get current list of translations in alteration. None if it is deletion
        if 'nameTranslations' in filing['alteration']:
            filing['listOfTranslations'] = filing['alteration'].get('nameTranslations', [])
            # Get previous translations for deleted translations. No record created in aliases version for deletions
            filing['previousNameTranslations'] = VersionedBusinessDetailsService.get_name_translations_before_revision(
                self._filing.transaction_id, self._business.id)
        if filing['alteration'].get('shareStructure', None):
            filing['shareClasses'] = filing['alteration']['shareStructure']['shareClasses']
            filing['resolutions'] = filing['alteration']['shareStructure'].get('resolutionDates', [])
        # Get previous business type
        versioned_business = VersionedBusinessDetailsService.get_business_revision_before_filing(
            self._filing.id, self._business.id)
        prev_legal_type = versioned_business['legalType']
        filing['previousLegalType'] = prev_legal_type
        with suppress(KeyError):
            filing['previousLegalTypeDescription'] = ReportMeta.entity_description[prev_legal_type]

    def _has_change(self, old_value, new_value):  # pylint: disable=no-self-use;
        """Check to fix the hole in diff.

        example:
            old_value: None and new_value: ''
            In reality there is no change but diff track it as a change
        """
        has_change = True  # assume that in all other cases diff has a valid change
        if isinstance(old_value, str) and new_value is None:
            has_change = old_value != ''
        elif isinstance(new_value, str) and old_value is None:
            has_change = new_value != ''
        elif isinstance(old_value, bool) and new_value is None:
            has_change = old_value is True
        elif isinstance(new_value, bool) and old_value is None:
            has_change = new_value is True

        return has_change

    def _format_with_diff_data(self, filing):
        if incorporation_application := filing['incorporationApplication']:
            diff = filing.get('correction', {}).get('diff', [])

            self._format_name_translations_with_diff_data(filing, diff)
            self._format_office_with_diff_data(incorporation_application, diff)
            self._format_party_with_diff_data(incorporation_application, diff)
            self._format_share_class_with_diff_data(incorporation_application, diff)

    def _format_name_translations_with_diff_data(self, filing, diff):  # pylint: disable=no-self-use;
        name_translations_path = '/filing/incorporationApplication/nameTranslations'
        name_translations = next((x for x in diff if x['path']
                                  .startswith(name_translations_path)
                                  and (x['path'].endswith('/name') or
                                       x['path'].endswith('/nameTranslations'))), None)
        filing['hasNameTranslationsCorrected'] = name_translations is not None

    def _format_office_with_diff_data(self, incorporation_application, diff):
        office_path = '/filing/incorporationApplication/offices/'
        reg_mailing_address = \
            next((x for x in diff if x['path']
                  .startswith(office_path + 'registeredOffice/mailingAddress/')
                  and self._has_change(x.get('oldValue'), x.get('newValue'))), None)
        reg_delivery_address = \
            next((x for x in diff if x['path']
                  .startswith(office_path + 'registeredOffice/deliveryAddress/')
                  and self._has_change(x.get('oldValue'), x.get('newValue'))), None)

        rec_mailing_address = \
            next((x for x in diff if x['path']
                  .startswith(office_path + 'recordsOffice/mailingAddress/')
                  and self._has_change(x.get('oldValue'), x.get('newValue'))), None)
        rec_delivery_address = \
            next((x for x in diff if x['path']
                  .startswith(office_path + 'recordsOffice/deliveryAddress/')
                  and self._has_change(x.get('oldValue'), x.get('newValue'))), None)

        offices = incorporation_application['offices']
        offices['registeredOffice']['mailingAddress']['hasCorrected'] = reg_mailing_address is not None
        offices['registeredOffice']['deliveryAddress']['hasCorrected'] = reg_delivery_address is not None
        offices['recordsOffice']['mailingAddress']['hasCorrected'] = rec_mailing_address is not None
        offices['recordsOffice']['deliveryAddress']['hasCorrected'] = rec_delivery_address is not None

    def _format_party_with_diff_data(self, incorporation_application, diff):
        party_path = '/filing/incorporationApplication/parties/'
        parties_corrected = \
            set([re.search(r'\/parties\/([\w\-]+)', x['path'])[1] for x in diff if  # pylint:disable=consider-using-set-comprehension; # noqa: E501;
                 x['path'].startswith(party_path)
                 and self._has_change(x.get('oldValue'), x.get('newValue'))])

        parties_removed = \
            [x for x in diff if x['path'] == party_path[:-1]  # remove last slash
             and not x.get('newValue') and x.get('oldValue')]

        parties = incorporation_application['parties']
        for party_id in parties_corrected:
            # x['officer']['id'] is required until #5302 ticket implements, change to x['id'] together with #5302
            if party := next((x for x in parties if x['officer']['id'] == party_id), None):
                party['hasCorrected'] = True

        for party_removed in parties_removed:
            party = party_removed.get('oldValue')
            party['hasRemoved'] = True
            parties.append(party)

    def _format_share_class_with_diff_data(self, incorporation_application, diff):  # pylint: disable=too-many-locals,no-self-use; # noqa: E501;
        share_classes_path = '/filing/incorporationApplication/shareStructure/shareClasses/'
        share_classes_corrected = \
            set([re.search(r'\/shareClasses\/([\w\-]+)', x['path'])[1] for x in diff if  # pylint:disable=consider-using-set-comprehension; # noqa: E501
                 x['path'].startswith(share_classes_path)
                 and '/series' not in x['path']
                 and self._has_change(x.get('oldValue'), x.get('newValue'))])
        share_classes_removed = \
            [x for x in diff if x['path'] == share_classes_path[:-1]  # remove last slash
             and not x.get('newValue') and x.get('oldValue')]

        share_classes = incorporation_application.get('shareStructure', {}).get('shareClasses', [])
        for share_class_id in share_classes_corrected:
            if share_class := next((x for x in share_classes if x['id'] == share_class_id), None):
                share_class['hasCorrected'] = True

        for share_class_removed in share_classes_removed:
            share_class = share_class_removed.get('oldValue')
            share_class['hasRemoved'] = True
            share_classes.append(share_class)

        self._format_share_series_with_diff_data(share_classes, share_classes_path, diff)

    def _format_share_series_with_diff_data(self, share_classes, share_classes_path, diff):  # pylint: disable=too-many-locals,no-self-use; # noqa: E501;
        share_series_corrected = \
            [re.search(r'\/shareClasses\/([\w\-]+)\/series\/([\w\-]+)', x['path']) for x in diff if
             x['path'].startswith(share_classes_path)
             and '/series/' in x['path']
             and (x['path'].endswith('/name') or
                  x['path'].endswith('/maxNumberOfShares') or
                  x['path'].endswith('/hasRightsOrRestrictions'))]
        share_series_removed = \
            [x for x in diff if
             x['path'].startswith(share_classes_path)
             and x['path'].endswith('/series')
             and not x.get('newValue') and x.get('oldValue')]

        for series_corrected in share_series_corrected:
            share_class_id = series_corrected[1]
            share_series_id = series_corrected[2]
            share_class = next((x for x in share_classes if x['id'] == share_class_id), {})
            if share_series := next((x for x in share_class.get('series', []) if x['id'] == share_series_id), None):
                share_series['hasCorrected'] = True

        for series_removed in share_series_removed:
            share_class_id = re.search(r'\/shareClasses\/([\w\-]+)', series_removed['path'])[1]
            if share_class := next((x for x in share_classes if x['id'] == share_class_id), None):
                share_series = series_removed.get('oldValue')
                share_series['hasRemoved'] = True
                if series := share_class.get('series', None):
                    series.append(share_series)
                else:
                    share_class['series'] = [share_series]

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
        'alterationNotice': {
            'filingDescription': 'Alteration Notice',
            'fileName': 'alterationNotice'
        },
        'transition': {
            'filingDescription': 'Transition Application',
            'fileName': 'transitionApplication'
        },
        'changeOfAddress': {
            'hasDifferentTemplates': True,
            'filingDescription': 'Change of Address',
            'BC': {
                'fileName': 'bcAddressChange'
            },
            'BEN': {
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
            'BEN': {
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
            'BEN': {
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
        },
        'certificateOfNameChange': {
            'filingDescription': 'Certificate of Name Change',
            'fileName': 'certificateOfNameChange'
        }
    }

    entity_description = {
        Business.LegalTypes.COOP.value: 'BC Cooperative Association',
        Business.LegalTypes.COMP.value: 'BC Company',
        Business.LegalTypes.BCOMP.value: 'BC Benefit Company',
    }
