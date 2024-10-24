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
from typing import Final

import pycountry
import requests
from dateutil.relativedelta import relativedelta
from flask import current_app, jsonify

from legal_api.core.meta.filing import FILINGS
from legal_api.models import (
    AmalgamatingBusiness,
    Amalgamation,
    Business,
    ConsentContinuationOut,
    CorpType,
    Document,
    Filing,
    OfficeType,
    PartyRole,
)
from legal_api.models.business import ASSOCIATION_TYPE_DESC
from legal_api.reports.registrar_meta import RegistrarInfo
from legal_api.services import MinioService, VersionedBusinessDetailsService
from legal_api.utils.auth import jwt
from legal_api.utils.formatting import float_to_str
from legal_api.utils.legislation_datetime import LegislationDatetime


OUTPUT_DATE_FORMAT: Final = '%B %-d, %Y'


class Report:  # pylint: disable=too-few-public-methods, too-many-lines
    # TODO review pylint warning and alter as required
    """Service to create report outputs."""

    def __init__(self, filing):
        """Create the Report instance."""
        self._filing = filing
        self._business = None
        self._report_key = None
        self._report_date_time = LegislationDatetime.now()

    def get_pdf(self, report_type=None):
        """Render a pdf for the report."""
        self._report_key = report_type if report_type else self._filing.filing_type
        if self._report_key in ReportMeta.static_reports:
            return self._get_static_report()
        return self._get_report()

    def _get_static_report(self):
        document_type = ReportMeta.static_reports[self._report_key]['documentType']
        document: Document = self._filing.documents.filter(Document.type == document_type).first()
        response = MinioService.get_file(document.file_key)
        return current_app.response_class(
            response=response.data,
            status=response.status,
            mimetype='application/pdf'
        )

    def _get_report(self):
        if self._filing.business_id:
            self._business = Business.find_by_internal_id(self._filing.business_id)
            Report._populate_business_info_to_filing(self._filing, self._business)
        if self._report_key == 'alteration':
            self._report_key = 'alterationNotice'
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

        return current_app.response_class(
            response=response.content,
            status=response.status_code,
            mimetype='application/pdf'
        )

    def _get_report_filename(self):
        filing_date = str(self._filing.filing_date)[:19]
        legal_entity_number = self._business.identifier if self._business else \
            self._filing.filing_json['filing'].get('business', {}).get('identifier', '')
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
            'amalgamation/amalgamatingCorp',
            'amalgamation/amalgamationName',
            'amalgamation/amalgamationStmt',
            'amalgamation/approvalType',
            'amalgamation/effectiveDate',
            'bc-annual-report/legalObligations',
            'bc-address-change/addresses',
            'bc-director-change/directors',
            'common/certificateFooter',
            'common/certificateLogo',
            'common/certificateRegistrarSignature',
            'common/certificateSeal',
            'common/certificateStyle',
            'common/addresses',
            'common/shareStructure',
            'common/correctedOnCertificate',
            'common/style',
            'common/styleLetterOverride',
            'common/businessDetails',
            'common/footerMOCS',
            'common/directors',
            'continuation/authorization',
            'continuation/companyNameStmt',
            'continuation/effectiveDate',
            'continuation/exproRegistrationInBc',
            'continuation/foreignJurisdiction',
            'continuation/nameRequest',
            'common/completingParty',
            'correction/businessDetails',
            'correction/addresses',
            'correction/associateType',
            'correction/directors',
            'correction/legalNameChange',
            'correction/resolution',
            'correction/rulesMemorandum',
            'change-of-registration/legal-name',
            'change-of-registration/nature-of-business',
            'change-of-registration/addresses',
            'change-of-registration/proprietor',
            'change-of-registration/completingParty',
            'change-of-registration/partner',
            'incorporation-application/benefitCompanyStmt',
            'incorporation-application/completingParty',
            'incorporation-application/effectiveDate',
            'incorporation-application/incorporator',
            'incorporation-application/nameRequest',
            'incorporation-application/cooperativeAssociationType',
            'restoration-application/nameRequest',
            'restoration-application/legalName',
            'restoration-application/legalNameDissolution',
            'restoration-application/approvalType',
            'restoration-application/applicant',
            'restoration-application/expiry',
            'registration/nameRequest',
            'registration/addresses',
            'registration/completingParty',
            'registration/party',
            'registration-statement/party',
            'registration-statement/business-info',
            'registration-statement/completingParty',
            'common/statement',
            'common/benefitCompanyStmt',
            'dissolution/custodianOfRecords',
            'dissolution/dissolutionStatement',
            'dissolution/firmsDissolutionDate',
            'notice-of-articles/directors',
            'notice-of-articles/restrictions',
            'common/resolutionDates',
            'alteration-notice/businessTypeChange',
            'alteration-notice/legalNameChange',
            'alteration-notice/statement',
            'common/effectiveDate',
            'common/nameTranslation',
            'alteration-notice/companyProvisions',
            'special-resolution/resolution',
            'special-resolution/resolutionApplication',
            'addresses',
            'certification',
            'directors',
            'dissolution',
            'footer',
            'legalNameChange',
            'logo',
            'macros',
            'style'
        ]

        # substitute template parts - marked up by [[filename]]
        for template_part in template_parts:
            template_part_code = Path(f'{template_path}/template-parts/{template_part}.html').read_text()
            template_code = template_code.replace('[[{}.html]]'.format(template_part), template_part_code)

        return template_code

    def _get_template_filename(self):
        if ReportMeta.reports[self._report_key].get('hasDifferentTemplates', False):
            # Get template specific to legal type
            file_name = None
            specific_template = ReportMeta.reports[self._report_key].get(self._business.legal_type, None)
            if file_name is None:
                # Fallback to default if specific template not found
                file_name = specific_template['fileName'] if specific_template else \
                    ReportMeta.reports[self._report_key]['default']['fileName']
        else:
            file_name = ReportMeta.reports[self._report_key]['fileName']
        return '{}.html'.format(file_name)

    def _get_template_data(self):
        if self._report_key in ['noticeOfArticles', 'amendedRegistrationStatement', 'correctedRegistrationStatement']:
            filing = VersionedBusinessDetailsService.get_company_details_revision(self._filing.id, self._business.id)
            self._format_noa_data(filing)
        else:
            filing = copy.deepcopy(self._filing.filing_json['filing'])
            filing['header']['filingId'] = self._filing.id
            filing['header']['status'] = self._filing.status
            self._format_filing_json(filing)

        filing['header']['reportType'] = self._report_key

        self._format_par_value(filing)
        self._set_dates(filing)
        self._set_description(filing)
        self._set_tax_id(filing)
        self._set_meta_info(filing)
        self._set_registrar_info(filing)
        self._set_completing_party(filing)
        return filing

    def _format_par_value(self, filing):
        if share_classes := filing.get('shareClasses'):
            for share_class in share_classes:
                if (par_value := share_class.get('parValue')) and isinstance(par_value, float):
                    share_class['parValue'] = float_to_str(par_value)

    def _format_filing_json(self, filing):  # pylint: disable=too-many-branches, too-many-statements
        if self._report_key == 'incorporationApplication':
            self._format_incorporation_data(filing)
        elif self._report_key in ['specialResolution', 'specialResolutionApplication']:
            self._handle_special_resolution_filing_data(filing)
        elif self._report_key == 'alterationNotice':
            self._format_alteration_data(filing)
        elif self._report_key == 'registration':
            self._format_registration_data(filing)
        elif self._report_key == 'changeOfRegistration':
            self._format_change_of_registration_data(filing, 'changeOfRegistration')
        elif self._report_key in ['certificateOfNameChange', 'certificateOfNameCorrection']:
            self._format_name_change_data(filing)
        elif self._report_key == 'certificateOfRestoration':
            self._certificate_of_restorationformat__data(filing)
        elif self._report_key == 'restoration':
            self._format_restoration_data(filing)
        elif self._report_key == 'letterOfConsent':
            self._format_consent_continuation_out_data(filing)
        elif self._report_key == 'correction':
            self._format_correction_data(filing)
        elif self._report_key == 'transition':
            self._format_transition_data(filing)
        elif self._report_key == 'dissolution':
            self._format_dissolution_data(filing)
        elif self._report_key == 'letterOfAgmExtension':
            self._format_agm_extension_data(filing)
        elif self._report_key == 'letterOfAgmLocationChange':
            self._format_agm_location_change_data(filing)
        elif self._report_key == 'amalgamationApplication':
            self._format_amalgamation_data(filing)
        elif self._report_key == 'certificateOfAmalgamation':
            self._format_certificate_of_amalgamation_data(filing)
        elif self._report_key == 'continuationIn':
            self._format_continuation_in_data(filing)
        elif self._report_key == 'certificateOfContinuation':
            self._format_certificate_of_continuation_in_data(filing)
        else:
            # set registered office address from either the COA filing or status quo data in AR filing
            with suppress(KeyError):
                self._set_addresses(filing)
            # set director list from either the COD filing or status quo data in AR filing
            with suppress(KeyError):
                self._set_directors(filing)

    def _handle_special_resolution_filing_data(self, filing):
        """Handle special resolution (and correction), special resolution application (non correction)."""
        if self._report_key == 'specialResolution':
            self._format_special_resolution(filing)
        elif self._report_key == 'specialResolutionApplication':
            self._format_special_resolution_application(filing, 'alteration')

    def _set_completing_party(self, filing):
        completing_party_role = PartyRole.get_party_roles_by_filing(
            self._filing.id, datetime.utcnow(), PartyRole.RoleTypes.COMPLETING_PARTY.value)
        if completing_party_role:
            filing['completingParty'] = completing_party_role[0].party.json
            with suppress(KeyError):
                self._format_address(filing['completingParty']['deliveryAddress'])
            with suppress(KeyError):
                self._format_address(filing['completingParty']['mailingAddress'])

    def _set_registrar_info(self, filing):
        if filing.get('correction'):
            original_filing = Filing.find_by_id(filing.get('correction').get('correctedFilingId'))
            original_registrar = {**RegistrarInfo.get_registrar_info(original_filing.effective_date)}
            filing['registrarInfo'] = original_registrar
            current_registrar = {**RegistrarInfo.get_registrar_info(self._filing.effective_date)}
            if original_registrar['name'] != current_registrar['name']:
                filing['currentRegistrarInfo'] = current_registrar
        elif filing.get('annualReport'):
            # effective_date in annualReport will be ar_date or agm_date, which could be in past.
            filing['registrarInfo'] = {**RegistrarInfo.get_registrar_info(self._filing.filing_date)}
        else:
            filing['registrarInfo'] = {**RegistrarInfo.get_registrar_info(self._filing.effective_date)}

    def _set_tax_id(self, filing):
        if self._business and self._business.tax_id:
            filing['taxId'] = self._business.tax_id

    def _set_description(self, filing):
        legal_type = (self._filing.filing_json
                      .get('filing')
                      .get(self._filing.filing_type)
                      .get('nameRequest', {})
                      .get('legalType'))
        if not legal_type and self._business:
            legal_type = self._business.legal_type

        filing['numberedDescription'] = Business.BUSINESSES.get(legal_type, {}).get('numberedDescription')
        filing['numberedLegalNameSuffix'] = Business.BUSINESSES.get(legal_type, {}).get('numberedLegalNameSuffix')

        corp_type = CorpType.find_by_id(legal_type)
        filing['entityDescription'] = corp_type.full_desc

        act = {
            Business.LegalTypes.COOP.value: 'Cooperative Association Act',
            Business.LegalTypes.SOLE_PROP.value: 'Partnership Act',
            Business.LegalTypes.PARTNERSHIP.value: 'Partnership Act'
        }  # This could be the legislation column from CorpType. Yet to discuss.
        # BEN, BC, CC, ULC, CBEN, C, CCC, CUL: Business Corporations Act
        filing['entityAct'] = act.get(legal_type, 'Business Corporations Act')

    def _set_dates(self, filing):
        # Filing Date
        filing_datetime = LegislationDatetime.as_legislation_timezone(self._filing.filing_date)
        filing['filing_date_time'] = LegislationDatetime.format_as_report_string(filing_datetime)
        # Effective Date
        effective_date = filing_datetime if self._filing.effective_date is None \
            else LegislationDatetime.as_legislation_timezone(self._filing.effective_date)
        filing['effective_date_time'] = LegislationDatetime.format_as_report_string(effective_date)
        filing['effective_date'] = effective_date.strftime(OUTPUT_DATE_FORMAT)
        # Recognition Date
        if self._business:
            recognition_datetime = LegislationDatetime.as_legislation_timezone(self._business.founding_date)
            filing['recognition_date_time'] = LegislationDatetime.format_as_report_string(recognition_datetime)
            filing['recognition_date_utc'] = recognition_datetime.strftime(OUTPUT_DATE_FORMAT)
            if self._business.start_date:
                filing['start_date_utc'] = self._business.start_date.strftime(OUTPUT_DATE_FORMAT)
        # For Annual Report - Set AGM date as the effective date
        if self._filing.filing_type == 'annualReport':
            agm_date_str = filing.get('annualReport', {}).get('annualGeneralMeetingDate', None)
            if agm_date_str:
                agm_date = datetime.fromisoformat(agm_date_str)
                filing['agm_date'] = agm_date.strftime(OUTPUT_DATE_FORMAT)
                # for AR, the effective date is the AGM date
                filing['effective_date'] = agm_date.strftime(OUTPUT_DATE_FORMAT)
            else:
                filing['agm_date'] = 'No AGM'

        if filing.get('correction'):
            original_filing = Filing.find_by_id(filing.get('correction').get('correctedFilingId'))
            original_filing_datetime = LegislationDatetime.as_legislation_timezone(original_filing.filing_date)
            filing['original_filing_date_time'] = LegislationDatetime.format_as_report_string(original_filing_datetime)
        filing['report_date_time'] = LegislationDatetime.format_as_report_string(self._report_date_time)
        filing['report_date'] = self._report_date_time.strftime(OUTPUT_DATE_FORMAT)

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
            with suppress(KeyError):
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
        address['streetAddressAdditional'] = address.get('streetAddressAdditional') or ''
        address['addressRegion'] = address.get('addressRegion') or ''
        address['deliveryInstructions'] = address.get('deliveryInstructions') or ''

        country = address['addressCountry']
        country = pycountry.countries.search_fuzzy(country)[0].name
        address['addressCountry'] = country
        return address

    @staticmethod
    def _populate_business_info_to_filing(filing: Filing, business: Business):
        founding_datetime = LegislationDatetime.as_legislation_timezone(business.founding_date)
        if filing.transaction_id:
            business_json = VersionedBusinessDetailsService.get_business_revision(filing.transaction_id, business)
        else:
            business_json = business.json()
            business_json['legalName'] = business.legal_name  # legal name easy fix
        business_json['formatted_founding_date_time'] = LegislationDatetime.format_as_report_string(founding_datetime)
        business_json['formatted_founding_date'] = founding_datetime.strftime(OUTPUT_DATE_FORMAT)
        filing.filing_json['filing']['business'] = business_json
        filing.filing_json['filing']['header']['filingId'] = filing.id

    def _format_transition_data(self, filing):
        filing.update(filing['transition'])
        self._format_directors(filing['parties'])
        self._format_address(filing['offices']['registeredOffice']['deliveryAddress'])
        self._format_address(filing['offices']['registeredOffice']['mailingAddress'])
        if 'recordsOffice' in filing['offices']:
            self._format_address(filing['offices']['recordsOffice']['deliveryAddress'])
            self._format_address(filing['offices']['recordsOffice']['mailingAddress'])
        if filing.get('shareStructure', {}).get('shareClasses', None):
            filing['shareClasses'] = filing['shareStructure']['shareClasses']

    def _format_incorporation_data(self, filing):
        self._format_address(filing['incorporationApplication']['offices']['registeredOffice']['deliveryAddress'])
        self._format_address(filing['incorporationApplication']['offices']['registeredOffice']['mailingAddress'])
        if 'recordsOffice' in filing['incorporationApplication']['offices']:
            self._format_address(filing['incorporationApplication']['offices']['recordsOffice']['deliveryAddress'])
            self._format_address(filing['incorporationApplication']['offices']['recordsOffice']['mailingAddress'])
        self._format_directors(filing['incorporationApplication']['parties'])
        # create helper lists
        filing['nameRequest'] = filing['incorporationApplication'].get('nameRequest')
        filing['listOfTranslations'] = filing['incorporationApplication'].get('nameTranslations', [])
        filing['offices'] = filing['incorporationApplication']['offices']
        filing['parties'] = filing['incorporationApplication']['parties']
        if filing['incorporationApplication'].get('shareClasses', None):
            filing['shareClasses'] = filing['incorporationApplication']['shareClasses']
        elif 'shareStructure' in filing['incorporationApplication']:
            filing['shareClasses'] = filing['incorporationApplication']['shareStructure']['shareClasses']

        if cooperative := filing['incorporationApplication'].get('cooperative', None):
            cooperative['associationTypeName'] = \
                ASSOCIATION_TYPE_DESC.get(cooperative['cooperativeAssociationType'], '')

    def _set_party_name(self, parties):
        for party in parties:
            party['officer']['name'] = self._get_party_name(party)

    def _format_registration_data(self, filing):
        with suppress(KeyError):
            self._format_address(filing['registration']['offices']['businessOffice']['deliveryAddress'])
        with suppress(KeyError):
            self._format_address(filing['registration']['offices']['businessOffice']['mailingAddress'])
        self._format_directors(filing['registration']['parties'])
        self._set_party_name(filing['registration']['parties'])

        start_date = LegislationDatetime.as_legislation_timezone_from_date_str(filing['registration']['startDate'])
        filing['registration']['startDate'] = start_date.strftime(OUTPUT_DATE_FORMAT)

    def _format_name_change_data(self, filing):
        meta_data = self._filing.meta_data or {}
        from_legal_name = ''
        to_legal_name = ''
        if self._filing.filing_type == 'alteration':
            from_legal_name = meta_data.get('alteration', {}).get('fromLegalName')
            to_legal_name = meta_data.get('alteration', {}).get('toLegalName')
        if self._filing.filing_type == 'correction':
            from_legal_name = meta_data.get('correction', {}).get('fromLegalName')
            to_legal_name = meta_data.get('correction', {}).get('toLegalName')
            corrected_on = LegislationDatetime.as_legislation_timezone(self._filing.filing_date)
            filing['correctedOn'] = corrected_on.strftime(OUTPUT_DATE_FORMAT)
        if self._filing.filing_type == 'specialResolution' and 'changeOfName' in meta_data.get('legalFilings', []):
            from_legal_name = meta_data.get('changeOfName', {}).get('fromLegalName')
            to_legal_name = meta_data.get('changeOfName', {}).get('toLegalName')
        filing['fromLegalName'] = from_legal_name
        filing['toLegalName'] = to_legal_name

    def _format_certificate_of_restoration_data(self, filing):
        meta_data = self._filing.meta_data or {}
        filing['fromLegalName'] = meta_data.get('restoration', {}).get('fromLegalName')
        filing['toLegalName'] = meta_data.get('restoration', {}).get('toLegalName')
        if expiry_date_str := meta_data.get('restoration', {}).get('expiry'):
            expiry_date = LegislationDatetime.as_legislation_timezone_from_date_str(expiry_date_str)
            filing['restoration_expiry_date'] = expiry_date.strftime(OUTPUT_DATE_FORMAT)
        if self._filing.filing_sub_type == 'limitedRestorationToFull':
            business_previous_restoration_expiry = \
                VersionedBusinessDetailsService.find_last_value_from_business_revision(self._filing.transaction_id,
                                                                                       self._business.id,
                                                                                       is_restoration_expiry_date=True)
            restoration_expiry_datetime = LegislationDatetime.as_legislation_timezone(
                business_previous_restoration_expiry.restoration_expiry_date)
            filing['previous_restoration_expiry_date'] = restoration_expiry_datetime.strftime(OUTPUT_DATE_FORMAT)

        business_dissolution = VersionedBusinessDetailsService.find_last_value_from_business_revision(
            self._filing.transaction_id, self._business.id, is_dissolution_date=True)
        filing['formatted_dissolution_date'] = \
            LegislationDatetime.format_as_report_string(business_dissolution.dissolution_date)

    def _format_dissolution_data(self, filing):
        if self._business.legal_type in ['SP', 'GP'] and filing['dissolution']['dissolutionType'] == 'voluntary':
            filing['dissolution']['dissolution_date_str'] = LegislationDatetime. \
                as_legislation_timezone_from_date_str(filing['dissolution']['dissolutionDate']). \
                strftime(OUTPUT_DATE_FORMAT)
        self._format_directors(filing['dissolution']['parties'])
        filing['parties'] = filing['dissolution']['parties']

    def _format_restoration_data(self, filing):
        filing['nameRequest'] = filing['restoration'].get('nameRequest')
        filing['parties'] = filing['restoration'].get('parties')
        filing['offices'] = filing['restoration']['offices']
        meta_data = self._filing.meta_data or {}
        filing['fromLegalName'] = meta_data.get('restoration', {}).get('fromLegalName')

        if relationships := filing['restoration'].get('relationships'):
            filing['relationshipsDesc'] = ', '.join(relationships)

        approval_type = filing['restoration'].get('approvalType')
        filing['approvalType'] = approval_type
        if approval_type == 'courtOrder':
            filing['courtOrder'] = filing['restoration'].get('courtOrder')
        else:
            filing['applicationDate'] = filing['restoration'].get('applicationDate', 'Not Applicable')
            filing['noticeDate'] = filing['restoration'].get('noticeDate', 'Not Applicable')

        business_dissolution = VersionedBusinessDetailsService.find_last_value_from_business_revision(
            self._filing.transaction_id, self._business.id, is_dissolution_date=True)
        filing['dissolutionLegalName'] = business_dissolution.legal_name

        if expiry_date := meta_data.get('restoration', {}).get('expiry'):
            expiry_date = LegislationDatetime.as_legislation_timezone_from_date_str(expiry_date)
            expiry_date = expiry_date.replace(minute=1)
            filing['restoration_expiry_date'] = LegislationDatetime.format_as_report_string(expiry_date)

    def _format_consent_continuation_out_data(self, filing):
        cco = ConsentContinuationOut.get_by_filing_id(self._filing.id)

        country = pycountry.countries.get(alpha_2=cco.foreign_jurisdiction)
        region = None
        if cco.foreign_jurisdiction_region and cco.foreign_jurisdiction_region != 'FEDERAL':
            region = pycountry.subdivisions.\
                get(code=f'{cco.foreign_jurisdiction}-{cco.foreign_jurisdiction_region}')
        filing['jurisdiction'] = f'{region.name}, {country.name}' if region else country.name

        expiry_date = LegislationDatetime.as_legislation_timezone(cco.expiry_date)
        filing['cco_expiry_date'] = expiry_date.strftime(OUTPUT_DATE_FORMAT)

        filing['offices'] = VersionedBusinessDetailsService.\
            get_office_revision(self._filing.transaction_id, self._business.id)

        with suppress(KeyError):
            self._format_address(filing['offices']['registeredOffice']['deliveryAddress'])
        with suppress(KeyError):
            self._format_address(filing['offices']['registeredOffice']['mailingAddress'])

    def _format_agm_extension_data(self, filing):
        meta_data = self._filing.meta_data or {}
        is_first_agm = meta_data.get('agmExtension', {}).get('isFirstAgm', '')
        filing['is_first_agm'] = is_first_agm
        filing['agm_year'] = meta_data.get('agmExtension', {}).get('year', '')
        filing['is_final_agm'] = meta_data.get('agmExtension', {}).get('isFinalExtension', '')

        number_words = ['one', 'two', 'three', 'four', 'five', 'six']
        duration_numeric = meta_data.get('agmExtension', {}).get('extensionDuration', '')
        filing['duration_numeric'] = duration_numeric
        filing['duration_spelling'] = number_words[int(duration_numeric) - 1]

        if is_first_agm:
            founding_date_json = self._filing.filing_json['filing'].get('business', {}).get('foundingDate', '')
            founding_date = founding_date_json[0:10]
            original_date_time = LegislationDatetime.\
                as_legislation_timezone_from_date_str(founding_date) + relativedelta(months=18)
            filing['original_agm_date'] = original_date_time.strftime(OUTPUT_DATE_FORMAT)
        else:
            expire_date_current_string = meta_data.get('agmExtension', {}).get('expireDateCurrExt', '')
            date_current_obj = LegislationDatetime.as_legislation_timezone_from_date_str(expire_date_current_string)
            filing['original_agm_date'] = date_current_obj.strftime(OUTPUT_DATE_FORMAT)

        if expire_date_approved_string := meta_data.get('agmExtension', {}).get('expireDateApprovedExt', ''):
            date_approved_obj = LegislationDatetime.as_legislation_timezone_from_date_str(expire_date_approved_string)
            filing['extended_agm_date'] = date_approved_obj.strftime(OUTPUT_DATE_FORMAT)

        filing['offices'] = VersionedBusinessDetailsService.\
            get_office_revision(self._filing.transaction_id, self._business.id)
        with suppress(KeyError):
            self._format_address(filing['offices']['registeredOffice']['mailingAddress'])

    def _format_agm_location_change_data(self, filing):
        filing['agm_year'] = self._filing.filing_json['filing'].get('agmLocationChange', {}).get('year', '')

        filing['location'] = self._filing.filing_json['filing'].get('agmLocationChange', {}).get('agmLocation', '')

        filing['offices'] = VersionedBusinessDetailsService.\
            get_office_revision(self._filing.transaction_id, self._business.id)

        with suppress(KeyError):
            self._format_address(filing['offices']['registeredOffice']['mailingAddress'])

    def _format_alteration_data(self, filing):
        # Get current list of translations in alteration. None if it is deletion
        if 'nameTranslations' in filing['alteration']:
            filing['listOfTranslations'] = filing['alteration'].get('nameTranslations', [])
            # Get previous translations for deleted translations. No record created in aliases version for deletions
            filing['previousNameTranslations'] = VersionedBusinessDetailsService.get_name_translations_before_revision(
                self._filing.transaction_id, self._business.id)
        if filing['alteration'].get('shareStructure', None):
            filing['shareClasses'] = filing['alteration']['shareStructure'].get('shareClasses', [])
            filing['resolutions'] = filing['alteration']['shareStructure'].get('resolutionDates', [])

        to_legal_name = None
        if self._filing.status == 'COMPLETED':
            meta_data = self._filing.meta_data or {}
            prev_legal_type = meta_data.get('alteration', {}).get('fromLegalType')
            new_legal_type = meta_data.get('alteration', {}).get('toLegalType')
            prev_legal_name = meta_data.get('alteration', {}).get('fromLegalName')
            to_legal_name = meta_data.get('alteration', {}).get('toLegalName')
        else:
            prev_legal_type = filing.get('business').get('legalType')
            new_legal_type = filing.get('alteration').get('business').get('legalType')
            prev_legal_name = filing.get('business').get('legalName')
            identifier = filing.get('business').get('identifier')
            name_request_json = filing.get('alteration').get('nameRequest', {})
            if name_request_json and not (to_legal_name := name_request_json.get('legalName')):
                to_legal_name = Business.generate_numbered_legal_name(new_legal_type, identifier)

        if prev_legal_name and to_legal_name and prev_legal_name != to_legal_name:
            filing['previousLegalName'] = prev_legal_name
            filing['newLegalName'] = to_legal_name
        filing['nameRequest'] = filing.get('alteration').get('nameRequest', {})
        filing['provisionsRemoved'] = filing.get('alteration').get('provisionsRemoved')

        filing['previousLegalType'] = prev_legal_type
        filing['newLegalType'] = new_legal_type
        filing['previousLegalTypeDescription'] = self._get_legal_type_description(prev_legal_type)\
            if prev_legal_type else None
        filing['newLegalTypeDescription'] = self._get_legal_type_description(new_legal_type)\
            if new_legal_type else None

    def _format_amalgamation_data(self, filing):
        amalgamation = filing['amalgamationApplication']

        filing['nameRequest'] = amalgamation.get('nameRequest', {})
        filing['listOfTranslations'] = amalgamation.get('nameTranslations', [])
        filing['contactPoint'] = amalgamation.get('contactPoint', {})
        filing['courtApproval'] = amalgamation.get('courtApproval')
        filing['incorporationAgreement'] = amalgamation.get('incorporationAgreement', {})

        self._set_amalgamating_businesses(filing)
        if amalgamation['type'] in [Amalgamation.AmalgamationTypes.horizontal.name,
                                    Amalgamation.AmalgamationTypes.vertical.name]:
            self._set_from_primary_or_holding_business_data(filing)
        else:
            filing['offices'] = amalgamation.get('offices', {})
            filing['parties'] = amalgamation['parties']
            filing['shareClasses'] = amalgamation.get('shareStructure', {}).get('shareClasses', [])

        # Formatting addresses for registered and records office
        self._format_address(filing['offices']['registeredOffice']['deliveryAddress'])
        self._format_address(filing['offices']['registeredOffice']['mailingAddress'])
        if 'recordsOffice' in filing['offices']:
            self._format_address(filing['offices']['recordsOffice']['deliveryAddress'])
            self._format_address(filing['offices']['recordsOffice']['mailingAddress'])

        # Formatting parties
        self._format_directors(filing['parties'])

    def _format_certificate_of_amalgamation_data(self, filing):
        self._set_amalgamating_businesses(filing)

    def _set_amalgamating_businesses(self, filing):
        amalgamating_businesses = []
        business_legal_name = None
        for amalgamating_business in filing['amalgamationApplication']['amalgamatingBusinesses']:
            identifier = amalgamating_business.get('identifier')
            if foreign_legal_name := amalgamating_business.get('legalName'):
                business_legal_name = foreign_legal_name
            elif ting_business := self._get_versioned_amalgamating_business(identifier):
                business_legal_name = ting_business.legal_name

            amalgamating_businesses.append({
                'legalName': business_legal_name,
                'identifier': identifier
            })
        filing['amalgamatingBusinesses'] = amalgamating_businesses

    def _get_versioned_amalgamating_business(self, identifier):
        # until TED business is created, get it from business table
        ting_business = Business.find_by_identifier(identifier)
        if self._filing.transaction_id:
            # get TING business from version
            # when TED is dissolved by staff (with court order) and TING is restored, user can modify TING data
            # which should not be reflected here
            ting_business = VersionedBusinessDetailsService.get_business_revision_obj(
                self._filing.transaction_id, ting_business.id)
        return ting_business

    def _set_from_primary_or_holding_business_data(self, filing):  # pylint: disable=too-many-locals, too-many-branches
        ting_business = next(x for x in filing['amalgamationApplication']['amalgamatingBusinesses']
                             if x['role'] in [AmalgamatingBusiness.Role.holding.name,
                                              AmalgamatingBusiness.Role.primary.name])
        primary_or_holding_business = self._get_versioned_amalgamating_business(ting_business['identifier'])
        filing['nameRequest']['legalName'] = primary_or_holding_business.legal_name

        parties = []
        # copy director
        if self._filing.transaction_id:
            parties_version = VersionedBusinessDetailsService.get_party_role_revision(
                self._filing.transaction_id,
                primary_or_holding_business.id,
                role=PartyRole.RoleTypes.DIRECTOR.value)
            for director_json in parties_version:
                director_json['roles'] = [{'roleType': 'Director'}]
                parties.append(director_json)
        else:
            active_directors = PartyRole.get_active_directors(primary_or_holding_business.id,
                                                              self._filing.effective_date.date())
            for director in active_directors:
                director_json = director.json
                director_json['roles'] = [{'roleType': 'Director'}]
                parties.append(director_json)

        # copy completing party from filing json
        for party_info in filing['amalgamationApplication'].get('parties'):
            if comp_party_role := next((x for x in party_info.get('roles')
                                        if x['roleType'].lower() == 'completing party'), None):
                party_info['roles'] = [comp_party_role]  # override roles to have only completing party
                parties.append(party_info)
                break
        filing['parties'] = parties

        # copy offices
        offices = {}
        if self._filing.transaction_id:
            offices = VersionedBusinessDetailsService.get_office_revision(
                self._filing.transaction_id,
                primary_or_holding_business.id)
        else:
            officelist = primary_or_holding_business.offices.all()
            for i in officelist:
                if i.office_type in [OfficeType.REGISTERED, OfficeType.RECORDS]:
                    offices[i.office_type] = {}
                    for address in i.addresses:
                        offices[i.office_type][f'{address.address_type}Address'] = address.json
        filing['offices'] = offices

        # copy shares
        share_classes = []
        if self._filing.transaction_id:
            share_classes = VersionedBusinessDetailsService.get_share_class_revision(
                self._filing.transaction_id,
                primary_or_holding_business.id)
        else:
            for share_class in primary_or_holding_business.share_classes.all():
                share_classes.append(share_class.json)
        filing['shareClasses'] = share_classes

        # copy resolution dates
        resolutions = []
        if self._filing.transaction_id:
            resolutions = VersionedBusinessDetailsService.get_resolution_dates_revision(
                self._filing.transaction_id,
                primary_or_holding_business.id)
        else:
            for resolution in primary_or_holding_business.resolutions.all():
                resolutions.append({'date': resolution.resolution_date.strftime(OUTPUT_DATE_FORMAT)})
        filing['resolutions'] = resolutions

    def _format_change_of_registration_data(self, filing, filing_type):  # noqa: E501 # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        prev_completed_filing = Filing.get_previous_completed_filing(self._filing)
        versioned_business = VersionedBusinessDetailsService.\
            get_business_revision_obj(prev_completed_filing.transaction_id, self._business.id)

        # Change of Name
        prev_legal_name = versioned_business.legal_name
        name_request_json = filing.get(filing_type).get('nameRequest')
        filing['nameRequest'] = name_request_json
        if name_request_json:
            to_legal_name = name_request_json.get('legalName')
            if prev_legal_name and to_legal_name and prev_legal_name != to_legal_name:
                filing['previousLegalName'] = prev_legal_name
                filing['newLegalName'] = to_legal_name

        # Change of Nature of Business
        prev_naics_description = versioned_business.naics_description
        naics_json = filing.get(filing_type).get('business', {}).get('naics')
        if naics_json:
            to_naics_description = naics_json.get('naicsDescription')
            if prev_naics_description and to_naics_description and prev_naics_description != to_naics_description:
                filing['newNaicsDescription'] = to_naics_description

        # Change of start date
        if filing_type == 'correction':
            prev_start_date = versioned_business.start_date
            new_start_date_str = filing.get(filing_type).get('startDate')
            if new_start_date_str != LegislationDatetime.format_as_legislation_date(prev_start_date):
                filing['newStartDate'] = new_start_date_str

        # Change of Address
        if business_office := filing.get(filing_type).get('offices', {}).get('businessOffice'):
            filing['offices'] = {}
            filing['offices']['businessOffice'] = business_office
            offices_json = VersionedBusinessDetailsService.get_office_revision(
                prev_completed_filing.transaction_id,
                self._filing.business_id)
            filing['offices']['businessOffice']['mailingAddress']['changed'] = \
                self._compare_address(business_office.get('mailingAddress'),
                                      offices_json['businessOffice']['mailingAddress'])
            filing['offices']['businessOffice']['deliveryAddress']['changed'] = \
                self._compare_address(business_office.get('deliveryAddress'),
                                      offices_json['businessOffice']['deliveryAddress'])
            filing['offices']['businessOffice']['changed'] = \
                filing['offices']['businessOffice']['mailingAddress']['changed']\
                or filing['offices']['businessOffice']['deliveryAddress']['changed']
            with suppress(KeyError):
                self._format_address(filing[filing_type]['offices']['businessOffice']['deliveryAddress'])
            with suppress(KeyError):
                self._format_address(filing[filing_type]['offices']['businessOffice']['mailingAddress'])

        # Change of party
        if filing.get(filing_type).get('parties'):
            filing['parties'] = filing.get(filing_type).get('parties')
            self._format_directors(filing['parties'])
            filing['partyChange'] = False
            filing['newParties'] = []
            parties_to_edit = []
            for party in filing.get('parties'):
                if party['officer'].get('id'):
                    parties_to_edit.append(str(party['officer'].get('id')))
                    prev_party =\
                        VersionedBusinessDetailsService.get_party_revision(
                            prev_completed_filing.transaction_id, party['officer'].get('id'))
                    prev_party_json = VersionedBusinessDetailsService.party_revision_json(
                        prev_completed_filing.transaction_id, prev_party, True)
                    if self._has_party_name_change(prev_party_json, party):
                        party['nameChanged'] = True
                        party['previousName'] = self._get_party_name(prev_party_json)
                        filing['partyChange'] = True
                    if self._compare_address(party.get('mailingAddress'), prev_party_json.get('mailingAddress')):
                        party['mailingAddress']['changed'] = True
                        filing['partyChange'] = True
                    if self._compare_address(party.get('deliveryAddress'), prev_party_json.get('deliveryAddress')):
                        party['deliveryAddress']['changed'] = True
                        filing['partyChange'] = True
                else:
                    if [role for role in party.get('roles', []) if role['roleType'].lower() in ['partner']]:
                        filing['newParties'].append(party)

            existing_party_json = VersionedBusinessDetailsService.get_party_role_revision(
                prev_completed_filing.transaction_id, self._business.id, True)
            parties_deleted = [p for p in existing_party_json if p['officer']['id'] not in parties_to_edit]
            filing['ceasedParties'] = parties_deleted

    def _format_certificate_of_continuation_in_data(self, filing):
        continuation_in = self._filing.meta_data.get('continuationIn')
        country_code = continuation_in['country']
        region_code = continuation_in['region']

        country = pycountry.countries.get(alpha_2=country_code)
        region = None
        if region_code and region_code.upper() != 'FEDERAL':
            region = pycountry.subdivisions.get(code=f'{country_code}-{region_code}')
        filing['jurisdiction'] = f'{region.name}, {country.name}' if region else country.name

    def _format_continuation_in_data(self, filing):
        self._format_address(filing['continuationIn']['offices']['registeredOffice']['deliveryAddress'])
        self._format_address(filing['continuationIn']['offices']['registeredOffice']['mailingAddress'])
        if 'recordsOffice' in filing['continuationIn']['offices']:
            self._format_address(filing['continuationIn']['offices']['recordsOffice']['deliveryAddress'])
            self._format_address(filing['continuationIn']['offices']['recordsOffice']['mailingAddress'])
        self._format_directors(filing['continuationIn']['parties'])
        # create helper lists
        filing['nameRequest'] = filing['continuationIn'].get('nameRequest')
        filing['listOfTranslations'] = filing['continuationIn'].get('nameTranslations', [])
        filing['offices'] = filing['continuationIn']['offices']
        filing['parties'] = filing['continuationIn']['parties']
        if filing['continuationIn'].get('shareClasses', None):
            filing['shareClasses'] = filing['continuationIn']['shareClasses']
        elif 'shareStructure' in filing['continuationIn']:
            filing['shareClasses'] = filing['continuationIn']['shareStructure']['shareClasses']

        # set expro business
        if filing['continuationIn'].get('business'):
            filing['exproBusiness'] = filing['continuationIn']['business']
            # format founding date
            founding_date_str = filing['exproBusiness']['foundingDate']
            founding_date_datetime = datetime.fromisoformat(founding_date_str)
            founding_date = LegislationDatetime.as_legislation_timezone(founding_date_datetime)
            filing['exproBusiness']['formattedFoundingDate'] = founding_date.strftime(OUTPUT_DATE_FORMAT)

        filing['authorization'] = filing['continuationIn'].get('authorization')
        filing['foreignJurisdiction'] = filing['continuationIn'].get('foreignJurisdiction')

        # set foreign jurisdiction region and country name
        foreign_jurisdiction = filing['continuationIn'].get('foreignJurisdiction')
        region_code = None
        if filing.get('continuationIn').get('foreignJurisdiction').get('region'):
            region_code = foreign_jurisdiction['region']
        country_code = foreign_jurisdiction['country']
        country = pycountry.countries.get(alpha_2=country_code)
        region = None
        if region_code and region_code.upper() != 'FEDERAL':
            region = pycountry.subdivisions.get(code=f'{country_code}-{region_code}')
            filing['foreignJurisdiction']['region'] = region.name if region_code else ''
        filing['foreignJurisdiction']['country'] = country.name

        # format incorporation date
        incorp_date = \
            LegislationDatetime.as_legislation_timezone_from_date_str(foreign_jurisdiction.get('incorporationDate'))
        filing['foreignJurisdiction']['incorporationDate'] = incorp_date.strftime(OUTPUT_DATE_FORMAT)

    @staticmethod
    def _get_party_name(party_json):
        party_name = ''
        if party_json.get('officer').get('partyType') == 'person':
            last_name = party_json['officer'].get('lastName')
            first_name = party_json['officer'].get('firstName', '')
            middle_name = party_json['officer'].get('middleName', party_json['officer'].get('middleInitial', ''))
            if not middle_name and not first_name:
                party_name = f'{last_name}'
            else:
                party_name = f'{last_name}, {first_name} {middle_name}'
        elif party_json.get('officer').get('partyType') == 'organization':
            party_name = party_json['officer'].get('organizationName')
        return party_name

    @staticmethod
    def _has_party_name_change(prev_party_json, current_party_json):
        changed = False
        middle_name = current_party_json['officer'].get('middleName', current_party_json['officer'].
                                                        get('middleInitial', ''))
        if current_party_json.get('officer').get('partyType') == 'person':
            if prev_party_json['officer'].get('firstName').upper() != current_party_json['officer'].get('firstName').\
                    upper() or prev_party_json['officer'].get('middleName', '').upper() != \
                    middle_name.upper() or prev_party_json['officer'].get('lastName').upper() != \
                    current_party_json['officer'].get('lastName').upper():
                changed = True
        elif current_party_json.get('officer').get('partyType') == 'organization':
            if prev_party_json['officer'].get('organizationName').upper() != \
                    current_party_json['officer'].get('organizationName').upper():
                changed = True
        return changed

    @staticmethod
    def _compare_address(new_address, existing_address):
        if not new_address and not existing_address:
            return False
        if new_address and not existing_address:
            return True

        changed = False
        excluded_keys = ['addressCountryDescription', 'addressType', 'addressCountry']
        for key in existing_address:
            if key not in excluded_keys:
                if (new_address.get(key, '') or '') != (existing_address.get(key) or ''):
                    changed = True
        return changed

    @staticmethod
    def _get_legal_type_description(legal_type):
        corp_type = CorpType.find_by_id(legal_type)
        return corp_type.full_desc if corp_type else None

    def _has_change(self, old_value, new_value):
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

    def _format_correction_data(self, filing):
        if self._business.legal_type in ['SP', 'GP']:
            self._format_change_of_registration_data(filing, 'correction')
        else:
            prev_completed_filing = Filing.get_previous_completed_filing(self._filing)
            versioned_business = VersionedBusinessDetailsService.\
                get_business_revision_obj(prev_completed_filing.transaction_id, self._business.id)

            self._format_name_request_data(filing, versioned_business)
            self._format_name_translations_data(filing, prev_completed_filing)
            self._format_office_data(filing, prev_completed_filing)
            self._format_party_data(filing, prev_completed_filing)
            self._format_share_class_data(filing, prev_completed_filing)
            self._format_resolution_data(filing)

    def _format_name_request_data(self, filing, versioned_business: Business):
        name_request_json = filing.get('correction').get('nameRequest', {})
        filing['nameRequest'] = name_request_json
        prev_legal_name = versioned_business.legal_name

        if name_request_json and not (new_legal_name := name_request_json.get('legalName')):
            new_legal_name = Business.generate_numbered_legal_name(name_request_json['legalType'],
                                                                   versioned_business.identifier)

        if new_legal_name and prev_legal_name != new_legal_name:
            filing['previousLegalName'] = prev_legal_name
            filing['newLegalName'] = new_legal_name

    def _format_name_translations_data(self, filing, prev_completed_filing: Filing):
        filing['listOfTranslations'] = filing['correction'].get('nameTranslations', [])
        versioned_name_translations = VersionedBusinessDetailsService.\
            get_name_translations_revision(prev_completed_filing.transaction_id, self._business.id)
        filing['previousNameTranslations'] = versioned_name_translations
        filing['nameTranslationsChange'] = \
            sorted([translation['name'] for translation in filing['listOfTranslations']]) != \
            sorted([translation['name'] for translation in versioned_name_translations])

    def _format_office_data(self, filing, prev_completed_filing: Filing):
        filing['offices'] = {}
        if offices := filing.get('correction').get('offices'):
            offices_json = VersionedBusinessDetailsService.get_office_revision(prev_completed_filing.transaction_id,
                                                                               self._filing.business_id)
            if registered_office := offices.get('registeredOffice'):
                filing['offices']['registeredOffice'] = registered_office
                filing['offices']['registeredOffice']['mailingAddress']['changed'] = \
                    self._compare_address(registered_office.get('mailingAddress'),
                                          offices_json['registeredOffice']['mailingAddress'])
                filing['offices']['registeredOffice']['deliveryAddress']['changed'] = \
                    self._compare_address(registered_office.get('deliveryAddress'),
                                          offices_json['registeredOffice']['deliveryAddress'])
                filing['offices']['registeredOffice']['changed'] = \
                    filing['offices']['registeredOffice']['mailingAddress']['changed'] \
                    or filing['offices']['registeredOffice']['deliveryAddress']['changed']
                with suppress(KeyError):
                    self._format_address(filing['offices']['registeredOffice']['deliveryAddress'])
                with suppress(KeyError):
                    self._format_address(filing['offices']['registeredOffice']['mailingAddress'])

            if records_office := offices.get('recordsOffice'):
                filing['offices']['recordsOffice'] = records_office
                filing['offices']['recordsOffice']['mailingAddress']['changed'] = \
                    self._compare_address(records_office.get('mailingAddress'),
                                          offices_json['recordsOffice']['mailingAddress'])
                filing['offices']['recordsOffice']['deliveryAddress']['changed'] = \
                    self._compare_address(records_office.get('deliveryAddress'),
                                          offices_json['recordsOffice']['deliveryAddress'])
                filing['offices']['recordsOffice']['changed'] = \
                    filing['offices']['recordsOffice']['mailingAddress']['changed'] \
                    or filing['offices']['recordsOffice']['deliveryAddress']['changed']
                with suppress(KeyError):
                    self._format_address(filing['offices']['recordsOffice']['deliveryAddress'])
                with suppress(KeyError):
                    self._format_address(filing['offices']['recordsOffice']['mailingAddress'])

    def _format_party_data(self, filing, prev_completed_filing: Filing):
        filing['parties'] = filing.get('correction').get('parties', [])
        if filing.get('parties'):
            self._format_directors(filing['parties'])
            filing['partyChange'] = False
            filing['newParties'] = []
            parties_to_edit = []
            for party in filing.get('parties'):
                if party_id := party['officer'].get('id'):
                    parties_to_edit.append(str(party_id))
                    prev_party =\
                        VersionedBusinessDetailsService.get_party_revision(
                            prev_completed_filing.transaction_id, party_id)
                    prev_party_json = VersionedBusinessDetailsService.party_revision_json(
                        prev_completed_filing.transaction_id, prev_party, True)
                    if self._has_party_name_change(prev_party_json, party):
                        party['nameChanged'] = True
                        party['previousName'] = self._get_party_name(prev_party_json)
                        filing['partyChange'] = True
                    if self._compare_address(party.get('mailingAddress'), prev_party_json.get('mailingAddress')):
                        party['mailingAddress']['changed'] = True
                        filing['partyChange'] = True
                    if self._compare_address(party.get('deliveryAddress'), prev_party_json.get('deliveryAddress')):
                        party['deliveryAddress']['changed'] = True
                        filing['partyChange'] = True
                else:
                    if [role for role in party.get('roles', []) if role['roleType'].lower() in ['director']]:
                        filing['newParties'].append(party)

            existing_party_json = VersionedBusinessDetailsService.get_party_role_revision(
                prev_completed_filing.transaction_id, self._business.id, True)
            parties_deleted = [p for p in existing_party_json if p['officer']['id'] not in parties_to_edit]
            filing['ceasedParties'] = parties_deleted

    def _format_share_class_data(self, filing, prev_completed_filing: Filing):  # pylint: disable=too-many-locals; # noqa: E501;
        filing['shareClasses'] = filing.get('correction').get('shareStructure', {}).get('shareClasses')
        filing['resolutions'] = filing.get('correction').get('shareStructure', {}).get('resolutionDates', [])
        filing['newShareClasses'] = []
        if filing.get('shareClasses'):
            prev_share_class_json = VersionedBusinessDetailsService.get_share_class_revision(
                prev_completed_filing.transaction_id,
                prev_completed_filing.business_id)
            prev_share_class_ids = [x['id'] for x in prev_share_class_json]

            share_class_to_edit = []
            for share_class in filing.get('shareClasses'):
                if share_class_id := share_class.get('id'):
                    if (share_class_id := str(share_class_id)) in prev_share_class_ids:
                        share_class_to_edit.append(share_class_id)
                        if self._compare_json(share_class,
                                              next((x for x in prev_share_class_json if x['id'] == share_class_id)),
                                              ['id', 'series', 'type']):
                            share_class['changed'] = True
                            filing['shareClassesChange'] = True

                        self._format_share_series_data(share_class, filing, prev_completed_filing)
                    else:
                        del share_class['id']
                        filing['newShareClasses'].append(share_class)
                else:
                    filing['newShareClasses'].append(share_class)

            ceased_share_classes = [s for s in prev_share_class_json if s['id'] not in share_class_to_edit]
            filing['ceasedShareClasses'] = ceased_share_classes

    def _format_share_series_data(self, share_class, filing, prev_completed_filing: Filing):  # pylint: disable=too-many-locals; # noqa: E501;
        if share_class.get('series'):
            prev_share_series_json = VersionedBusinessDetailsService.get_share_series_revision(
                prev_completed_filing.transaction_id,
                share_class.get('id'))
            prev_share_series_ids = [x['id'] for x in prev_share_series_json]
            share_series_to_edit = []
            for share_series in share_class.get('series'):
                if share_series_id := share_series.get('id'):
                    if (share_series_id := str(share_series_id)) in prev_share_series_ids:
                        share_series_to_edit.append(share_series_id)
                        if self._compare_json(share_series,
                                              next((x for x in prev_share_series_json if x['id'] == share_series_id)),
                                              ['id', 'type']):
                            share_series['changed'] = True
                            filing['shareClassesChange'] = True
                    else:
                        del share_series['id']
                        filing['shareClassesChange'] = True
                else:
                    filing['shareClassesChange'] = True

            ceased_share_series = [s for s in prev_share_series_json if s['id'] not in share_series_to_edit]
            if ceased_share_series:
                filing['shareClassesChange'] = True

    def _format_resolution_data(self, filing: Filing):
        meta_data = self._filing.meta_data or {}
        filing_source = 'correction'
        prev_association_type = meta_data.get(filing_source, {}).get('fromCooperativeAssociationType')
        to_association_type = meta_data.get(filing_source, {}).get('toCooperativeAssociationType')
        if prev_association_type and to_association_type and prev_association_type != to_association_type:
            filing['prevCoopAssociationType'] = ASSOCIATION_TYPE_DESC.get(prev_association_type, '')
            filing['newCoopAssociationType'] = ASSOCIATION_TYPE_DESC.get(to_association_type, '')
        filing['rulesInResolution'] = filing.get(filing_source, {}).get('rulesInResolution')
        filing['uploadNewRules'] = meta_data.get(filing_source, {}).get('uploadNewRules')
        filing['uploadNewMemorandum'] = meta_data.get(filing_source, {}).get('uploadNewMemorandum')
        filing['memorandumInResolution'] = filing.get(filing_source, {}).get('memorandumInResolution')
        if (resolution_date_str := filing.get(filing_source, {}).get('resolutionDate', None)):
            resolution_date = LegislationDatetime.as_legislation_timezone_from_date_str(resolution_date_str)
            filing[filing_source]['resolutionDate'] = resolution_date.strftime(OUTPUT_DATE_FORMAT)

    @staticmethod
    def _compare_json(new_json, existing_json, excluded_keys):
        if not new_json and not existing_json:
            return False
        if new_json and not existing_json:
            return True

        changed = False
        for key in existing_json:
            if key not in excluded_keys:
                if (new_json.get(key, '') or '') != (existing_json.get(key) or ''):
                    changed = True
        return changed

    def _format_special_resolution(self, filing):
        """For special resolutions."""
        display_name = FILINGS.get(self._filing.filing_type, {}).get('displayName')
        if isinstance(display_name, dict):
            display_name = display_name.get(self._business.legal_type)
        filing_source = 'specialResolution' if self._filing.filing_type == 'specialResolution' else 'correction'
        filing['header']['displayName'] = display_name
        resolution_date_str = filing.get(filing_source, {}).get('resolutionDate', None)
        signing_date_str = filing.get(filing_source, {}).get('signingDate', None)
        if resolution_date_str:
            resolution_date = LegislationDatetime.as_legislation_timezone_from_date_str(resolution_date_str)
            filing[filing_source]['resolutionDate'] = resolution_date.strftime(OUTPUT_DATE_FORMAT)
        if signing_date_str:
            signing_date = LegislationDatetime.as_legislation_timezone_from_date_str(signing_date_str)
            filing[filing_source]['signingDate'] = signing_date.strftime(OUTPUT_DATE_FORMAT)

    def _format_special_resolution_application(self, filing, filing_source):
        """For special resolutions."""
        meta_data = self._filing.meta_data or {}
        if filing_source == 'alteration':
            prev_legal_name = meta_data.get('changeOfName', {}).get('fromLegalName')
            to_legal_name = meta_data.get('changeOfName', {}).get('toLegalName')
            if prev_legal_name and to_legal_name and prev_legal_name != to_legal_name:
                filing['fromLegalName'] = prev_legal_name
                filing['toLegalName'] = to_legal_name
                filing['nrNumber'] = filing.get('changeOfName').get('nameRequest', {}).get('nrNumber', None)
        elif filing_source == 'correction':
            prev_legal_name = meta_data.get(filing_source, {}).get('fromLegalName')
            to_legal_name = meta_data.get(filing_source, {}).get('toLegalName')
            if prev_legal_name and to_legal_name and prev_legal_name != to_legal_name:
                filing['fromLegalName'] = prev_legal_name
                filing['toLegalName'] = to_legal_name
                filing['nrNumber'] = filing.get(filing_source).get('nameRequest', {}).get('nrNumber', None)
        self._format_resolution_data(filing)

    def _format_noa_data(self, filing):
        filing['header'] = {}
        filing['header']['filingId'] = self._filing.id

    def _set_meta_info(self, filing):
        filing['environment'] = f'{self._get_environment()} FILING #{self._filing.id}'.lstrip()
        # Get source
        filing['source'] = self._filing.source
        # Appears in the Description section of the PDF Document Properties as Title.
        if not (title := self._filing.FILINGS[self._filing.filing_type].get('title')):
            if not (self._filing.filing_sub_type and (title := self._filing.FILINGS[self._filing.filing_type]
                                                      .get(self._filing.filing_sub_type, {})
                                                      .get('title'))):
                title = self._filing.filing_type
        filing['meta_title'] = '{} on {}'.format(title, filing['filing_date_time'])

        # Appears in the Description section of the PDF Document Properties as Subject.
        if self._report_key == 'noticeOfArticles':
            filing['meta_subject'] = '{} ({})'.format(self._business.legal_name, self._business.identifier)
        else:
            legal_name = self._filing.filing_json['filing'].get('business', {}).get('legalName', 'NA')
            filing['meta_subject'] = '{} ({})'.format(
                legal_name,
                self._filing.filing_json['filing'].get('business', {}).get('identifier', 'NA'))

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
        'amalgamationApplication': {
            'filingDescription': 'Amalgamation Application',
            'fileName': 'amalgamationApplication'
        },
        'certificateOfAmalgamation': {
            'filingDescription': 'Certificate Of Amalgamation',
            'fileName': 'certificateOfAmalgamation'
        },
        'certificate': {
            'filingDescription': 'Certificate of Incorporation',
            'fileName': 'certificateOfIncorporation'
        },
        'incorporationApplication': {
            'filingDescription': 'Incorporation Application',
            'fileName': 'incorporationApplication'
        },
        'noticeOfArticles': {
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
            'default': {
                'fileName': 'bcAddressChange'
            },
            'CP': {
                'fileName': 'changeOfAddress'
            }
        },
        'changeOfDirectors': {
            'hasDifferentTemplates': True,
            'filingDescription': 'Change of Directors',
            'default': {
                'fileName': 'bcDirectorChange'
            },
            'CP': {
                'fileName': 'changeOfDirectors'
            }
        },
        'annualReport': {
            'hasDifferentTemplates': True,
            'filingDescription': 'Annual Report',
            'default': {
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
        'specialResolutionApplication': {
            'filingDescription': 'Special Resolution Application',
            'fileName': 'specialResolutionApplication'
        },
        'voluntaryDissolution': {
            'filingDescription': 'Voluntary Dissolution',
            'fileName': 'voluntaryDissolution'
        },
        'certificateOfNameChange': {
            'filingDescription': 'Certificate of Name Change',
            'fileName': 'certificateOfNameChange'
        },
        'certificateOfNameCorrection': {
            'filingDescription': 'Certificate of Name Correction',
            'fileName': 'certificateOfNameChange'
        },
        'certificateOfDissolution': {
            'filingDescription': 'Certificate of Dissolution',
            'fileName': 'certificateOfDissolution'
        },
        'dissolution': {
            'filingDescription': 'Dissolution Application',
            'fileName': 'dissolution'
        },
        'registration': {
            'filingDescription': 'Statement of Registration',
            'fileName': 'registration'
        },
        'amendedRegistrationStatement': {
            'filingDescription': 'Amended Registration Statement',
            'fileName': 'amendedRegistrationStatement'
        },
        'correctedRegistrationStatement': {
            'filingDescription': 'Corrected Registration Statement',
            'fileName': 'amendedRegistrationStatement'
        },
        'changeOfRegistration': {
            'filingDescription': 'Change of Registration',
            'fileName': 'changeOfRegistration'
        },
        'correction': {
            'hasDifferentTemplates': True,
            'filingDescription': 'Correction',
            'default': {
                'fileName': 'correction'
            },
            'SP': {
                'fileName': 'firmCorrection'
            },
            'GP': {
                'fileName': 'firmCorrection'
            }
        },
        'certificateOfRestoration': {
            'filingDescription': 'Certificate of Restoration',
            'fileName': 'certificateOfRestoration'
        },
        'restoration': {
            'filingDescription': 'Restoration Application',
            'fileName': 'restoration'
        },
        'letterOfConsent': {
            'filingDescription': 'Letter Of Consent',
            'fileName': 'letterOfConsent'
        },
        'letterOfAgmExtension': {
            'filingDescription': 'Letter Of AGM Extension',
            'fileName': 'letterOfAgmExtension'
        },
        'letterOfAgmLocationChange': {
            'filingDescription': 'Letter Of AGM Location Change',
            'fileName': 'letterOfAgmLocationChange'
        },
        'continuationIn': {
            'filingDescription': 'Continuation Application',
            'fileName': 'continuationApplication'
        },
        'certificateOfContinuation': {
            'filingDescription': 'Certificate of Continuation',
            'fileName': 'certificateOfContinuation'
        }
    }

    static_reports = {
        'certifiedRules': {
            'documentType': 'coop_rules'
        },
        'certifiedMemorandum': {
            'documentType': 'coop_memorandum'
        },
        'affidavit': {
            'documentType': 'affidavit'
        },
        'uploadedCourtOrder': {
            'documentType': 'court_order'
        }
    }
