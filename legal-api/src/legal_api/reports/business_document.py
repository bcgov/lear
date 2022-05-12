# Copyright © 2021 Province of British Columbia
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
import json
import os
from http import HTTPStatus
from pathlib import Path

import pycountry
import requests
from flask import current_app, jsonify

from legal_api.models import Alias, Business, CorpType, Filing
from legal_api.reports.registrar_meta import RegistrarInfo
from legal_api.resources.v2.business import get_addresses, get_directors
from legal_api.utils.auth import jwt
from legal_api.utils.legislation_datetime import LegislationDatetime


class BusinessDocument:  # pylint: disable=too-few-public-methods
    # TODO review pylint warning and alter as required
    """Service to create business summary output."""

    def __init__(self, business, document_key):
        """Create the Report instance."""
        self._business = business
        self._document_key = document_key
        self._report_date_time = LegislationDatetime.now()
        self._epoch_filing_date = None

    def get_pdf(self):
        """Render the business summary pdf."""
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
        report_date = str(self._report_date_time)[:19]
        return '{}_{}_{}.pdf'.format(self._business.identifier, report_date, 'Summary').replace(' ', '_')

    def _get_template(self):
        try:
            template_path = current_app.config.get('REPORT_TEMPLATE_PATH')
            template_code = Path(f'{template_path}/businessSummary.html').read_text()
            # substitute template parts
            template_code = self._substitute_template_parts(template_code)
        except Exception as err:
            current_app.logger.error(err)
            raise err
        return template_code

    @staticmethod
    def _substitute_template_parts(template_code):
        template_path = current_app.config.get('REPORT_TEMPLATE_PATH')
        template_parts = [
            'business-summary/alterations',
            'business-summary/amalgamations',
            'business-summary/businessDetails',
            'business-summary/liquidation',
            'business-summary/nameChanges',
            'business-summary/stateTransition',
            'business-summary/recordKeeper',
            'common/addresses',
            'common/businessDetails',
            'common/nameTranslation',
            'common/style',
            'footer',
            'logo',
            'macros',
            'notice-of-articles/directors'
        ]
        # substitute template parts - marked up by [[filename]]
        for template_part in template_parts:
            template_part_code = Path(f'{template_path}/template-parts/{template_part}.html').read_text()
            template_code = template_code.replace('[[{}.html]]'.format(template_part), template_part_code)
        return template_code

    def _get_template_data(self):
        business_json = {}
        try:
            business_json['reportType'] = self._document_key
            business_json['business'] = self._business.json()
            business_json['registrarInfo'] = {**RegistrarInfo.get_registrar_info(self._report_date_time)}
            self._set_business_details(business_json)
            self._set_directors(business_json)
            self._set_addresses(business_json)
            self._set_dates(business_json)
            self._set_description(business_json)
            self._set_meta_info(business_json)
            self._set_name_translations(business_json)
            self._set_business_state_changes(business_json)
            self._set_record_keepers(business_json)
            self._set_business_changes(business_json)
            self._set_amalgamation_details(business_json)
            self._set_liquidation_details(business_json)
        except Exception as e:
            current_app.logger.error(e)
            raise e
        return business_json

    def _set_business_details(self, business: dict):
        business['business']['displayState'] = business['business']['state']
        business['business']['coopType'] = BusinessDocument.CP_TYPE_DESCRIPTION[self._business.association_type]\
            if self._business.association_type else 'Not Available'
        if self._business.last_ar_date:
            last_ar_date = self._business.last_ar_date.strftime('%B %-d, %Y')
        else:
            last_ar_date = 'Not Available'
        business['business']['last_ar_date'] = last_ar_date
        if self._business.last_agm_date:
            last_agm_date = self._business.last_agm_date.strftime('%B %-d, %Y')
        else:
            last_agm_date = 'Not Available'
        business['business']['last_agm_date'] = last_agm_date
        epoch_filing = Filing.get_filings_by_status(self._business.id, [Filing.Status.EPOCH])
        if epoch_filing:
            epoch_filing_date = epoch_filing[0].effective_date
            self._epoch_filing_date = epoch_filing_date
            epoch_filing_date = LegislationDatetime.as_legislation_timezone(epoch_filing_date). \
                strftime('%B %-d, %Y')
            business['business']['epochFilingDate'] = epoch_filing_date

    def _set_description(self, business: dict):
        legal_type = self._business.legal_type
        corp_type = CorpType.find_by_id(legal_type)
        business['entityDescription'] = corp_type.full_desc
        act = {
            Business.LegalTypes.COOP.value: 'Cooperative Association Act'
        }  # This could be the legislation column from CorpType. Yet to discuss.
        business['entityAct'] = act.get(legal_type, 'Business Corporations Act')
        description = {
            Business.LegalTypes.COOP.value: 'Cooperative Association'
        }
        business['entityShortDescription'] = description.get(legal_type, 'Corporation')

    def _set_dates(self, business: dict):
        founding_datetime = LegislationDatetime.as_legislation_timezone(self._business.founding_date)
        business['formatted_founding_date_time'] = LegislationDatetime.format_as_report_string(founding_datetime)
        business['formatted_founding_date'] = founding_datetime.strftime('%B %-d, %Y')
        business['report_date_time'] = LegislationDatetime.format_as_report_string(self._report_date_time)

    def _set_addresses(self, business: dict):
        address_json = get_addresses(self._business.identifier).json
        for office_type in ['registeredOffice', 'recordsOffice']:
            if office_type in address_json:
                for key, value in address_json[office_type].items():
                    address_json[office_type][key] = BusinessDocument._format_address(value)
        business['offices'] = address_json

    def _set_directors(self, business: dict):
        directors_json = get_directors(self._business.identifier).json['directors']
        for director in directors_json:
            if director.get('mailingAddress'):
                director['mailingAddress'] = BusinessDocument._format_address(director['mailingAddress'])
            if director.get('deliveryAddress'):
                director['deliveryAddress'] = BusinessDocument._format_address(director['deliveryAddress'])
        business['parties'] = directors_json

    def _set_name_translations(self, business: dict):
        aliases = Alias.find_by_type(self._business.id, 'TRANSLATION')
        business['listOfTranslations'] = [alias.json for alias in aliases]

    def _set_business_state_changes(self, business: dict):
        state_filings = []
        # Any filings like restoration, liquidation etc. that changes the state must be included here
        for filing in Filing.get_filings_by_types(self._business.id, ['dissolution', 'restorationApplication',
                                                                      'dissolved', 'restoration',
                                                                      'voluntaryDissolution',
                                                                      'Involuntary Dissolution',
                                                                      'voluntaryLiquidation']):
            state_filings.append(BusinessDocument._format_state_filing(filing))
        business['stateFilings'] = state_filings

    def _set_record_keepers(self, business: dict):
        if self._business.state.name == 'HISTORICAL':
            custodian_json = [party_role.json for party_role in self._business.party_roles.all()
                              if party_role.role.lower() == 'custodian']
            for custodian in custodian_json:
                custodian['mailingAddress'] = BusinessDocument._format_address(custodian['mailingAddress'])
                custodian['deliveryAddress'] = BusinessDocument._format_address(custodian['deliveryAddress'])
            business['custodians'] = custodian_json

    def _set_business_changes(self, business: dict):
        name_changes = []
        alterations = []
        # Any future filings that includes a company name/type change must be added here
        for filing in Filing.get_filings_by_types(self._business.id, ['alteration', 'correction', 'changeOfName',
                                                                      'specialResolution']):
            filing_meta = filing.meta_data
            filing_json = filing.filing_json
            if filing_meta:
                filing_changes = filing_meta.get(filing.filing_type, {})
                filing_datetime = LegislationDatetime.as_legislation_timezone(filing.filing_date)
                formatted_filing_date_time = LegislationDatetime.format_as_report_string(filing_datetime)
                if filing.filing_type == 'alteration':
                    change_info = {}
                    change_info['filingDateTime'] = formatted_filing_date_time
                    if filing_changes.get('fromLegalType') != filing_changes.get('toLegalType'):
                        change_info['fromLegalType'] = BusinessDocument.\
                            _get_legal_type_description(filing_changes['fromLegalType'])
                        change_info['toLegalType'] = BusinessDocument.\
                            _get_legal_type_description(filing_changes['toLegalType'])
                        if not filing_changes.get('fromLegalName'):
                            change_info['fromLegalName'] = filing_json['filing']['business']['legalName']
                            change_info['toLegalName'] = filing_json['filing']['business']['legalName']
                    if filing_changes.get('fromLegalName'):
                        change_info['fromLegalName'] = filing_changes['fromLegalName']
                        change_info['toLegalName'] = filing_changes['toLegalName']

                    if change_info.get('fromLegalType'):
                        alterations.append(change_info)
                    elif change_info.get('fromLegalName'):
                        name_changes.append(change_info)
                else:
                    if filing_changes.get('fromLegalName') or filing.filing_type == 'changeOfName':
                        name_change_info = {}
                        name_change_info['fromLegalName'] = filing_changes.get('fromLegalName', 'Not Available')
                        name_change_info['toLegalName'] = filing_changes.get('toLegalName', 'Not Available')
                        name_change_info['filingDateTime'] = formatted_filing_date_time
                        name_changes.append(name_change_info)
                    elif filing_meta.get('changeOfName'):  # For compound filing like CP special resolution
                        name_change_info = {}
                        name_change_info['fromLegalName'] = filing_meta.get('changeOfName').get('fromLegalName',
                                                                                                'Not Available')
                        name_change_info['toLegalName'] = filing_meta.get('changeOfName').get('toLegalName',
                                                                                              'Not Available')
                        name_change_info['filingDateTime'] = formatted_filing_date_time
                        name_changes.append(name_change_info)
        business['nameChanges'] = name_changes
        business['alterations'] = alterations

    @staticmethod
    def _format_state_filing(filing: Filing) -> dict:
        filing_info = {}
        filing_datetime = LegislationDatetime.as_legislation_timezone(filing.filing_date)
        filing_info['filing_date_time'] = LegislationDatetime.format_as_report_string(filing_datetime)
        effective_datetime = LegislationDatetime.as_legislation_timezone(filing.effective_date)
        filing_info['effective_date_time'] = LegislationDatetime.format_as_report_string(effective_datetime)
        filing_meta = filing.meta_data
        if filing.filing_type == 'dissolution':
            filing_info['filing_name'] = BusinessDocument.\
                _get_summary_display_name(filing.filing_type, filing_meta['dissolution']['dissolutionType'])
        else:
            filing_info['filing_name'] = BusinessDocument.\
                _get_summary_display_name(filing.filing_type, None)
        return filing_info

    def _set_amalgamation_details(self, business: dict):
        amalgamated_businesses = []
        amalgamation_application = Filing.get_filings_by_types(self._business.id, ['amalgamationApplication'])
        if amalgamation_application:
            business['business']['amalgamatedEntity'] = True
            # else condition will have to be added when we do amalgamation in the new system
            if self._epoch_filing_date and amalgamation_application[0].effective_date < self._epoch_filing_date:
                amalgamated_businesses_info = {
                    'legalName': 'Not Available',
                    'identifier': 'Not Available'
                }
                amalgamated_businesses.append(amalgamated_businesses_info)
        business['amalgamatedEntities'] = amalgamated_businesses

    def _set_liquidation_details(self, business: dict):
        liquidation_info = {}
        liquidation = Filing.get_filings_by_types(self._business.id, ['voluntaryLiquidation'])
        if liquidation:
            filing_datetime = LegislationDatetime.as_legislation_timezone(liquidation[0].filing_date)
            liquidation_info['filing_date_time'] = LegislationDatetime.format_as_report_string(filing_datetime)
            business['business']['state'] = Business.State.LIQUIDATION.name
            business['business']['displayState'] = Business.State.HISTORICAL.name
            if self._epoch_filing_date and liquidation[0].effective_date < self._epoch_filing_date:
                liquidation_info['custodian'] = 'Not Available'
                records_office_info = {}
                records_office_info['deliveryAddress'] = 'Not Available'
                records_office_info['mailingAddress'] = 'Not Available'
                liquidation_info['recordsOffice'] = records_office_info
        business['liquidation'] = liquidation_info

    @staticmethod
    def _format_address(address):
        country = address['addressCountry']
        country = pycountry.countries.search_fuzzy(country)[0].name
        address['addressCountry'] = country
        address['addressCountryDescription'] = country
        return address

    def _set_meta_info(self, business: dict):
        business['environment'] = f'{self._get_environment()} BUSINESS #{self._business.identifier}'.lstrip()
        business['meta_title'] = 'Business Summary on {}'.format(business['report_date_time'])
        business['meta_subject'] = '{} ({})'.format(self._business.legal_name, self._business.identifier)

    @staticmethod
    def _get_environment():
        namespace = os.getenv('POD_NAMESPACE', '').lower()
        if namespace.endswith('dev'):
            return 'DEV'
        if namespace.endswith('test'):
            return 'TEST'
        return ''

    @staticmethod
    def _get_summary_display_name(filing_type: str, filing_sub_type: str) -> str:
        if filing_sub_type:
            return BusinessDocument.FILING_SUMMARY_DISPLAY_NAME[filing_type][filing_sub_type]
        else:
            return BusinessDocument.FILING_SUMMARY_DISPLAY_NAME[filing_type]

    @staticmethod
    def _get_legal_type_description(legal_type: str) -> str:
        return BusinessDocument.LEGAL_TYPE_DESCRIPTION[legal_type]

    FILING_SUMMARY_DISPLAY_NAME = {
        'dissolution': {
            'voluntary': 'Voluntary Dissolution'
        },
        'restorationApplication': 'Restoration Application',
        'restoration': 'Restoration Application',
        'dissolved': 'Involuntary Dissolution',
        'voluntaryDissolution': 'Voluntary Dissolution',
        'Involuntary Dissolution': 'Involuntary Dissolution',
        'voluntaryLiquidation': 'Voluntary Liquidation'
    }

    CP_TYPE_DESCRIPTION = {
        'CP': 'Ordinary Cooperative',
        'CSC': 'Community Service Cooperative',
        'HC': 'Housing Cooperative'
    }

    LEGAL_TYPE_DESCRIPTION = {
        'ULC': 'BC Unlimited Liability Company',
        'BEN': 'BC Benefit Company',
        'CP': 'BC Cooperative Association',
        'BC': 'BC Limited Company',
        'CC': 'BC Community Contribution Company',
        'LLC': 'Limited Liability Company'
    }
