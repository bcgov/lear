import copy
from flask import current_app

from business_model.models import Filing, UserRoles
from document_record_service import (
    DocumentRecordService, 
    RequestInfo as DrsRequestInfo, 
    get_document_class
)

from business_filer.services import Flags
from business_filer.services.publish_event import PublishEvent

def update_drs_with_busienss_id(filing_submission: Filing, flags: Flags, legal_type: str): # noqa: PLR0915, PLR0912
    document_id_state = filing_submission.filing_json["filing"]["header"].get("documentIdState", {})
    submitter_roles = filing_submission.submitter_roles

    if  document_id_state and flags.is_on("enable-document-records"):
        filing_type = filing_submission.filing_type
        temp_reg = filing_submission.temp_reg
        
        # Replace temp_reg with business_identifier for static documents(or staff filing)
        if (filing_type in ["incorporationApplication", "continuationIn"]
            or (
                # If a filing is created by staff on the UI with a temp ID, 
                # replace it with the business identifier
                submitter_roles == UserRoles.staff
                and document_id_state["valid"]
                and temp_reg
        )):
            # Get existing document on DRS
            doc_list = DocumentRecordService().get_document(
                DrsRequestInfo(
                    document_class=get_document_class(legal_type),
                    consumer_identifier=temp_reg
                )
            )

            if not isinstance(doc_list, list):
                current_app.logger.info(
                    f"No associated documents found for temporary registration ID: {temp_reg}"
                )
            else:
                # Update missing consumer document id
                if document_id_state["valid"] and document_id_state["consumerDocumentId"] == "":
                    copied_json = copy.deepcopy(filing_submission.filing_json)
                    copied_json["filing"]["header"]["documentIdState"]["consumerDocumentId"] = doc_list[0]["consumerDocumentId"]
                    filing_submission._filing_json = copied_json
                    current_app.logger.info(
                        f"Updated missing document id {doc_list[0]["consumerDocumentId"]}"
                    )
                # Replace temp registration id with business identifier:
                for associated_document in doc_list:
                    doc_service_id = associated_document["documentServiceId"]
                    PublishEvent.publish_drs_creation_event(current_app, 
                        DrsRequestInfo(
                            document_service_id=doc_service_id,
                            consumer_identifier=filing_submission.business_id,
                            consumer_reference_id=str(filing_submission.id)
                        ).json
                    )
