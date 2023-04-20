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
from datetime import datetime
from http import HTTPStatus
from pathlib import Path

import pycountry
import requests
from flask import current_app, jsonify

from legal_api.models import Alias, Business, CorpType, Filing
from legal_api.reports.registrar_meta import RegistrarInfo
from legal_api.resources.v2.business import get_addresses, get_directors
from legal_api.resources.v2.business.business_parties import get_parties
from legal_api.utils.auth import jwt
from legal_api.utils.legislation_datetime import LegislationDatetime


class BusinessDocument:
    """Service to create business document outputs."""

    def __init__(self, business, document_key):
        """Create the Report instance."""
        self._business = business
        self._document_key = document_key
        self._report_date_time = LegislationDatetime.now()
        self._epoch_filing_date = None

    def get_pdf(self):
        """Render the business document pdf response."""
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

    def get_json(self):
        """Render the business document json response."""
        return self._get_template_data(get_json=True), HTTPStatus.OK

    def _get_report_filename(self):
        report_date = str(self._report_date_time)[:19]
        return '{}_{}_{}.pdf'.format(self._business.identifier, report_date,
                                     ReportMeta.reports[self._document_key]['reportName']).replace(' ', '_')

    def _get_template(self):
        try:
            template_path = current_app.config.get('REPORT_TEMPLATE_PATH')
            template_file_name = ReportMeta.reports[self._document_key]['templateName']
            template_code = Path(f'{template_path}/{template_file_name}.html').read_text()
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
            'business-summary/parties',
            'common/addresses',
            'common/businessDetails',
            'common/footerMOCS',
            'common/nameTranslation',
            'common/style',
            'common/styleLetterOverride',
            'common/certificateFooter',
            'common/certificateLogo',
            'common/certificateRegistrarSignature',
            'common/certificateSeal',
            'common/certificateStyle',
            'common/courtOrder',
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

    def _get_template_data(self, get_json=False):
        """Return the json for the report template."""
        business_json = {}
        try:
            # get document data
            business_json['reportType'] = self._document_key
            business_json['business'] = self._business.json()
            business_json['registrarInfo'] = {**RegistrarInfo.get_registrar_info(self._report_date_time)}
            self._set_description(business_json)
            self._set_epoch_date(business_json)

            if self._document_key in ['lseal', 'summary']:
                self._set_addresses(business_json)
                self._set_business_state_changes(business_json)

            if self._document_key == 'summary':
                self._set_parties(business_json)
                self._set_name_translations(business_json)
                self._set_business_changes(business_json)
                self._set_amalgamation_details(business_json)
                self._set_liquidation_details(business_json)

            if self._business.legal_type in ['SP', 'GP']:
                registration_filing = Filing.get_filings_by_types(self._business.id, ['registration'])
                if registration_filing:
                    business_json['business']['registrationDateTime'] = \
                        registration_filing[0].effective_date.isoformat()

            if get_json:
                # set report date
                business_json['reportDateTime'] = \
                    LegislationDatetime.as_utc_timezone(self._report_date_time).isoformat()
                # remove signature etc. from registrar info
                pruned_registrar_info = {}
                for key in business_json['registrarInfo']:
                    if key in ['name', 'title', 'startDate', 'endDate']:
                        pruned_registrar_info[key] = business_json['registrarInfo'][key]
                business_json['registrarInfo'] = pruned_registrar_info
                # return raw document json
                return business_json

            # else make pretty for pdf template
            self._set_description_xtra(business_json)
            self._set_dates(business_json)
            self._set_meta_info(business_json)

            if self._document_key == 'summary':
                # set party groups
                self._set_directors(business_json)
                self._set_record_keepers(business_json)

        except Exception as e:
            current_app.logger.error(e)
            raise e
        return business_json

    def _set_epoch_date(self, business: dict):
        """Set the epoch filing date (date it was imported from COLIN)."""
        epoch_filing = Filing.get_filings_by_status(self._business.id, [Filing.Status.EPOCH])
        if epoch_filing:
            self._epoch_filing_date = epoch_filing[0].effective_date
            business['business']['epochFilingDate'] = self._epoch_filing_date.isoformat()

    def _set_description(self, business: dict):
        """Set business descriptors used by json and pdf template."""
        legal_type = self._business.legal_type
        corp_type = CorpType.find_by_id(legal_type)
        business['entityDescription'] = corp_type.full_desc
        act = {
            Business.LegalTypes.COOP.value: 'Cooperative Association Act',
            Business.LegalTypes.SOLE_PROP.value: 'Partnership Act',
            Business.LegalTypes.PARTNERSHIP.value: 'Partnership Act'
        }  # This could be the legislation column from CorpType. Yet to discuss.
        business['entityAct'] = act.get(legal_type, 'Business Corporations Act')

        business['business']['coopType'] = BusinessDocument.CP_TYPE_DESCRIPTION[self._business.association_type]\
            if self._business.association_type else 'Not Available'

    def _set_description_xtra(self, business: dict):
        """Set business descriptors only used by pdf template."""
        description = {
            Business.LegalTypes.COOP.value: 'Cooperative Association',
            Business.LegalTypes.BCOMP.value: 'Benefit Company',
            Business.LegalTypes.PARTNERSHIP.value: 'General Partnership',
            Business.LegalTypes.SOLE_PROP.value: 'Sole Proprietorship',
        }
        business['entityShortDescription'] = description.get(self._business.legal_type, 'Corporation')
        business['entityInformalDescription'] = business['entityShortDescription'].lower()

    def _set_dates(self, business: dict):  # pylint: disable=too-many-branches
        """Set the business json with formatted dates."""
        # business dates
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
        if epoch_date := business['business'].get('epochFilingDate'):
            business['business']['epochFilingDate'] = LegislationDatetime.\
                as_legislation_timezone(datetime.fromisoformat(epoch_date)).strftime('%B %-d, %Y')
        if self._business.restoration_expiry_date:
            business['business']['restorationExpiryDate'] = LegislationDatetime.\
                format_as_report_string(self._business.restoration_expiry_date)
        # state change dates
        for filing in business.get('stateFilings', []):
            filing_datetime = datetime.fromisoformat(filing['filingDateTime'])
            filing['filingDateTime'] = LegislationDatetime.format_as_report_string(filing_datetime)
            effective_datetime = LegislationDatetime\
                .as_legislation_timezone(datetime.fromisoformat(filing['effectiveDateTime']))
            filing['effectiveDateTime'] = LegislationDatetime.format_as_report_string(effective_datetime)
            filing['effectiveDate'] = effective_datetime.strftime('%B %-d, %Y')
        # name change dates
        for filing in business.get('nameChanges', []):
            filing_datetime = datetime.fromisoformat(filing['filingDateTime'])
            filing['filingDateTime'] = LegislationDatetime.format_as_report_string(filing_datetime)
        # alteration change dates
        for filing in business.get('alterations', []):
            filing_datetime = datetime.fromisoformat(filing['filingDateTime'])
            filing['filingDateTime'] = LegislationDatetime.format_as_report_string(filing_datetime)
        # liquidation date
        if liquidation_date := business.get('liquidation', {}).get('filingDateTime'):
            filing_datetime = datetime.fromisoformat(liquidation_date)
            business['liquidation']['filingDateTime'] = LegislationDatetime.format_as_report_string(filing_datetime)
        # registration dates
        if registration_datetime_str := business['business'].get('registrationDateTime'):
            business['formatted_registration_date'] = LegislationDatetime.\
                format_as_report_string(datetime.fromisoformat(registration_datetime_str))
        # founding dates
        founding_datetime = LegislationDatetime.as_legislation_timezone(self._business.founding_date)
        business['formatted_founding_date_time'] = LegislationDatetime.format_as_report_string(founding_datetime)
        business['formatted_founding_date'] = founding_datetime.strftime('%B %-d, %Y')
        # dissolution dates
        if self._business.dissolution_date:
            dissolution_datetime = LegislationDatetime.as_legislation_timezone(self._business.dissolution_date)
            business['formatted_dissolution_date'] = dissolution_datetime.strftime('%B %-d, %Y')
        # report dates
        business['report_date_time'] = LegislationDatetime.format_as_report_string(self._report_date_time)
        business['report_date'] = self._report_date_time.strftime('%B %-d, %Y')
        if self._business.start_date:
            business['start_date_utc'] = self._business.start_date.strftime('%B %-d, %Y')
        if self._business.restoration_expiry_date:
            formatted_restoration_expiry_date = \
                LegislationDatetime.format_as_report_expiry_string(self._business.restoration_expiry_date)
            business['formatted_restoration_expiry_date'] = formatted_restoration_expiry_date

    def _set_addresses(self, business: dict):
        """Set business addresses."""
        address_json = get_addresses(self._business.identifier).json
        for office_type in ['registeredOffice', 'recordsOffice', 'businessOffice']:
            if office_type in address_json:
                for key, value in address_json[office_type].items():
                    address_json[office_type][key] = BusinessDocument._format_address(value)
        business['offices'] = address_json

    def _set_directors(self, business: dict):
        """Set directors (these have a different schema than parties)."""
        directors_json = get_directors(self._business.identifier).json['directors']
        for director in directors_json:
            if director.get('mailingAddress'):
                director['mailingAddress'] = BusinessDocument._format_address(director['mailingAddress'])
            if director.get('deliveryAddress'):
                director['deliveryAddress'] = BusinessDocument._format_address(director['deliveryAddress'])
        business['directors'] = directors_json

    def _set_parties(self, business: dict):
        """Set the parties of the business (all parties)."""
        party_json = get_parties(self._business.identifier).json['parties']
        for party in party_json:
            if party.get('mailingAddress'):
                party['mailingAddress'] = BusinessDocument._format_address(party['mailingAddress'])
            if party.get('deliveryAddress'):
                party['deliveryAddress'] = BusinessDocument._format_address(party['deliveryAddress'])
        business['parties'] = party_json

    def _set_name_translations(self, business: dict):
        """Set the aliases."""
        aliases = Alias.find_by_type(self._business.id, 'TRANSLATION')
        business['listOfTranslations'] = [alias.json for alias in aliases]

    def _set_business_state_changes(self, business: dict):
        """Set list of partial state change filing data."""
        state_filings = []
        # Any filings like restoration, liquidation etc. that changes the state must be included here
        for filing in Filing.get_filings_by_types(self._business.id, ['dissolution', 'restorationApplication',
                                                                      'dissolved', 'restoration',
                                                                      'voluntaryDissolution',
                                                                      'Involuntary Dissolution',
                                                                      'voluntaryLiquidation', 'putBackOn']):
            state_filings.append(self._format_state_filing(filing))
        business['stateFilings'] = state_filings

    def _set_record_keepers(self, business: dict):
        """Set the custodians of the business (parties with custodian role)."""
        if self._business.state.name == 'HISTORICAL':
            custodian_json = [party_role.json for party_role in self._business.party_roles.all()
                              if party_role.role.lower() == 'custodian']
            for custodian in custodian_json:
                custodian['mailingAddress'] = BusinessDocument._format_address(custodian['mailingAddress'])
                custodian['deliveryAddress'] = BusinessDocument._format_address(custodian['deliveryAddress'])
            business['custodians'] = custodian_json

    def _set_business_changes(self, business: dict):
        """Set list of partial name/type change filing data."""
        name_changes = []
        alterations = []
        # Any future filings that includes a company name/type change must be added here
        for filing in Filing.get_filings_by_types(self._business.id, ['alteration', 'correction', 'changeOfName',
                                                                      'changeOfRegistration', 'specialResolution']):
            filing_meta = filing.meta_data
            filing_json = filing.filing_json
            if filing_meta:
                filing_changes = filing_meta.get(filing.filing_type, {})
                if filing.filing_type == 'alteration':
                    change_info = {}
                    change_info['filingDateTime'] = filing.filing_date.isoformat()
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
                        name_change_info['filingDateTime'] = filing.filing_date.isoformat()
                        name_changes.append(name_change_info)
                    elif filing_meta.get('changeOfName'):  # For compound filing like CP special resolution
                        name_change_info = {}
                        name_change_info['fromLegalName'] = filing_meta.get('changeOfName').get('fromLegalName',
                                                                                                'Not Available')
                        name_change_info['toLegalName'] = filing_meta.get('changeOfName').get('toLegalName',
                                                                                              'Not Available')
                        name_change_info['filingDateTime'] = filing.filing_date.isoformat()
                        name_changes.append(name_change_info)
        business['nameChanges'] = name_changes
        business['alterations'] = alterations

    def _format_state_filing(self, filing: Filing) -> dict:
        """Format state change filing data."""
        filing_info = {}

        filing_info['filingDateTime'] = filing.filing_date.isoformat()
        filing_info['effectiveDateTime'] = filing.effective_date.isoformat()

        filing_meta = filing.meta_data
        if filing.filing_type == 'dissolution':
            filing_info['filingName'] = BusinessDocument.\
                _get_summary_display_name(filing.filing_type,
                                          filing_meta['dissolution']['dissolutionType'],
                                          self._business.legal_type)
            if self._business.legal_type in ['SP', 'GP'] and filing_meta['dissolution']['dissolutionType'] == \
                    'voluntary':
                filing_info['dissolution_date_str'] = \
                    datetime.utcnow().strptime(filing.filing_json['filing']['dissolution']['dissolutionDate'],
                                               '%Y-%m-%d').date().strftime('%B %-d, %Y')
        elif filing.filing_type == 'restoration':
            filing_info['filingName'] = BusinessDocument.\
                _get_summary_display_name(filing.filing_type,
                                          filing.filing_sub_type,
                                          self._business.legal_type)
            if filing.filing_sub_type in ['limitedRestoration', 'limitedRestorationExtension']:
                expiry_date = filing_meta['restoration']['expiry']
                expiry_date = LegislationDatetime.as_legislation_timezone_from_date_str(expiry_date)
                expiry_date = expiry_date.replace(minute=1)
                filing_info['limitedRestorationExpiryDate'] = LegislationDatetime.format_as_report_string(expiry_date)

        else:
            filing_info['filingName'] = BusinessDocument.\
                _get_summary_display_name(filing.filing_type, None, None)
        return filing_info

    def _set_amalgamation_details(self, business: dict):
        """Set the list of partial amalgamation filing data."""
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
        """Set partial liquidation filing data."""
        liquidation_info = {}
        liquidation = Filing.get_filings_by_types(self._business.id, ['voluntaryLiquidation'])
        if liquidation:
            liquidation_info['filingDateTime'] = liquidation[0].filing_date.isoformat()
            business['business']['state'] = Business.State.LIQUIDATION.name
            if self._epoch_filing_date and liquidation[0].effective_date < self._epoch_filing_date:
                liquidation_info['custodian'] = 'Not Available'
                records_office_info = {}
                records_office_info['deliveryAddress'] = 'Not Available'
                records_office_info['mailingAddress'] = 'Not Available'
                liquidation_info['recordsOffice'] = records_office_info
        business['liquidation'] = liquidation_info

    @staticmethod
    def _format_address(address):
        address['streetAddressAdditional'] = address.get('streetAddressAdditional') or ''
        address['addressRegion'] = address.get('addressRegion') or ''
        address['deliveryInstructions'] = address.get('deliveryInstructions') or ''

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
    def _get_summary_display_name(filing_type: str, filing_sub_type: str, legal_type: str) -> str:
        if filing_type == 'dissolution':
            return BusinessDocument.FILING_SUMMARY_DISPLAY_NAME[filing_type][filing_sub_type][legal_type]
        elif filing_type == 'restoration':
            return BusinessDocument.FILING_SUMMARY_DISPLAY_NAME[filing_type][filing_sub_type]
        else:
            return BusinessDocument.FILING_SUMMARY_DISPLAY_NAME[filing_type]

    @staticmethod
    def _get_legal_type_description(legal_type: str) -> str:
        corp_type = CorpType.find_by_id(legal_type)
        return corp_type.full_desc if corp_type else ''

    FILING_SUMMARY_DISPLAY_NAME = {
        'dissolution': {
            'voluntary': {
                'CP': 'Voluntary Dissolution',
                'BC': 'Voluntary Dissolution',
                'BEN': 'Voluntary Dissolution',
                'ULC': 'Voluntary Dissolution',
                'CC': 'Voluntary Dissolution',
                'LLC': 'Voluntary Dissolution',
                'SP': 'Dissolution Application',
                'GP': 'Dissolution Application'
            },
            'administrative': {
                'CP': 'Administrative Dissolution',
                'BC': 'Administrative Dissolution',
                'BEN': 'Administrative Dissolution',
                'ULC': 'Administrative Dissolution',
                'CC': 'Administrative Dissolution',
                'LLC': 'Administrative Dissolution',
                'SP': 'Administrative Dissolution',
                'GP': 'Administrative Dissolution'
            }
        },
        'restorationApplication': 'Restoration Application',
        'restoration': {
            'fullRestoration': 'Full Restoration',
            'limitedRestoration': 'Limited Restoration',
            'limitedRestorationExtension': 'Extension of Limited Restoration',
            'limitedRestorationToFull': 'Convert Limited Restoration to Full Restoration'
        },
        'dissolved': 'Involuntary Dissolution',
        'voluntaryDissolution': 'Voluntary Dissolution',
        'Involuntary Dissolution': 'Involuntary Dissolution',
        'voluntaryLiquidation': 'Voluntary Liquidation',
        'putBackOn': 'Correction - Put Back On'
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


class ReportMeta:  # pylint: disable=too-few-public-methods
    """Helper class to maintain the report meta information."""

    reports = {
        'summary': {
            'reportName': 'summary',
            'templateName': 'businessSummary'
        },
        'cogs': {
            'reportName': 'Certificate_of_Good_Standing',
            'templateName': 'certificateOfGoodStanding'
        },
        'cstat': {
            'reportName': 'Certificate_of_Status',
            'templateName': 'certificateOfStatus'
        },
        'lseal': {
            'reportName': 'Letter_Under_Seal',
            'templateName': 'letterUnderSeal'
        }
    }
