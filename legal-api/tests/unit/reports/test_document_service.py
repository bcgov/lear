# Copyright © 2025 Province of British Columbia
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

"""Test-Suite to ensure that the Report class is working as expected."""
import copy
from datetime import datetime
from http import HTTPStatus
import datedelta
import json

import pytest

from legal_api.models import Filing
from legal_api.reports.document_service import DocumentService
from legal_api.reports.report import ReportMeta
from tests.unit.models import factory_business, factory_completed_filing
from registry_schemas.example_data import FILING_TEMPLATE


META_COLIN = {
  "colinFilingInfo": {
    "eventId": 7678798,
    "eventType": "FILE",
    "filingType": "NOCDR"
  }
}
META_MODERN = {}
DOCS_MODERN = {
  "documents": {
    "certificateOfIncorporation": "https://test.com/BC0888490/filings/2405954/documents/certificateOfIncorporation",
    "legalFilings": [
      {"incorporationApplication": "https://test.com/BC0888490/filings/2405954/documents/incorporationApplication"}
    ],
    "noticeOfArticles": "https://test.com/BC0888490/filings/2405954/documents/noticeOfArticles",
    "receipt": "https://test.com/BC0888490/filings/2405954/documents/receipt"
  }
}
DOCS_COLIN = {
  "documents": {
    "certificateOfIncorporation": "https://test.com/BC0791952/filings/515091/documents/certificateOfIncorporation",
    "legalFilings": [
      {"incorporationApplication": "https://test.com/BC0791952/filings/515091/documents/incorporationApplication"}
    ],
    "noticeOfArticles": "https://test.com/BC0791952/filings/515091/documents/noticeOfArticles",
    "receipt": "https://test.com/BC0791952/filings/515091/documents/receipt"
  }
}
DOCS_STATIC1 = {
  "documents": {
    "certificateOfIncorporation": "https://test.com/CP1044798/filings/233791/documents/certificateOfIncorporation",
    "certifiedMemorandum": "https://test.com/CP1044798/filings/233791/documents/certifiedMemorandum",
    "certifiedRules": "https://test.com/CP1044798/filings/233791/documents/certifiedRules",
    "legalFilings": [
      {"incorporationApplication": "https://test.com/CP1044798/filings/233791/documents/incorporationApplication"}
    ],
    "receipt": "https://test.com/CP1044798/filings/233791/documents/receipt"
  }
}
DOCS_STATIC2 = {
  "documents": {
    "certificateOfContinuation": "https://test.com/C9900863/filings/155753/documents/certificateOfContinuation",
    "legalFilings": [
      {"continuationIn": "https://test.com/C9900863/filings/155753/documents/continuationIn"}
    ],
    "noticeOfArticles": "https://test.com/C9900863/filings/155753/documents/noticeOfArticles",
    "receipt": "https://test.com/C9900863/filings/155753/documents/receipt",
    "staticDocuments": [
      {
        "name": "Unlimited Liability Corporation Information",
        "url": "https://test.com/C9900863/filings/155753/documents/static/DS0000100741"
      },
      {
        "name": "20250107-Authorization1.pdf",
        "url": "https://test.com/C9900863/filings/155753/documents/static/DS0000100740"
      }
    ]
  }
}
DRS_NONE = []
DRS_MODERN = [
  {
    "dateCreated": "2026-03-11T15:45:51+00:00",
    "datePublished": "2026-03-03T20:00:00+00:00",
    "entityIdentifier": "BC0888490",
    "eventIdentifier": 2405954,
    "identifier": "DSR0000100951",
    "name": "certificateOfIncorporation.pdf",
    "productCode": "BUSINESS",
    "reportType": "CERT",
    "url": ""
  },
  {
    "dateCreated": "2026-03-11T15:53:19+00:00",
    "datePublished": "2026-03-03T20:00:00+00:00",
    "entityIdentifier": "BC0888490",
    "eventIdentifier": 2405954,
    "identifier": "DSR0000100952",
    "name": "noticeOfArticles.pdf",
    "productCode": "BUSINESS",
    "reportType": "NOA",
    "url": ""
  },
  {
    "dateCreated": "2026-03-11T16:09:51+00:00",
    "datePublished": "2026-03-03T20:00:00+00:00",
    "entityIdentifier": "BC0888490",
    "eventIdentifier": 2405954,
    "identifier": "DSR0000100954",
    "name": "incorporationApplication.pdf",
    "productCode": "BUSINESS",
    "reportType": "FILING",
    "url": ""
  }
]
DRS_COLIN = [
  {
    "dateCreated": "2026-02-24T23:15:35+00:00",
    "datePublished": "2007-05-23T18:40:59+00:00",
    "entityIdentifier": "BC0791952",
    "eventIdentifier": 7678798,
    "identifier": "DSR0000100896",
    "name": "BC0791952-ICORP-RECEIPT.pdf",
    "productCode": "BUSINESS",
    "reportType": "RECEIPT",
    "url": ""
  },
  {
    "dateCreated": "2026-02-24T23:15:37+00:00",
    "datePublished": "2007-05-23T18:40:59+00:00",
    "entityIdentifier": "BC0791952",
    "eventIdentifier": 7678798,
    "identifier": "DSR0000100897",
    "name": "BC0791952-ICORP-FILING.pdf",
    "productCode": "BUSINESS",
    "reportType": "FILING",
    "url": ""
  },
  {
    "dateCreated": "2026-02-24T23:15:41+00:00",
    "datePublished": "2007-05-23T18:40:59+00:00",
    "entityIdentifier": "BC0791952",
    "eventIdentifier": 7678798,
    "identifier": "DSR0000100898",
    "name": "BC0791952-ICORP-NOA.pdf",
    "productCode": "BUSINESS",
    "reportType": "NOA",
    "url": ""
  },
  {
    "dateCreated": "2026-02-24T23:15:45+00:00",
    "datePublished": "2007-05-23T18:40:59+00:00",
    "entityIdentifier": "BC0791952",
    "eventIdentifier": 7678798,
    "identifier": "DSR0000100899",
    "name": "BC0791952-ICORP-CERT.pdf",
    "productCode": "BUSINESS",
    "reportType": "CERT",
    "url": ""
  }
]
DRS_STATIC1 = [
  {
    "consumerDocumentId": "0100000525",
    "dateCreated": "2026-03-11T19:19:32+00:00",
    "datePublished": "2026-01-22T00:00:00+00:00",
    "documentClass": "COOP",
    "documentType": "COOP_MEMORANDUM",
    "documentTypeDescription": "Cooperative Memorandum",
    "entityIdentifier": "CP1044798",
    "eventIdentifier": 233791,
    "identifier": "DS0000101630",
    "name": "",
    "url": ""
  },
  {
    "consumerDocumentId": "0100000526",
    "dateCreated": "2026-03-11T19:19:37+00:00",
    "datePublished": "2026-01-22T00:00:00+00:00",
    "documentClass": "COOP",
    "documentType": "COOP_RULES",
    "documentTypeDescription": "Cooperative Rules",
    "entityIdentifier": "CP1044798",
    "eventIdentifier": 233791,
    "identifier": "DS0000101631",
    "name": "",
    "url": ""
  }
]
DRS_STATIC2 = [
  {
    "consumerDocumentId": "0100000193",
    "dateCreated": "2025-01-07T16:11:59+00:00",
    "datePublished": "2025-01-07T20:00:00+00:00",
    "documentClass": "CORP",
    "documentType": "CNTA",
    "documentTypeDescription": "Continuation in Authorization",
    "entityIdentifier": "C9900863",
    "eventIdentifier": 155753,
    "identifier": "DS0000100740",
    "name": "20250107-Authorization1.pdf",
    "url": ""
  },
  {
    "consumerDocumentId": "0100000193",
    "dateCreated": "2025-01-07T16:12:05+00:00",
    "datePublished": "2025-01-07T20:00:00+00:00",
    "documentClass": "CORP",
    "documentType": "DIRECTOR_AFFIDAVIT",
    "documentTypeDescription": "Director Affidavit",
    "entityIdentifier": "C9900863",
    "eventIdentifier": 155753,
    "identifier": "DS0000100741",
    "name": "20250107-Affidavit.pdf",
    "url": ""
  }
]

# testdata pattern is ({description}, {doc_data}, {drs_data}, {receipt}, {filing}, {noa}, {cert}, {static})
TEST_FILING_UPDATE_DATA = [
    ("No docs", DOCS_MODERN, DRS_NONE, None, None, None, None, None),
    ("Modern docs", DOCS_MODERN, DRS_MODERN, None, "reportType=FILING&drsId=DSR0000100954", "reportType=NOA&drsId=DSR0000100952", "reportType=CERT&drsId=DSR0000100951", None),
    ("Colin docs", DOCS_COLIN, DRS_COLIN, "reportType=RECEIPT&drsId=DSR0000100896", "reportType=FILING&drsId=DSR0000100897", "reportType=NOA&drsId=DSR0000100898", "reportType=CERT&drsId=DSR0000100899", None),
    ("Static 1", DOCS_STATIC1, DRS_STATIC1, None, None, None, None, "documentClass=COOP&drsId=DS0000101630"),
    ("Static 2", DOCS_STATIC2, DRS_STATIC2, None, None, None, None, "documentClass=CORP&drsId=DS0000100741"),
]
# testdata pattern is ({description}, {doc_data}, {drs_data}, {receipt}, {filing}, {noa}, {cert}, {static}, {meta}, {filing_id})
TEST_BUSINESS_UPDATE_DATA = [
    ("No docs", DOCS_MODERN, DRS_NONE, None, None, None, None, None, META_MODERN, 2405954),
    ("Modern docs", DOCS_MODERN, DRS_MODERN, None, "reportType=FILING&drsId=DSR0000100954", "reportType=NOA&drsId=DSR0000100952", "reportType=CERT&drsId=DSR0000100951", None, META_MODERN, 2405954),
    ("Colin docs", DOCS_COLIN, DRS_COLIN, "reportType=RECEIPT&drsId=DSR0000100896", "reportType=FILING&drsId=DSR0000100897", "reportType=NOA&drsId=DSR0000100898", "reportType=CERT&drsId=DSR0000100899", None,  META_COLIN, 0),
    ("Static 1", DOCS_STATIC1, DRS_STATIC1, None, None, None, None, "documentClass=COOP&drsId=DS0000101630", META_MODERN, 233791),
    ("Static 2", DOCS_STATIC2, DRS_STATIC2, None, None, None, None, "documentClass=CORP&drsId=DS0000100741", META_MODERN, 155753),
]
# testdata pattern is ({has_data}, {report_key}, {report_type})
TEST_REPORT_META_DATA = [
    (False, "JUNK", None),
    (True, "amalgamationApplication", "FILING"),
    (True, "certificateOfAmalgamation", "CERT"),
    (True, "certificateOfIncorporation", "CERT"),
    (True, "incorporationApplication", "FILING"),
    (True, "noticeOfArticles", "NOA"),
    (True, "alteration", "FILING"),
    (True, "alterationNotice", "FILING"),
    (True, "transition", "FILING"),
    (True, "changeOfAddress", "FILING"),
    (True, "changeOfDirectors", "FILING"),
    (True, "annualReport", "FILING"),
    (True, "changeOfName", "FILING"),
    (True, "specialResolution", "FILING"),
    (True, "specialResolutionApplication", "FILING"),
    (True, "voluntaryDissolution", "FILING"),
    (True, "certificateOfNameChange", "CERT"),
    (True, "certificateOfNameCorrection", "CERT"),
    (True, "certificateOfDissolution", "CERT"),
    (True, "dissolution", "FILING"),
    (True, "registration", "FILING"),
    (True, "amendedRegistrationStatement", "FILING"),
    (True, "correctedRegistrationStatement", "FILING"),
    (True, "changeOfRegistration", "FILING"),
    (True, "correction", "FILING"),
    (True, "certificateOfRestoration", "CERT"),
    (True, "letterOfConsent", "FILING"),
    (True, "letterOfConsentAmalgamationOut", "FILING"),
    (True, "letterOfAgmExtension", "FILING"),
    (True, "letterOfAgmLocationChange", "FILING"),
    (True, "continuationIn", "FILING"),
    (True, "certificateOfContinuation", "CERT"),
    (True, "noticeOfWithdrawal", "FILING"),
    (True, "appointReceiver", "FILING"),
    (True, "ceaseReceiver", "FILING"),
    (True, "default", "FILING"),
]


@pytest.mark.parametrize("has_data,report_key,report_type", TEST_REPORT_META_DATA)
def test_report_meta_type(session, has_data, report_key, report_type):
    """Assert that DRS report type configuration is as expected."""
    report_meta = ReportMeta.reports.get(report_key)
    if not has_data:
        assert not report_meta
    else:
        assert report_meta
        assert report_meta.get("reportType") == report_type


@pytest.mark.parametrize("desc,doc_data,drs_data,receipt,filing,noa,cert,static", TEST_FILING_UPDATE_DATA)
def test_update_filing_docs(session, desc, doc_data, drs_data, receipt, filing, noa, cert,static):
    """Assert that updating filing output url's with DRS info works as expected."""
    doc_service: DocumentService = DocumentService()
    filing_docs = copy.deepcopy(doc_data)
    results = doc_service.update_document_list(drs_data, filing_docs)
    assert results
    text_results: str = json.dumps(results)
    if not receipt:
        assert text_results.find("reportType=RECEIPT") < 1
    else:
        assert text_results.find(receipt) > 0
    if not filing:
        assert text_results.find("reportType=FILING") < 1
    else:
        assert text_results.find(filing) > 0
    if not noa:
        assert text_results.find("reportType=NOA") < 1
    else:
        assert text_results.find(noa) > 0
    if not cert:
        assert text_results.find("reportType=CERT") < 1
    else:
        assert text_results.find(cert) > 0
    if not static:
        assert text_results.find("documentClass=") < 1
    else:
        assert text_results.find(static) > 0


@pytest.mark.parametrize("desc,doc_data,drs_data,receipt,filing,noa,cert,static,meta,filing_id", TEST_BUSINESS_UPDATE_DATA)
def test_update_ledger_docs(session, desc, doc_data, drs_data, receipt, filing, noa, cert,static, meta, filing_id):
    """Assert that updating business ledger filing output url's with DRS info works as expected."""
    doc_service: DocumentService = DocumentService()
    filing_docs = copy.deepcopy(doc_data)
    filing1: Filing = Filing()
    filing1.id = filing_id
    filing1._meta_data = meta  # pylint: disable=protected-access
    filing1.paper_only = False
    if filing_id == 0:
        filing1.source = filing1.Source.COLIN.value
    else:
        filing1.source = filing1.Source.LEAR.value
    results = doc_service.update_filing_documents(drs_data, filing_docs, filing1)
    assert results
    text_results: str = json.dumps(results)
    if not receipt:
        assert text_results.find("reportType=RECEIPT") < 1
    else:
        assert text_results.find(receipt) > 0
    if not filing:
        assert text_results.find("reportType=FILING") < 1
    else:
        assert text_results.find(filing) > 0
    if not noa:
        assert text_results.find("reportType=NOA") < 1
    else:
        assert text_results.find(noa) > 0
    if not cert:
        assert text_results.find("reportType=CERT") < 1
    else:
        assert text_results.find(cert) > 0
    if not static:
        assert text_results.find("documentClass=") < 1
    else:
        assert text_results.find(static) > 0


def test_create_document(session, mock_doc_service, mocker):
    mocker.patch('legal_api.services.AccountService.get_bearer_token', return_value='')
    founding_date = datetime.utcnow()
    business = factory_business('CP1234567', founding_date=founding_date)
    filing = copy.deepcopy(FILING_TEMPLATE)
    filing['filing']['header']['name'] = 'Involuntary Dissolution'
    completed_filing = \
        factory_completed_filing(business, filing, filing_date=founding_date + datedelta.datedelta(months=1))
    document_service = DocumentService()
    assert document_service.has_document(business.identifier, completed_filing.id, 'annualReport') == False
    response, status = document_service.create_document(business.identifier, completed_filing.id, 'annualReport', '3113', completed_filing.filing_type)
    assert status == HTTPStatus.CREATED
    assert response['identifier'] == 1
    assert response['url'] == 'https://document-service.com/document/1'
    assert document_service.has_document(business.identifier, completed_filing.id, 'annualReport') != False


def test_get_document(session, mock_doc_service, mocker):
    mocker.patch('legal_api.services.AccountService.get_bearer_token', return_value='')
    founding_date = datetime.utcnow()
    business = factory_business('CP1234567', founding_date=founding_date)
    filing = copy.deepcopy(FILING_TEMPLATE)
    filing['filing']['header']['name'] = 'Involuntary Dissolution'
    completed_filing = \
        factory_completed_filing(business, filing, filing_date=founding_date + datedelta.datedelta(months=1))
    document_service = DocumentService()
    assert document_service.has_document(business.identifier, completed_filing.id, 'annualReport') == False
    response, status = document_service.create_document(business.identifier, completed_filing.id, 'annualReport', '3113', completed_filing.filing_type)
    assert response
    response, status = document_service.get_document(business.identifier, completed_filing.id, 'annualReport', '3113')
    assert response
    assert status == HTTPStatus.OK
    assert document_service.has_document(business.identifier, completed_filing.id, 'annualReport') != False