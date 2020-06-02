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

"""Tests to assure the Document Meta Service.

Test-Suite to ensure that the Document Meta Service is working as expected.
"""

from legal_api.services import document_meta
from legal_api.utils.legislation_datetime import LegislationDatetime


def test_filing_status_documents_empty(app):
    """Assert that no documents are returned for non PAID and COMPLETED filing."""
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'NOT_PAID_OR_COMPLETE',
                    'name': 'changeOfAddress',
                    'availableOnPaperOnly': False,
                    'date': LegislationDatetime.now().isoformat()
                },
                'business': {
                    'identifier': 'BC1234567'
                }
            }
        }
        assert len(document_meta.get_documents(filing)) == 0


def test_paper_only_documents_empty(app):
    """Assert that no documents are returned for non PAID and COMPLETED filing."""
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'COMPLETED',
                    'name': 'changeOfAddress',
                    'availableOnPaperOnly': True,
                    'date': LegislationDatetime.now().isoformat()
                },
                'business': {
                    'identifier': 'BC1234567'
                }
            }
        }
        assert len(document_meta.get_documents(filing)) == 0


def test_ar_documents(app):
    """Assert that annual report documents are returned."""
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'COMPLETED',
                    'name': 'annualReport',
                    'availableOnPaperOnly': False,
                    'date': LegislationDatetime.now().isoformat()
                },
                'business': {
                    'identifier': 'BC1234567'
                }
            }
        }

        documents = document_meta.get_documents(filing)
        assert len(documents) == 1
        assert documents[0]['type'] == 'REPORT'
        assert documents[0]['reportType'] is None
        assert documents[0]['filingId'] == filing['filing']['header']['filingId']
        assert documents[0]['title'] == 'Annual Report'

        business_identifier = filing['filing']['business']['identifier']
        filing_date = filing['filing']['header']['date']
        filename = document_meta.get_general_filename(business_identifier, 'Annual Report', filing_date, 'pdf')
        assert documents[0]['filename'] == filename


def test_coa_documents(app):
    """Assert that change of address documents are returned."""
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'COMPLETED',
                    'name': 'changeOfAddress',
                    'availableOnPaperOnly': False,
                    'date': LegislationDatetime.now().isoformat()
                },
                'business': {
                    'identifier': 'BC1234567'
                }
            }
        }

        documents = document_meta.get_documents(filing)
        assert len(documents) == 1
        assert documents[0]['type'] == 'REPORT'
        assert documents[0]['reportType'] is None
        assert documents[0]['filingId'] == filing['filing']['header']['filingId']
        assert documents[0]['title'] == 'Address Change'

        business_identifier = filing['filing']['business']['identifier']
        filing_date = filing['filing']['header']['date']
        filename = document_meta.get_general_filename(business_identifier, 'Address Change', filing_date, 'pdf')
        assert documents[0]['filename'] == filename


def test_cod_documents(app):
    """Assert that change of directors documents are returned."""
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'COMPLETED',
                    'name': 'changeOfDirectors',
                    'availableOnPaperOnly': False,
                    'date': LegislationDatetime.now().isoformat()
                },
                'business': {
                    'identifier': 'BC1234567'
                }
            }
        }
        documents = document_meta.get_documents(filing)
        assert len(documents) == 1
        assert documents[0]['type'] == 'REPORT'
        assert documents[0]['reportType'] is None
        assert documents[0]['filingId'] == filing['filing']['header']['filingId']
        assert documents[0]['title'] == 'Director Change'

        business_identifier = filing['filing']['business']['identifier']
        filing_date = filing['filing']['header']['date']
        filename = document_meta.get_general_filename(business_identifier, 'Director Change', filing_date, 'pdf')
        assert documents[0]['filename'] == filename


def test_con_documents(app):
    """Assert that change of name documents are returned."""
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'COMPLETED',
                    'name': 'changeOfName',
                    'availableOnPaperOnly': False,
                    'date': LegislationDatetime.now().isoformat()
                },
                'business': {
                    'identifier': 'BC1234567'
                }
            }
        }
        documents = document_meta.get_documents(filing)
        assert len(documents) == 1
        assert documents[0]['type'] == 'REPORT'
        assert documents[0]['reportType'] is None
        assert documents[0]['filingId'] == filing['filing']['header']['filingId']
        assert documents[0]['title'] == 'Legal Name Change'

        business_identifier = filing['filing']['business']['identifier']
        filing_date = filing['filing']['header']['date']
        filename = document_meta.get_general_filename(business_identifier, 'Legal Name Change', filing_date, 'pdf')
        assert documents[0]['filename'] == filename


def test_special_resolution_documents(app):
    """Assert that special resolution documents are returned."""
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'COMPLETED',
                    'name': 'specialResolution',
                    'availableOnPaperOnly': False,
                    'date': LegislationDatetime.now().isoformat()
                },
                'business': {
                    'identifier': 'BC1234567'
                }
            }
        }
        documents = document_meta.get_documents(filing)
        assert len(documents) == 1
        assert documents[0]['type'] == 'REPORT'
        assert documents[0]['reportType'] is None
        assert documents[0]['filingId'] == filing['filing']['header']['filingId']
        assert documents[0]['title'] == 'Special Resolution'

        business_identifier = filing['filing']['business']['identifier']
        filing_date = filing['filing']['header']['date']
        filename = document_meta.get_general_filename(business_identifier, 'Special Resolution', filing_date, 'pdf')
        assert documents[0]['filename'] == filename


def test_voluntary_dissolution_documents(app):
    """Assert that voluntary dissolution documents are returned."""
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'COMPLETED',
                    'name': 'voluntaryDissolution',
                    'availableOnPaperOnly': False,
                    'date': LegislationDatetime.now().isoformat()
                },
                'business': {
                    'identifier': 'BC1234567'
                }
            }
        }
        documents = document_meta.get_documents(filing)
        assert len(documents) == 1
        assert documents[0]['type'] == 'REPORT'
        assert documents[0]['reportType'] is None
        assert documents[0]['filingId'] == filing['filing']['header']['filingId']
        assert documents[0]['title'] == 'Voluntary Dissolution'

        business_identifier = filing['filing']['business']['identifier']
        filing_date = filing['filing']['header']['date']
        filename = document_meta.get_general_filename(business_identifier, 'Voluntary Dissolution', filing_date, 'pdf')
        assert documents[0]['filename'] == filename


def test_incorporation_application_fed_documents(app):
    """Assert that voluntary dissolution documents are returned."""
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'COMPLETED',
                    'name': 'incorporationApplication',
                    'availableOnPaperOnly': False,
                    'effectiveDate': LegislationDatetime.tomorrow_midnight().isoformat(),
                    'date': LegislationDatetime.now().isoformat()
                },
                'business': {
                    'identifier': 'BC1234567'
                }
            }
        }
        documents = document_meta.get_documents(filing)

        assert len(documents) == 1
        assert documents[0]['type'] == 'REPORT'
        assert documents[0]['reportType'] is None
        assert documents[0]['filingId'] == filing['filing']['header']['filingId']
        assert documents[0]['title'] == 'Incorporation Application - Future Effective Incorporation'

        business_identifier = filing['filing']['business']['identifier']
        filing_date = filing['filing']['header']['date']
        filename = document_meta.get_general_filename(business_identifier,
                                                      'Incorporation Application (Future Effective)',
                                                      filing_date,
                                                      'pdf'
                                                      )
        assert documents[0]['filename'] == filename


def test_incorporation_application_documents(app):
    """Assert that voluntary dissolution documents are returned."""
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'COMPLETED',
                    'name': 'incorporationApplication',
                    'availableOnPaperOnly': False,
                    'effectiveDate': LegislationDatetime.now().isoformat(),
                    'date': LegislationDatetime.now().isoformat()
                },
                'business': {
                    'identifier': 'BC1234567'
                }
            }
        }
        documents = document_meta.get_documents(filing)
        assert len(documents) == 3
        assert documents[0]['type'] == 'REPORT'
        assert documents[0]['reportType'] is None
        assert documents[0]['filingId'] == filing['filing']['header']['filingId']
        assert documents[0]['title'] == 'Incorporation Application'

        business_identifier = filing['filing']['business']['identifier']
        filing_date = filing['filing']['header']['date']
        ia_filename = document_meta.get_general_filename(business_identifier,
                                                         'Incorporation Application',
                                                         filing_date,
                                                         'pdf'
                                                         )
        noa_filename = document_meta.get_general_filename(business_identifier,
                                                          'Notice of Articles',
                                                          filing_date,
                                                          'pdf'
                                                          )
        certificate_filename = document_meta.get_general_filename(business_identifier,
                                                                  'Certificate',
                                                                  filing_date,
                                                                  'pdf'
                                                                  )

        assert documents[0]['filename'] == ia_filename

        assert documents[1]['type'] == 'REPORT'
        assert documents[1]['reportType'] == 'noa'
        assert documents[1]['filingId'] == filing['filing']['header']['filingId']
        assert documents[1]['title'] == 'Notice of Articles'
        assert documents[1]['filename'] == noa_filename

        assert documents[2]['type'] == 'REPORT'
        assert documents[2]['reportType'] == 'certificate'
        assert documents[2]['filingId'] == filing['filing']['header']['filingId']
        assert documents[2]['title'] == 'Certificate'
        assert documents[2]['filename'] == certificate_filename
