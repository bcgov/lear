import re
import uuid
from datetime import UTC, datetime

# if TYPE_CHECKING:
from business_model.models import Business, Document, Filing
from flask import Flask

from business_filer.common.filing import FilingTypes
from business_filer.exceptions import PublishException
from business_filer.services import Flags, gcp_queue
from gcp_queue import SimpleCloudEvent, to_queue_message

# DRS keys are formatted as "{documentClass}-{documentServiceId}", e.g. "COOP-DS0000101951".
# Legacy Minio keys (UUIDs) do not match this pattern.
_DRS_KEY_PATTERN = re.compile(r"^[A-Z]+-DS\d+$")


class PublishEvent:
    """Service to publish specific events onto the GCP Queue."""

    @staticmethod
    def publish_email_message(app: Flask, business: Business, filing: Filing, option: str = "PAID"):
        """Publish the email message."""
        try:
            subject = app.config.get("BUSINESS_MAILER_TOPIC")
            data = {"email": {"filingId": filing.id, "type": filing.filing_type, "option": option}}

            ce = PublishEvent._create_cloud_event(app, business, filing, subject, data)

            gcp_queue.publish(subject, to_queue_message(ce))
        except Exception as err:  # pylint: disable=broad-except;
            raise PublishException(err) from err

    @staticmethod
    def publish_event(app: Flask, business: Business, filing: Filing):
        """Publish the filing message onto the GCP-QUEUE filing subject."""
        try:
            subject = app.config.get("BUSINESS_EVENTS_TOPIC")

            identifier = business.identifier if business else (
                filing.temp_reg or 
                (filing.json or {}).get("filing", {}).get("business", {}).get("identifier")
            )
            data = {
                "filing": {
                    "header": {
                        "filingId": filing.id,
                        "effectiveDate": filing.effective_date.isoformat()
                    },
                    "business": {"identifier": identifier},
                    "legalFilings": filing.legal_filings()
                },
                "identifier": identifier
            }
            if filing.temp_reg:
                data["tempidentifier"] = filing.temp_reg

            ce = PublishEvent._create_cloud_event(app, business, filing, subject, data)
            gcp_queue.publish(subject, to_queue_message(ce))

        except Exception as err:  # pylint: disable=broad-except;
            raise PublishException(err) from err
    
    @staticmethod
    def publish_drs_create_message(app: Flask, business: Business, filing: Filing):
        """Publish the drs create record message."""
        try:
            subject = app.config.get("DOC_CREATE_REC_TOPIC")
            document_id = filing.filing_json["filing"][filing.filing_type].get("documentId", "")
            data = {
                "accountId": "business-api",
                "consumerDocumentId": document_id,
                "consumerIdentifier": business.identifier,
                "consumerFilingType": filing.filing_type,
                "consumerReferenceId": str(filing.id),
                "documentClass": "CORP"
            }

            ce = PublishEvent._create_cloud_event(app, business, filing, subject, data)
            gcp_queue.publish(subject, to_queue_message(ce))

        except Exception as err:  # pylint: disable=broad-except;
            raise PublishException(err) from err

    @staticmethod
    def publish_drs_update_message(app: Flask, business: Business, filing: Filing):
        """Publish a drs update record message for each DRS document uploaded with the filing.

        Updates the document record(s) with filing/business information once a filing completes,
        so the document shows up correctly in the ledger and is searchable in the DRS UI.
        """
        try:
            subject = app.config.get("DOC_UPDATE_REC_TOPIC")
            documents = Document.query.filter_by(filing_id=filing.id).all()
            for document in documents:
                if not PublishEvent._is_drs_document(document.file_key):
                    continue
                data = {
                    "accountId": "business-api",
                    "fileKey": document.file_key,
                    "businessIdentifier": business.identifier if business else None,
                    "filingDate": filing.completion_date.isoformat() if filing.completion_date else None,
                    "filingId": filing.id
                }
                data = {k: v for k, v in data.items() if v is not None}

                ce = PublishEvent._create_cloud_event(app, business, filing, subject, data)
                gcp_queue.publish(subject, to_queue_message(ce))

        except Exception as err:  # pylint: disable=broad-except;
            raise PublishException(err) from err

    @staticmethod
    def _is_drs_document(file_key: str) -> bool:
        """Return True if the file_key is a DRS key."""
        return bool(file_key) and bool(_DRS_KEY_PATTERN.match(file_key))

    @staticmethod
    def publish_mras_email(app: Flask, business: Business, filing: Filing):
        """Publish MRAS email message onto the NATS emailer subject."""
        if Flags.is_on("enable-sandbox"):
            app.logger.info("Skip publishing MRAS email")
            return


        if filing.filing_type in [
            FilingTypes.AMALGAMATIONAPPLICATION,
            FilingTypes.CONTINUATIONIN,
            FilingTypes.INCORPORATIONAPPLICATION
        ]:
            try:
                subject = app.config.get("BUSINESS_MAILER_TOPIC")
                data = {"email": {"filingId": filing.id, "type": filing.filing_type, "option": "mras"}}
                ce = PublishEvent._create_cloud_event(app, business, filing, subject, data)
                gcp_queue.publish(subject, to_queue_message(ce))
            except Exception as err:  # pylint: disable=broad-except;
                raise PublishException(err) from err

    @staticmethod
    def _create_cloud_event(app: Flask, business: Business, filing: Filing, subject: str, data: dict):
        """Create the cloud event."""
        identifier = business.identifier if business else (
            filing.temp_reg or 
            (filing.json or {}).get("filing", {}).get("business", {}).get("identifier")
        )

        ce = SimpleCloudEvent(
                id=str(uuid.uuid4()),
                source="".join([
                    app.config.get("LEGAL_API_URL"),
                    "/business/",
                    identifier,
                    "/filing/",
                    str(filing.id)]),
                subject=subject,
                time=datetime.now(UTC),
                type="bc.registry.business." + filing.filing_type,
                data=data
            )
        return ce
