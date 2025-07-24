import copy

from business_model.models import Filing, UserRoles
from document_record_service import (
    DocumentRecordService, 
    RequestInfo as DrsRequestInfo, 
    get_document_class,
    get_document_type
)
from flask import current_app

from business_filer.services import Flags

def sync_drs(filing_submission: Filing, flags: Flags): # noqa: PLR0915, PLR0912
    document_id_state = filing_submission.filing_json["filing"]["header"].get("documentIdState", {})
    legal_type = filing_submission.filing_json["filing"]["business"].get("legalType")
    submitter_roles = filing_submission.submitter_roles

    if  document_id_state and flags.is_on("enable-document-records"):
        filing_type = filing_submission.filing_json["filing"]["header"]["name"]
        temp_reg = filing_submission.temp_reg

        if filing_type in ["incorporationApplication", "continuationIn"]:
            # Get existing document on DRS
            doc_list = DocumentRecordService().get_document(
                DrsRequestInfo(
                    document_class=get_document_class(legal_type),
                    consumer_identifier=temp_reg
                )
            )

            if not isinstance(doc_list, list):
                current_app.logger.error(
                    f"No associated documents found for temporary registration ID: {temp_reg}"
                )
            else:
                # Update missing consumer document id
                if document_id_state["valid"] and document_id_state["consumerDocumentId"] == "":
                    copied_json = copy.deepcopy(filing_submission.filing_json)
                    copied_json["filing"]["header"]["documentIdState"]["consumerDocumentId"] = doc_list[0]["consumerDocumentId"]
                    filing_submission._filing_json = copied_json
                # Replace temp registration id with business identifier:
                for associated_document in doc_list:
                    doc_service_id = associated_document["documentServiceId"]
                    DocumentRecordService().update_document(
                        DrsRequestInfo(
                            document_service_id=doc_service_id,
                            consumer_identifier=filing_submission.filing_json["filing"]["business"]["identifier"],
                            consumer_reference_id=str(filing_submission.id)
                        )
                    )

        elif submitter_roles == UserRoles.staff:
            if filing_type and document_id_state["valid"]:
                try:
                    document_class = get_document_class(legal_type)
                    document_type = get_document_type(filing_type, legal_type)

                    response_json = DocumentRecordService().post_class_document(
                        request_info=DrsRequestInfo(
                            document_class=document_class,
                            document_type=document_type,
                            consumer_reference_id=filing_submission.id,
                            consumer_doc_id=document_id_state["consumerDocumentId"],
                            consumer_identifier=filing_submission.filing_json["filing"]["business"]["identifier"]
                        ),
                        has_file=False
                    )
                    if document_id_state["consumerDocumentId"] == "" and response_json:
                        # Update consumerDocumentId
                        copied_json = copy.deepcopy(filing_submission.filing_json)
                        copied_json["filing"]["header"]["documentIdState"]["consumerDocumentId"] = response_json["consumerDocumentId"]
                        filing_submission._filing_json = copied_json
                    else:
                        current_app.logger.error(
                            f"Document Record Creation Error: {filing_submission.id}, {response_json["rootCause"]}", exc_info=True)

                except Exception as error:
                    current_app.logger.error(f"Document Record Creation Error: {error}")                    
