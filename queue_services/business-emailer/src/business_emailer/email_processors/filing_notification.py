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

from flask import current_app
from jinja2 import Template

from business_emailer.email_processors import (
    get_filing_info,
    get_filled_template,
    get_pdfs,
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

    return additional_info


def _get_additional_recipients(filing: Filing, token: str) -> str:
    """Get additional recipients for a filing type."""
    recipients = None
    submitter_recipient_filings = ["alteration", "changeOfRegistration", "dissolution", "specialResolution"]
    if filing.filing_type in submitter_recipient_filings:
        optional_email = filing.filing_json["filing"]["header"].get("documentOptionalEmail")
        if filing.submitter_roles and UserRoles.staff in filing.submitter_roles and optional_email:
            # when staff do filing documentOptionalEmail may contain completing party email
            recipients = f"{recipients}, {optional_email}"
        else:
            user_email = get_user_email_from_auth(filing.filing_submitter.username, token)
            recipients = f"{recipients}, {user_email}"

    return recipients


def _get_attachments_and_extra_pdf_types(status: str, filing_type: str, filing: Filing, legal_type_key: str) -> tuple[list[str], list[str]]:
    """Get attachments for a filing type."""
    attachments = FILING_ATTACHMENTS.get(legal_type_key, {}).get(filing_type, {}).get("attachments", [])
    extra_pdf_types = FILING_ATTACHMENTS.get(legal_type_key, {}).get(filing_type, {}).get("extraPdfTypes", [])
    if (_get_additional_info(filing).get("nameChange", False)
        and (attachments_con := FILING_ATTACHMENTS.get(legal_type_key, {}).get(f"{filing_type}-con", {}))
    ):
        attachments = attachments_con.get("attachments", [])
        extra_pdf_types = attachments_con.get("extraPdfTypes", [])

    if status != Filing.Status.COMPLETED.value:
        extra_pdf_types = []

    return attachments, extra_pdf_types


def process(email_info: dict, token: str) -> dict | None:
    """Build the email the filing notification."""
    current_app.logger.debug("filing_notification: %s", email_info)
    filing_type, status = email_info["type"], email_info["option"]
    # get template vars from filing
    filing, business, leg_tmz_filing_date, leg_tmz_effective_date = get_filing_info(email_info["filingId"])
    
    if status == Filing.Status.PAID.value and not filing.is_future_effective:
        # We no longer send an email for this case
        return

    new_business_filings = ["amalgamationApplication", "continuationIn", "incorporationApplication", "registration"]
    filing_data = filing.json.get("filing", {}).get(filing_type, {})
    if filing_type in new_business_filings and not business:
        # For new business filings, the nameRequest contains relevant business details.
        # We overwrite the business info from the nameRequest and then set the identifier back to the temp reg id.
        name_request = filing_data.get("nameRequest")
        business = name_request
        business["identifier"] = filing.temp_reg

    legal_type = business.get("legalType")
    filing_name = FILING_TITLE.get(filing_type)
    business_identifier = business.get("identifier")
    if not legal_type or not filing_name or not business_identifier:
        # Should never happen - log and return. It will be skipped.
        current_app.logger.error("Missing legal_type, identifier and/or filing_name. Email: %s", email_info)
        return
    
    skipped_coop_filing_types = ["changeOfDirectors", "changeOfAddress"]
    if legal_type == Business.LegalTypes.COOP.value and filing_type in skipped_coop_filing_types:
        return

    dashboard_url = current_app.config.get("DASHBOARD_URL") + business_identifier

    is_future_effective_paid = filing.is_future_effective and status == Filing.Status.PAID.value
    if filing_type in new_business_filings and is_future_effective_paid:
        business_identifier = NOT_AVAILABLE

    show_effective_date = filing.is_future_effective
    business_name = business.get("legalName") or NOT_AVAILABLE
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

    if not business_number and legal_type != Business.LegalTypes.COOP.value:
        business_number = NOT_AVAILABLE

    # attachments and future attachments
    future_attachments, extra_pdf_types = _get_attachments_and_extra_pdf_types(status, filing_type, filing, legal_type_key)

    pdfs = get_pdfs(token, business, filing, leg_tmz_filing_date, leg_tmz_effective_date, extra_pdf_types)

    # render template with vars
    attachments_list = [pdf["fileName"].replace(".pdf", "") for pdf in pdfs]
    jnja_template: Template = Template(filled_template, autoescape=True)
    rendered_template = jnja_template.render(
        ar_date=filing_data.get("annualReportDate","")[:4],
        filing_date_time=leg_tmz_filing_date,
        effective_date_time=leg_tmz_effective_date,
        entity_dashboard_url=dashboard_url,
        filing_type=filing_type,
        attachments_list=attachments_list,
        business_description=business_description,
        business_name=business_name,
        business_identifier=business_identifier,
        business_number=business_number,
        filing_name=filing_name,
        filing_name_short=filing_name_short,
        future_attachments_list=future_attachments,
        office_name=OFFICE_NAME.get(legal_type_key),
        number_description="Registration" if legal_type_key == "FIRM" else "Incorporation",
        show_effective_date=show_effective_date,
    )

    # get recipients
    recipient_filing_type = None
    if filing_type in ["incorporationApplication", "registration", "changeOfRegistration"]:
        recipient_filing_type = filing_type

    recipients = get_recipients(status, filing.filing_json, token, recipient_filing_type)

    if additional_recipients := _get_additional_recipients(filing, token):
        recipients = f"{recipients}, {additional_recipients}"

    if not recipients:
        current_app.logger.error("No recipients found for filing notification email: %s", email_info)
        return

    # assign subject
    short_filing_name = FILING_TITLE_SHORT.get(filing_type) or filing_name
    subject = get_subject(is_future_effective_paid, business_name, legal_type, filing_name, short_filing_name)

    return {
        "recipients": recipients,
        "requestBy": "BCRegistries@gov.bc.ca",
        "content": {
            "subject": subject,
            "body": rendered_template,
            "attachments": pdfs
        }
    }
