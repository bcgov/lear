
import pytest
import requests_mock
from flask import current_app
from legal_api.reports.document_service import DocumentService, ReportTypes

@pytest.mark.parametrize('report_type, expected_certified', [
    # Legal Filings and Notices of Articles are official summaries that must be certified 
    # as they represent the "state of record" for a business.
    (ReportTypes.FILING.value, True),
    (ReportTypes.FILING_2.value, True),
    (ReportTypes.NOA.value, True),
    
    # FILING-3 is used for Letters (e.g., Letter of Consent). These are correspondence
    # items where a "Certified Copy" stamp is not appropriate and can obscure text.
    (ReportTypes.FILING_3.value, False),
    
    # Receipts are financial records and should not be stamped with a "Certified Copy" watermark.
    (ReportTypes.RECEIPT.value, False),
])
def test_get_filing_report_url_params(app, mocker, report_type, expected_certified):
    """
    Verify that the Document Service correctly decides whether to request a 'Certified Copy'.
    
    This is critical because the downstream Document Retrieval Service (DRS) uses the 
    'certifiedCopy' query parameter to burn a permanent watermark into the PDF binary.
    """
    mocker.patch('legal_api.services.AccountService.get_bearer_token', return_value='fake-token')
    with app.app_context():
        doc_service = DocumentService()
        drs_id = "test-drs-id"
        
        with requests_mock.Mocker() as m:
            base_url = current_app.config.get("DOCUMENT_SVC_URL").replace("/documents", "")
            product = current_app.config.get("DOCUMENT_PRODUCT_CODE")
            
            # Construct the expected URL based on the logic we are testing
            if expected_certified:
                expected_url = f"{base_url}/application-reports/{product}/{drs_id}?certifiedCopy=true"
            else:
                expected_url = f"{base_url}/application-reports/{product}/{drs_id}"
            
            m.get(expected_url, status_code=200, content=b"pdf-binary-data")
            
            response = doc_service.get_filing_report(drs_id, report_type)
            
            # Verification:
            # 1. The service reached the correct endpoint with the correct parameters
            assert m.request_history[-1].url == expected_url
            # 2. The binary data is returned correctly regardless of the stamp status
            assert response.content == b"pdf-binary-data"
