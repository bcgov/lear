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
"""Email processing rules and actions corp filing notifications."""
from __future__ import annotations

import copy
from contextlib import suppress

from flask import current_app
from jinja2 import Template

from business_emailer.email_processors import (
    get_filing_info,
    get_filled_template,
    get_pdfs,
    get_recipient_from_auth,
    get_recipients,
    get_subject,
    get_user_email_from_auth,
)
from business_emailer.email_processors.util import (
    FILING_ATTACHMENTS,
    FILING_TITLE,
    FILING_TITLE_SHORT,
    NOT_AVAILABLE,
    OFFICE_NAME,
    get_legal_type_key,
)
from business_model.models import Business, CorpType, Filing, UserRoles


def _get_additional_info(filing: Filing) -> dict:
    """Populate any additional info required for a filing type."""
    additional_info = {}
    if filing.filing_type == "alteration":
        meta_data_alteration = filing.meta_data.get("alteration", {}) if filing.meta_data else {}
        additional_info["nameChange"] = "toLegalName" in meta_data_alteration
    elif filing.filing_type == "specialResolution":
        additional_info["nameChange"] = filing.filing_json["filing"].get("changeOfName")
        additional_info["rulesChange"] = bool(filing.filing_json["filing"].get("alteration", {}).get("rulesFileKey"))
    elif filing.filing_type == "correction":
        additional_info["nameChange"] = "requestTypeCd" in filing.filing_json["filing"]["correction"].get("nameRequest", {})
        additional_info["rulesChange"] = bool(filing.filing_json["filing"]["correction"].get("rulesFileKey"))
        additional_info["memorandumChange"] = bool(filing.filing_json["filing"]["correction"].get("memorandumFileKey"))

    return additional_info


def _get_dissolution_display_name(filing: Filing, filing_type: str, default: str) -> str | None:
    """Return the dissolution sub-type specific display name used in the subject and email title."""
    if filing_type != "dissolution":
        return None
    return {
        "voluntary": "Voluntary Dissolution Application",
        "administrative": "Dissolution Application",
    }.get(filing.filing_sub_type, default)


def _apply_certified_coop_dissolution_names(pdfs: list[dict], filing_type: str, legal_type: str) -> list[dict]:
    """Rename coop dissolution attachments to their certified titles."""
    if filing_type == "dissolution" and legal_type == Business.LegalTypes.COOP.value:
        certified_names = {"Affidavit.pdf": "Certified Affidavit.pdf",
                           "Special Resolution.pdf": "Certified Special Resolution.pdf"}
        for pdf in pdfs:
            pdf["fileName"] = certified_names.get(pdf["fileName"], pdf["fileName"])
    return pdfs


def _get_additional_recipients(filing: Filing, token: str) -> str | None:
    """Get additional recipients for a filing type."""
    submitter_recipient_filings = ["alteration", "changeOfRegistration", "dissolution", "specialResolution"]
    if filing.filing_type in submitter_recipient_filings:
        if filing.submitter_roles and UserRoles.staff in filing.submitter_roles:
            # when staff do filing documentOptionalEmail may contain completing party email
            return filing.filing_json["filing"]["header"].get("documentOptionalEmail")
        return get_user_email_from_auth(filing.filing_submitter.username, token)


def _get_attachments_and_extra_pdf_types(status: str, filing_type: str, filing: Filing, legal_type_key: str) -> tuple[list[str], list[str]]:
    """Get attachments for a filing type."""
    attachments = copy.deepcopy(FILING_ATTACHMENTS.get(legal_type_key, {}).get(filing_type, {}).get("attachments", []))
    extra_pdf_types = copy.deepcopy(FILING_ATTACHMENTS.get(legal_type_key, {}).get(filing_type, {}).get("extraPdfTypes", []))

    # filing sub type overrides attachments and extraPdfTypes if present
    if filing.filing_sub_type and (attachments_sub := copy.deepcopy(FILING_ATTACHMENTS.get(legal_type_key, {}).get(f"{filing_type}-{filing.filing_sub_type}", {}))):
        attachments = attachments_sub.get("attachments", [])
        extra_pdf_types = attachments_sub.get("extraPdfTypes", [])
    
    def _remove_from_list(list: list, value: str):
        """Remove the value from the list.
        Suppresses ValueError
        """
        with suppress(ValueError):
            list.remove(value)

    if filing_type not in Filing.TempCorpFilingType:
        # adjust attachments for some filings that have dynamic attachments based on the filing data
        additional_info = _get_additional_info(filing)
        if not additional_info.get("nameChange"):
            # remove con if in the attachments list
            _remove_from_list(attachments, "Certificate of Name Change")
            _remove_from_list(attachments, "Certificate of Name Change Correction")
            _remove_from_list(extra_pdf_types, "certificateOfNameChange")
            _remove_from_list(extra_pdf_types, "certificateOfNameCorrection")

        if not additional_info.get("rulesChange"):
            # remove cr if in the attachments list
            _remove_from_list(attachments, "Certified Rules")
            _remove_from_list(extra_pdf_types, "certifiedRules")
            
        if not additional_info.get("memorandumChange"):
            # remove cm if in the attachments list
            _remove_from_list(attachments, "Certified Memorandum")
            _remove_from_list(extra_pdf_types, "certifiedMemorandum")

    if status != Filing.Status.COMPLETED.value:
        extra_pdf_types = []

    return attachments, extra_pdf_types


def _skip_email_check(status: str, filing: Filing, legal_type: str, filing_name: str, business_identifier: str) -> bool:
    """Determine if the email should be skipped."""
    invalid_status = (status not in [Filing.Status.COMPLETED.value, Filing.Status.PAID.value]
                      or (status == Filing.Status.PAID.value and not filing.is_future_effective))
    invalid_data = not legal_type or not filing_name or not business_identifier
    skipped_coop_filing_types = ["annualReport", "changeOfDirectors", "changeOfAddress"]
    invalid_coop_filing = legal_type == Business.LegalTypes.COOP.value and filing.filing_type in skipped_coop_filing_types
    invalid_dissolution_filing = filing.filing_type == "dissolution" and filing.filing_sub_type == "delay"

    return invalid_status or invalid_data or invalid_coop_filing or invalid_dissolution_filing


def process(email_info: dict, token: str) -> dict | None:
    """Build the email the filing notification."""
    current_app.logger.debug("filing_notification: %s", email_info)
    filing_type, status = email_info["type"], email_info["option"]

    # get template vars from filing
    filing, business, leg_tmz_filing_date, leg_tmz_effective_date = get_filing_info(email_info["filingId"])

    filing_data = filing.json.get("filing", {}).get(filing_type, {})
    if filing_type in Filing.TempCorpFilingType and not business:
        # For new business filings, the nameRequest contains relevant business details.
        # We overwrite the business info from the nameRequest and then set the identifier back to the temp reg id.
        name_request = filing_data.get("nameRequest")
        business = name_request
        business["identifier"] = filing.temp_reg

    legal_type = business.get("legalType")
    filing_name = FILING_TITLE.get(filing_type)
    business_identifier = business.get("identifier")

    if _skip_email_check(status, filing, legal_type, filing_name, business_identifier):
        return

    dashboard_url = current_app.config.get("DASHBOARD_URL") + business_identifier

    is_future_effective_paid = filing.is_future_effective and status == Filing.Status.PAID.value
    if filing_type in Filing.TempCorpFilingType and is_future_effective_paid:
        business_identifier = NOT_AVAILABLE

    show_effective_date = filing.is_future_effective

    # businessName is added for FIRMs when legalName is set to the proprietor name or list of partners
    business_name = business.get("businessName") or business.get("legalName") or NOT_AVAILABLE
    filing_name_short = FILING_TITLE_SHORT.get(filing_type)
    legal_type_key = get_legal_type_key(legal_type)
    business_description = "Business"
    if corp_type := CorpType.find_by_id(legal_type):
        business_description: str = corp_type.full_desc.replace("BC ", "")

    business_number = None
    if len(business.get("taxId", "")) > 9:  # noqa: PLR2004
        # Only show if bn15 is saved, format for ux
        business_number = business["taxId"].replace("BC", " BC")

    # get template and fill in parts
    filled_template = get_filled_template(filing.filing_type, is_future_effective_paid)

    # dissolution emails must not show a placeholder business number line when there is no bn
    if not business_number and legal_type != Business.LegalTypes.COOP.value and filing_type != "dissolution":
        business_number = NOT_AVAILABLE

    # attachments and future attachments
    full_attachments_list, extra_pdf_types = _get_attachments_and_extra_pdf_types(status, filing_type, filing, legal_type_key)
    filing_attachment_name = full_attachments_list[0] if full_attachments_list else None
    pdfs = _apply_certified_coop_dissolution_names(
        get_pdfs(token, business, filing, extra_pdf_types, filing_attachment_name), filing_type, legal_type)

    # render template with vars
    attachments_list = [pdf["fileName"].replace(".pdf", "") for pdf in pdfs]
    jnja_template: Template = Template(filled_template, autoescape=True)
    rendered_template = jnja_template.render(
        ar_date=filing_data.get("annualReportDate","")[:4],
        filing_date_time=leg_tmz_filing_date,
        effective_date_time=leg_tmz_effective_date,
        entity_dashboard_url=dashboard_url,
        filing_sub_type=filing.filing_sub_type,
        filing_type=filing_type,
        attachments_list=attachments_list,
        business_description=business_description,
        business_name=business_name,
        business_identifier=business_identifier,
        business_number=business_number,
        filing_name=filing_name,
        filing_name_short=filing_name_short,
        dissolution_display_name=_get_dissolution_display_name(filing, filing_type, filing_name),
        future_attachments_list=full_attachments_list,
        office_name=OFFICE_NAME.get(legal_type_key),
        number_description="Registration" if legal_type_key == "FIRM" else "Incorporation",
        show_effective_date=show_effective_date,
    )

    # get recipients
    recipient_filing_type = None
    if filing_type in Filing.TempCorpFilingType or filing_type in ["changeOfRegistration", "correction", "dissolution"]:
        recipient_filing_type = filing_type

    recipients = get_recipients(status, filing.filing_json, token, recipient_filing_type)

    if filing_type == "dissolution" and (business_email := get_recipient_from_auth(business_identifier, token)):
        # dissolution also notifies the business contact email
        recipients = f"{recipients}, {business_email}" if recipients else business_email

    if additional_recipients := _get_additional_recipients(filing, token):
        recipients = f"{recipients}, {additional_recipients}"

    if not recipients:
        current_app.logger.error("No recipients found for filing notification email: %s", email_info)
        return

    # assign subject
    short_filing_name = FILING_TITLE_SHORT.get(filing_type) or filing_name
    if filing.filing_sub_type and isinstance(short_filing_name, dict):
        # This filing has different subjects based on the filing sub type
        short_filing_name = short_filing_name.get(filing.filing_sub_type) or filing_name

    subject = get_subject(is_future_effective_paid, business_name, legal_type,
                          _get_dissolution_display_name(filing, filing_type, filing_name) or filing_name,
                          short_filing_name)

    return {
        "recipients": recipients,
        "requestBy": "BCRegistries@gov.bc.ca",
        "content": {
            "subject": subject,
            "body": rendered_template,
            "attachments": pdfs
        }
    }
