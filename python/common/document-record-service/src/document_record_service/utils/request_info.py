from urllib.parse import urlencode

from flask import request

# DRS request parameters
PARAM_ACCOUNT_ID = "Account-Id"
PARAM_ACCEPT = "Accept"
PARAM_CONTENT_TYPE = "Content-Type"
PARAM_QUERY_START_DATE = "queryStartDate"
PARAM_QUERY_END_DATE = "queryEndDate"
PARAM_FROM_UI = "fromUI"
PARAM_DOC_SERVICE_ID = "documentServiceId"
PARAM_CONSUMER_DOC_ID = "consumerDocumentId"
PARAM_CONSUMER_FILENAME = "consumerFilename"
PARAM_CONSUMER_FILEDATE = "consumerFilingDate"
PARAM_CONSUMER_IDENTIFIER = "consumerIdentifier"
PARAM_CONSUMER_REFERENCE_ID = "consumerReferenceId"
PARAM_DESCRIPTION = "description"
PARAM_DOCUMENT_TYPE = "documentType"
PARAM_DOCUMENT_CLASS = "documentClass"
PARAM_PAGE_NUMBER = "pageNumber"


class RequestInfo:
    """Contains parameter values and other common request information."""

    document_class: str = None
    document_type: str = None
    document_service_id: str = None
    consumer_doc_id: str = None
    consumer_filename: str = None
    consumer_filedate: str = None
    consumer_identifier: str = None
    consumer_reference_id: str = None

    def __init__(
        self,
        document_class: str = None,
        document_type: str = None,
        document_service_id: str = None,
        consumer_doc_id: str = None,
        consumer_filename: str = None,
        consumer_filedate: str = None,
        consumer_identifier: str = None,
        consumer_reference_id: str = None,
    ):
        """Set common base initialization."""
        self.document_class = document_class
        self.document_type = document_type
        self.document_service_id = document_service_id
        self.consumer_reference_id = consumer_reference_id
        self.consumer_doc_id = consumer_doc_id
        self.consumer_filename = consumer_filename
        self.consumer_filedate = consumer_filedate
        self.consumer_identifier = consumer_identifier

    @property
    def json(self) -> dict:
        """Return the request info as a JSON object, excluding None values."""
        field_map = {
            "documentServiceId": self.document_service_id,
            "consumerDocumentId": self.consumer_doc_id,
            "consumerFilename": self.consumer_filename,
            "consumerFilingDate": self.consumer_filedate,
            "consumerIdentifier": self.consumer_identifier,
            "consumerReferenceId": self.consumer_reference_id,
            "documentType": self.document_type,
            "documentClass": self.document_class,
        }
        return {k: v for k, v in field_map.items() if v is not None}

    @property
    def url_params(self) -> str:
        field_mapping = {
            "consumer_doc_id": "consumerDocumentId",
            "consumer_filename": "consumerFilename",
            "consumer_filedate": "consumerFiledate",
            "consumer_identifier": "consumerIdentifier",
            "consumer_reference_id": "consumerReferenceId",
            "document_service_id": "documentServiceId",
            "document_type": "documentType",
            # 'document_class' is intentionally excluded
        }

        params = {
            url_key: getattr(self, attr) for attr, url_key in field_mapping.items() if getattr(self, attr) is not None
        }

        return urlencode(params)


def get_request_info(req: request, info: RequestInfo) -> RequestInfo:  # type: ignore
    """Extract header and query parameters from the request."""
    # TODO: [DRS] Make sure account_id and key will be passed from request.
    # info.from_ui = req.args.get(PARAM_FROM_UI, False)
    # info.account_id = req.headers.get(PARAM_ACCOUNT_ID)
    # info.accept = req.headers.get(PARAM_ACCEPT)
    # info.content_type = req.headers.get(PARAM_CONTENT_TYPE)
    info.document_service_id = req.args.get(PARAM_DOC_SERVICE_ID)
    info.consumer_doc_id = req.args.get(PARAM_CONSUMER_DOC_ID)
    info.consumer_filename = req.args.get(PARAM_CONSUMER_FILENAME)
    info.consumer_filedate = req.args.get(PARAM_CONSUMER_FILEDATE)
    info.consumer_identifier = req.args.get(PARAM_CONSUMER_IDENTIFIER)
    info.consumer_reference_id = req.args.get(PARAM_CONSUMER_REFERENCE_ID)

    return info
