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
from typing import Final, Optional

import pycountry
import requests
from flask import current_app, jsonify

from legal_api.models import AlternateName, CorpType, Filing, LegalEntity
from legal_api.models.amalgamation import Amalgamation
from legal_api.reports.registrar_meta import RegistrarInfo
from legal_api.resources.v2.business import get_addresses, get_directors
from legal_api.resources.v2.business.business_parties import get_parties
from legal_api.utils.auth import jwt
from legal_api.utils.legislation_datetime import LegislationDatetime

NOT_AVAILABLE: Final = "Not Available"
OUTPUT_DATE_FORMAT: Final = "%B %-d, %Y"


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
        headers = {"Authorization": "Bearer {}".format(jwt.get_token_auth_header()), "Content-Type": "application/json"}
        data = {
            "reportName": self._get_report_filename(),
            "template": "'" + base64.b64encode(bytes(self._get_template(), "utf-8")).decode() + "'",
            "templateVars": self._get_template_data(),
        }
        response = requests.post(url=current_app.config.get("REPORT_SVC_URL"), headers=headers, data=json.dumps(data))
        if response.status_code != HTTPStatus.OK:
            return jsonify(message=str(response.content)), response.status_code
        return response.content, response.status_code

    def get_json(self):
        """Render the business document json response."""
        return self._get_template_data(get_json=True), HTTPStatus.OK

    def _get_report_filename(self):
        report_date = str(self._report_date_time)[:19]
        return "{}_{}_{}.pdf".format(
            self._business.identifier, report_date, ReportMeta.reports[self._document_key]["reportName"]
        ).replace(" ", "_")

    def _get_template(self):
        try:
            template_path = current_app.config.get("REPORT_TEMPLATE_PATH")
            template_file_name = ReportMeta.reports[self._document_key]["templateName"]
            template_code = Path(f"{template_path}/{template_file_name}.html").read_text()
            # substitute template parts
            template_code = self._substitute_template_parts(template_code)
        except Exception as err:
            current_app.logger.error(err)
            raise err
        return template_code

    @staticmethod
    def _substitute_template_parts(template_code):
        template_path = current_app.config.get("REPORT_TEMPLATE_PATH")
        template_parts = [
            "business-summary/alterations",
            "business-summary/amalgamations",
            "business-summary/amalgamating",
            "business-summary/businessDetails",
            "business-summary/liquidation",
            "business-summary/nameChanges",
            "business-summary/stateTransition",
            "business-summary/recordKeeper",
            "business-summary/parties",
            "common/addresses",
            "common/businessDetails",
            "common/footerMOCS",
            "common/nameTranslation",
            "common/style",
            "common/styleLetterOverride",
            "common/certificateFooter",
            "common/certificateLogo",
            "common/certificateRegistrarSignature",
            "common/certificateSeal",
            "common/certificateStyle",
            "common/courtOrder",
            "footer",
            "logo",
            "macros",
            "notice-of-articles/directors",
        ]
        # substitute template parts - marked up by [[filename]]
        for template_part in template_parts:
            template_part_code = Path(f"{template_path}/template-parts/{template_part}.html").read_text()
            template_code = template_code.replace("[[{}.html]]".format(template_part), template_part_code)
        return template_code

    def _get_template_data(self, get_json=False):
        """Return the json for the report template."""
        business_json = {}
        try:
            # get document data
            business_json["reportType"] = self._document_key
            business_json["business"] = self._business.json()
            business_json["business"]["businessName"] = self._business.business_name
            business_json["registrarInfo"] = {**RegistrarInfo.get_registrar_info(self._report_date_time)}
            self._set_description(business_json)
            self._set_epoch_date(business_json)

            if self._document_key in ["lseal", "summary"]:
                self._set_addresses(business_json)
                self._set_business_state_changes(business_json)

            if self._document_key == "summary":
                self._set_parties(business_json)
                self._set_name_translations(business_json)
                self._set_business_changes(business_json)
                self._set_amalgamation_details(business_json)
                self._set_amalgamating_details(business_json)
                self._set_liquidation_details(business_json)

            if self._business.entity_type in ["SP", "GP"]:
                registration_filing = Filing.get_filings_by_types(self._business, ["registration"])
                if registration_filing:
                    business_json["business"]["registrationDateTime"] = registration_filing[
                        0
                    ].effective_date.isoformat()

            if get_json:
                # set report date
                business_json["reportDateTime"] = LegislationDatetime.as_utc_timezone(
                    self._report_date_time
                ).isoformat()
                # remove signature etc. from registrar info
                pruned_registrar_info = {}
                for key in business_json["registrarInfo"]:
                    if key in ["name", "title", "startDate", "endDate"]:
                        pruned_registrar_info[key] = business_json["registrarInfo"][key]
                business_json["registrarInfo"] = pruned_registrar_info
                # return raw document json
                return business_json

            # else make pretty for pdf template
            self._set_description_xtra(business_json)
            self._set_dates(business_json)
            self._set_meta_info(business_json)

            if self._document_key == "summary":
                # set party groups
                self._set_directors(business_json)
                self._set_record_keepers(business_json)

        except Exception as e:
            current_app.logger.error(e)
            raise e
        return business_json

    def _set_epoch_date(self, legal_entity: dict):
        """Set the epoch filing date (date it was imported from COLIN)."""
        epoch_filing = Filing.get_filings_by_status(self._business, [Filing.Status.EPOCH])
        if epoch_filing:
            self._epoch_filing_date = epoch_filing[0].effective_date
            legal_entity["business"]["epochFilingDate"] = self._epoch_filing_date.isoformat()

    def _set_description(self, legal_entity: dict):
        """Set business descriptors used by json and pdf template."""
        legal_type = self._business.entity_type
        corp_type = CorpType.find_by_id(legal_type)
        legal_entity["entityDescription"] = corp_type.full_desc
        act = {
            LegalEntity.EntityTypes.COOP.value: "Cooperative Association Act",
            LegalEntity.EntityTypes.SOLE_PROP.value: "Partnership Act",
            LegalEntity.EntityTypes.PARTNERSHIP.value: "Partnership Act",
        }  # This could be the legislation column from CorpType. Yet to discuss.
        legal_entity["entityAct"] = act.get(legal_type, "Business Corporations Act")

        legal_entity["business"]["coopType"] = (
            BusinessDocument.CP_TYPE_DESCRIPTION[self._business.association_type]
            if self._business.association_type
            else NOT_AVAILABLE
        )

    def _set_description_xtra(self, legal_entity: dict):
        """Set business descriptors only used by pdf template."""
        description = {
            LegalEntity.EntityTypes.COOP.value: "Cooperative Association",
            LegalEntity.EntityTypes.BCOMP.value: "Benefit Company",
            LegalEntity.EntityTypes.PARTNERSHIP.value: "General Partnership",
            LegalEntity.EntityTypes.SOLE_PROP.value: "Sole Proprietorship",
        }
        legal_entity["entityShortDescription"] = description.get(self._business.entity_type, "Corporation")
        legal_entity["entityInformalDescription"] = legal_entity["entityShortDescription"].lower()

    def _set_dates(self, legal_entity: dict):  # pylint: disable=too-many-branches
        """Set the business json with formatted dates."""
        # business dates
        if self._business.last_ar_date:
            last_ar_date = self._business.last_ar_date.strftime(OUTPUT_DATE_FORMAT)
        else:
            last_ar_date = NOT_AVAILABLE
        legal_entity["business"]["last_ar_date"] = last_ar_date
        if self._business.last_agm_date:
            last_agm_date = self._business.last_agm_date.strftime(OUTPUT_DATE_FORMAT)
        else:
            last_agm_date = NOT_AVAILABLE
        legal_entity["business"]["last_agm_date"] = last_agm_date
        if epoch_date := legal_entity["business"].get("epochFilingDate"):
            legal_entity["business"]["epochFilingDate"] = LegislationDatetime.as_legislation_timezone(
                datetime.fromisoformat(epoch_date)
            ).strftime(OUTPUT_DATE_FORMAT)
        if self._business.restoration_expiry_date:
            legal_entity["business"]["restorationExpiryDate"] = LegislationDatetime.format_as_report_string(
                self._business.restoration_expiry_date
            )
        # state change dates
        for filing in legal_entity.get("stateFilings", []):
            filing_datetime = datetime.fromisoformat(filing["filingDateTime"])
            filing["filingDateTime"] = LegislationDatetime.format_as_report_string(filing_datetime)
            effective_datetime = LegislationDatetime.as_legislation_timezone(
                datetime.fromisoformat(filing["effectiveDateTime"])
            )
            filing["effectiveDateTime"] = LegislationDatetime.format_as_report_string(effective_datetime)
            filing["effectiveDate"] = effective_datetime.strftime(OUTPUT_DATE_FORMAT)
        # name change dates
        for filing in legal_entity.get("nameChanges", []):
            filing_datetime = datetime.fromisoformat(filing["filingDateTime"])
            filing["filingDateTime"] = LegislationDatetime.format_as_report_string(filing_datetime)
        # alteration change dates
        for filing in legal_entity.get("alterations", []):
            filing_datetime = datetime.fromisoformat(filing["filingDateTime"])
            filing["filingDateTime"] = LegislationDatetime.format_as_report_string(filing_datetime)
        # liquidation date
        if liquidation_date := legal_entity.get("liquidation", {}).get("filingDateTime"):
            filing_datetime = datetime.fromisoformat(liquidation_date)
            legal_entity["liquidation"]["filingDateTime"] = LegislationDatetime.format_as_report_string(filing_datetime)
        # registration dates
        if registration_datetime_str := legal_entity["business"].get("registrationDateTime"):
            legal_entity["formatted_registration_date"] = LegislationDatetime.format_as_report_string(
                datetime.fromisoformat(registration_datetime_str)
            )
        # founding dates
        founding_datetime = LegislationDatetime.as_legislation_timezone(self._business.founding_date)
        legal_entity["formatted_founding_date_time"] = LegislationDatetime.format_as_report_string(founding_datetime)
        legal_entity["formatted_founding_date"] = founding_datetime.strftime(OUTPUT_DATE_FORMAT)
        # dissolution dates
        if self._business.dissolution_date:
            dissolution_datetime = LegislationDatetime.as_legislation_timezone(self._business.dissolution_date)
            legal_entity["formatted_dissolution_date"] = dissolution_datetime.strftime(OUTPUT_DATE_FORMAT)
        # report dates
        legal_entity["report_date_time"] = LegislationDatetime.format_as_report_string(self._report_date_time)
        legal_entity["report_date"] = self._report_date_time.strftime(OUTPUT_DATE_FORMAT)
        if self._business.start_date:
            legal_entity["start_date_utc"] = self._business.start_date.strftime(OUTPUT_DATE_FORMAT)
        if self._business.restoration_expiry_date:
            formatted_restoration_expiry_date = LegislationDatetime.format_as_report_expiry_string(
                self._business.restoration_expiry_date
            )
            legal_entity["formatted_restoration_expiry_date"] = formatted_restoration_expiry_date

    def _set_addresses(self, legal_entity: dict):
        """Set business addresses."""
        address_json = get_addresses(self._business.identifier).json
        for office_type in ["registeredOffice", "recordsOffice", "businessOffice"]:
            if office_type in address_json:
                for key, value in address_json[office_type].items():
                    address_json[office_type][key] = BusinessDocument._format_address(value)
        legal_entity["offices"] = address_json

    def _set_directors(self, legal_entity: dict):
        """Set directors (these have a different schema than parties)."""
        directors_json = get_directors(self._business.identifier).json["directors"]
        for director in directors_json:
            if director.get("mailingAddress"):
                director["mailingAddress"] = BusinessDocument._format_address(director["mailingAddress"])
            if director.get("deliveryAddress"):
                director["deliveryAddress"] = BusinessDocument._format_address(director["deliveryAddress"])
        legal_entity["directors"] = directors_json

    def _set_parties(self, legal_entity: dict):
        """Set the parties of the business (all parties)."""
        party_json = get_parties(self._business.identifier).json["parties"]
        for party in party_json:
            if party.get("mailingAddress"):
                party["mailingAddress"] = BusinessDocument._format_address(party["mailingAddress"])
            if party.get("deliveryAddress"):
                party["deliveryAddress"] = BusinessDocument._format_address(party["deliveryAddress"])
            if not party.get("officer", {}).get("partyType") and not party.get("officer", {}).get("lastName"):
                party["officer"]["partyType"] = "organization"
        legal_entity["parties"] = party_json

    def _set_name_translations(self, legal_entity: dict):
        """Set the aliases."""
        aliases = AlternateName.find_by_name_type(self._business.id, "TRANSLATION")
        legal_entity["listOfTranslations"] = [alias.json for alias in aliases]

    def _set_business_state_changes(self, legal_entity: dict):
        """Set list of partial state change filing data."""
        state_filings = []
        # Any filings like restoration, liquidation etc. that changes the state must be included here
        for filing in Filing.get_filings_by_types(
            self._business,
            [
                "dissolution",
                "restorationApplication",
                "dissolved",
                "restoration",
                "voluntaryDissolution",
                "Involuntary Dissolution",
                "voluntaryLiquidation",
                "putBackOn",
                "continuationOut",
            ],
        ):
            state_filings.append(self._format_state_filing(filing))
        # If it is amalgamating business
        if legal_entity.get("business").get("amalgamatedInto"):
            amalgamating_business = self._business.amalgamating_businesses.one_or_none()
            amalgamation = Amalgamation.find_by_id(amalgamating_business.amalgamation_id)
            filing = Filing.find_by_id(amalgamation.filing_id)
            state_filings.insert(0, self._format_state_filing(filing))
        legal_entity["stateFilings"] = state_filings

    def _set_record_keepers(self, legal_entity: dict):
        """Set the custodians of the business (parties with custodian role)."""
        if self._business.state.name == "HISTORICAL":
            custodian_json = [
                party_role.json
                for party_role in self._business.entity_roles.all()
                if party_role.role_type.lower() == "custodian"
            ]
            for custodian in custodian_json:
                custodian["mailingAddress"] = BusinessDocument._format_address(custodian["mailingAddress"])
                custodian["deliveryAddress"] = BusinessDocument._format_address(custodian["deliveryAddress"])
            legal_entity["custodians"] = custodian_json

    def _set_business_changes(self, legal_entity: dict):
        """Set list of partial name/type change filing data."""
        name_changes = []
        alterations = []
        # Any future filings that includes a company name/type change must be added here
        for filing in Filing.get_filings_by_types(
            self._business,
            ["alteration", "correction", "changeOfName", "changeOfRegistration", "specialResolution"],
        ):
            filing_meta = filing.meta_data
            filing_json = filing.filing_json
            if filing_meta:
                filing_changes = filing_meta.get(filing.filing_type, {})
                if filing.filing_type == "alteration":
                    change_info = {}
                    change_info["filingDateTime"] = filing.filing_date.isoformat()
                    if filing_changes.get("fromLegalType") != filing_changes.get("toLegalType"):
                        change_info["fromLegalType"] = BusinessDocument._get_legal_type_description(
                            filing_changes["fromLegalType"]
                        )
                        change_info["toLegalType"] = BusinessDocument._get_legal_type_description(
                            filing_changes["toLegalType"]
                        )
                        if not filing_changes.get("fromBusinessName"):
                            change_info["fromBusinessName"] = filing_json["filing"]["business"]["businessName"]
                            change_info["toBusinessName"] = filing_json["filing"]["business"]["businessName"]
                    if filing_changes.get("fromBusinessName"):
                        change_info["fromBusinessName"] = filing_changes["fromBusinessName"]
                        change_info["toBusinessName"] = filing_changes["toBusinessName"]

                    if change_info.get("fromLegalType"):
                        alterations.append(change_info)
                    elif change_info.get("fromBusinessName"):
                        name_changes.append(change_info)
                else:
                    if filing_changes.get("fromBusinessName") or filing.filing_type == "changeOfName":
                        name_change_info = {}
                        name_change_info["fromBusinessName"] = filing_changes.get("fromBusinessName", NOT_AVAILABLE)
                        name_change_info["toBusinessName"] = filing_changes.get("toBusinessName", NOT_AVAILABLE)
                        name_change_info["filingDateTime"] = filing.filing_date.isoformat()
                        name_changes.append(name_change_info)
                    elif filing_meta.get("changeOfName"):  # For compound filing like CP special resolution
                        name_change_info = {}
                        name_change_info["fromBusinessName"] = filing_meta.get("changeOfName").get(
                            "fromBusinessName", NOT_AVAILABLE
                        )
                        name_change_info["toBusinessName"] = filing_meta.get("changeOfName").get(
                            "toBusinessName", NOT_AVAILABLE
                        )
                        name_change_info["filingDateTime"] = filing.filing_date.isoformat()
                        name_changes.append(name_change_info)
        legal_entity["nameChanges"] = name_changes
        legal_entity["alterations"] = alterations

    def _format_state_filing(self, filing: Filing) -> dict:
        """Format state change filing data."""
        filing_info = {}

        filing_info["filingType"] = filing.filing_type
        filing_info["filingDateTime"] = filing.filing_date.isoformat()
        filing_info["effectiveDateTime"] = filing.effective_date.isoformat()

        filing_meta = filing.meta_data
        if filing.filing_type == "dissolution":
            filing_info["filingName"] = BusinessDocument._get_summary_display_name(
                filing.filing_type, filing_meta["dissolution"]["dissolutionType"], self._business.entity_type
            )
            if (
                self._business.entity_type in ["SP", "GP"]
                and filing_meta["dissolution"]["dissolutionType"] == "voluntary"
            ):
                filing_info["dissolution_date_str"] = LegislationDatetime.as_legislation_timezone_from_date_str(
                    filing.filing_json["filing"]["dissolution"]["dissolutionDate"]
                ).strftime(OUTPUT_DATE_FORMAT)
        elif filing.filing_type == "restoration":
            filing_info["filingName"] = BusinessDocument._get_summary_display_name(
                filing.filing_type, filing.filing_sub_type, self._business.entity_type
            )
            if filing.filing_sub_type in ["limitedRestoration", "limitedRestorationExtension"]:
                expiry_date = filing_meta["restoration"]["expiry"]
                expiry_date = LegislationDatetime.as_legislation_timezone_from_date_str(expiry_date)
                expiry_date = expiry_date.replace(minute=1)
                filing_info["limitedRestorationExpiryDate"] = LegislationDatetime.format_as_report_string(expiry_date)
        elif filing.filing_type == "continuationOut":
            filing_info["filingName"] = BusinessDocument._get_summary_display_name(filing.filing_type, None, None)

            country_code = filing_meta["continuationOut"]["country"]
            region_code = filing_meta["continuationOut"]["region"]

            country = pycountry.countries.get(alpha_2=country_code)
            region = None
            if region_code and region_code.upper() != "FEDERAL":
                region = pycountry.subdivisions.get(code=f"{country_code}-{region_code}")
            filing_info["jurisdiction"] = f"{region.name}, {country.name}" if region else country.name
            filing_info["foreignLegalName"] = filing_meta["continuationOut"]["legalName"]
            continuation_out_date = LegislationDatetime.as_legislation_timezone_from_date_str(
                filing_meta["continuationOut"]["continuationOutDate"]
            )
            filing_info["continuationOutDate"] = continuation_out_date.strftime(OUTPUT_DATE_FORMAT)
        else:
            filing_info["filingName"] = BusinessDocument._get_summary_display_name(filing.filing_type, None, None)
        return filing_info

    def _set_amalgamation_details(self, legal_entity: dict):
        """Set amalgamation filing data."""
        amalgamated_businesses = []
        filings = Filing.get_filings_by_types(self._business, ["amalgamationApplication"])
        if filings:
            amalgamation_application = filings[0]
            legal_entity["business"]["amalgamatedEntity"] = True
            if self._epoch_filing_date and amalgamation_application.effective_date < self._epoch_filing_date:
                # imported from COLIN
                amalgamated_businesses_info = {"legalName": "Not Available", "identifier": "Not Available"}
                amalgamated_businesses.append(amalgamated_businesses_info)
            else:
                amalgamation = self._business.amalgamation.one_or_none()
                amalgamating_businesses = amalgamation.amalgamating_businesses.all()
                for amalgamating_business in amalgamating_businesses:
                    if ting_business := LegalEntity.find_by_internal_id(amalgamating_business.legal_entity_id):
                        identifier = ting_business.identifier
                        business_legal_name = ting_business.legal_name
                    else:
                        identifier = amalgamating_business.foreign_identifier or "Not Available"
                        business_legal_name = amalgamating_business.foreign_name or "Not Available"

                    amalgamated_businesses_info = {"legalName": business_legal_name, "identifier": identifier}
                    amalgamated_businesses.append(amalgamated_businesses_info)
        legal_entity["amalgamatedEntities"] = amalgamated_businesses

    def _set_amalgamating_details(self, legal_entity: dict):
        amalgamating_info = legal_entity.get("business", {}).get("amalgamatedInto")
        if amalgamating_info:
            legal_entity["business"]["isAmalgamating"] = True
            if legal_entity.get("amalgamatedEntities"):
                # Amalgamating business can contain amalgamatedEntities when it is created through an amalgamation
                # (if a business was a TED and it is now a TING). No need to show amalgamating businesses information
                legal_entity["amalgamatedEntities"] = []

    def _set_liquidation_details(self, legal_entity: dict):
        """Set partial liquidation filing data."""
        liquidation_info = {}
        liquidation = Filing.get_filings_by_types(self._business, ["voluntaryLiquidation"])
        if liquidation:
            liquidation_info["filingDateTime"] = liquidation[0].filing_date.isoformat()
            legal_entity["business"]["state"] = LegalEntity.State.LIQUIDATION.name
            if self._epoch_filing_date and liquidation[0].effective_date < self._epoch_filing_date:
                liquidation_info["custodian"] = NOT_AVAILABLE
                records_office_info = {}
                records_office_info["deliveryAddress"] = NOT_AVAILABLE
                records_office_info["mailingAddress"] = NOT_AVAILABLE
                liquidation_info["recordsOffice"] = records_office_info
        legal_entity["liquidation"] = liquidation_info

    @staticmethod
    def _format_address(address):
        address["streetAddressAdditional"] = address.get("streetAddressAdditional") or ""
        address["addressRegion"] = address.get("addressRegion") or ""
        address["deliveryInstructions"] = address.get("deliveryInstructions") or ""

        country = address["addressCountry"]
        country = pycountry.countries.search_fuzzy(country)[0].name
        address["addressCountry"] = country
        address["addressCountryDescription"] = country
        return address

    def _set_meta_info(self, legal_entity: dict):
        legal_entity["environment"] = f"{self._get_environment()} BUSINESS #{self._business.identifier}".lstrip()
        legal_entity["meta_title"] = "Business Summary on {}".format(legal_entity["report_date_time"])
        legal_entity["meta_subject"] = "{} ({})".format(self._business.business_name, self._business.identifier)

    @staticmethod
    def _get_environment():
        namespace = os.getenv("POD_NAMESPACE", "").lower()
        if namespace.endswith("dev"):
            return "DEV"
        if namespace.endswith("test"):
            return "TEST"
        return ""

    @staticmethod
    def _get_summary_display_name(filing_type: str, filing_sub_type: Optional[str], legal_type: Optional[str]) -> str:
        if filing_type == "dissolution":
            return BusinessDocument.FILING_SUMMARY_DISPLAY_NAME[filing_type][filing_sub_type][legal_type]
        elif filing_type == "restoration":
            return BusinessDocument.FILING_SUMMARY_DISPLAY_NAME[filing_type][filing_sub_type]
        else:
            return BusinessDocument.FILING_SUMMARY_DISPLAY_NAME[filing_type]

    @staticmethod
    def _get_legal_type_description(legal_type: str) -> str:
        corp_type = CorpType.find_by_id(legal_type)
        return corp_type.full_desc if corp_type else ""

    FILING_SUMMARY_DISPLAY_NAME = {
        "amalgamationApplication": "Amalgamation",
        "dissolution": {
            "voluntary": {
                "CP": "Voluntary Dissolution",
                "BC": "Voluntary Dissolution",
                "BEN": "Voluntary Dissolution",
                "ULC": "Voluntary Dissolution",
                "CC": "Voluntary Dissolution",
                "LLC": "Voluntary Dissolution",
                "SP": "Dissolution Application",
                "GP": "Dissolution Application",
            },
            "administrative": {
                "CP": "Administrative Dissolution",
                "BC": "Administrative Dissolution",
                "BEN": "Administrative Dissolution",
                "ULC": "Administrative Dissolution",
                "CC": "Administrative Dissolution",
                "LLC": "Administrative Dissolution",
                "SP": "Administrative Dissolution",
                "GP": "Administrative Dissolution",
            },
        },
        "restorationApplication": "Restoration Application",
        "restoration": {
            "fullRestoration": "Full Restoration",
            "limitedRestoration": "Limited Restoration",
            "limitedRestorationExtension": "Extension of Limited Restoration",
            "limitedRestorationToFull": "Convert Limited Restoration to Full Restoration",
        },
        "dissolved": "Involuntary Dissolution",
        "voluntaryDissolution": "Voluntary Dissolution",
        "Involuntary Dissolution": "Involuntary Dissolution",
        "voluntaryLiquidation": "Voluntary Liquidation",
        "putBackOn": "Correction - Put Back On",
        "continuationOut": "Continuation Out",
    }

    CP_TYPE_DESCRIPTION = {
        "CP": "Ordinary Cooperative",
        "CSC": "Community Service Cooperative",
        "HC": "Housing Cooperative",
    }

    LEGAL_TYPE_DESCRIPTION = {
        "ULC": "BC Unlimited Liability Company",
        "BEN": "BC Benefit Company",
        "CP": "BC Cooperative Association",
        "BC": "BC Limited Company",
        "CC": "BC Community Contribution Company",
        "LLC": "Limited Liability Company",
    }


class ReportMeta:  # pylint: disable=too-few-public-methods
    """Helper class to maintain the report meta information."""

    reports = {
        "summary": {"reportName": "summary", "templateName": "businessSummary"},
        "cogs": {"reportName": "Certificate_of_Good_Standing", "templateName": "certificateOfGoodStanding"},
        "cstat": {"reportName": "Certificate_of_Status", "templateName": "certificateOfStatus"},
        "lseal": {"reportName": "Letter_Under_Seal", "templateName": "letterUnderSeal"},
    }
