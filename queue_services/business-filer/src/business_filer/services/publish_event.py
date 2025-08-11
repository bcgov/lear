import uuid
from datetime import UTC, datetime

# if TYPE_CHECKING:
from business_model.models import Business, Filing
from flask import Flask

from business_filer.common.filing import FilingTypes
from business_filer.common.services.flag_manager import flags
from business_filer.exceptions import PublishException
from business_filer.services import gcp_queue
from gcp_queue import SimpleCloudEvent, to_queue_message


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
    def publish_mras_email(app: Flask, business: Business, filing: Filing):
        """Publish MRAS email message onto the NATS emailer subject."""
        if flags.is_on("enable-sandbox"):
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
