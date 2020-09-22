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
from unittest.mock import patch

from legal_api.services import DocumentMetaService, NameXService
from tests.unit.models import factory_business


FILING_DATE = '2020-07-14T11:41:07.230473-07:00'
COA_TITLE = 'Address Change'
NOA_TITLE = 'Notice of Articles'
NOA_FILENAME = 'BC1234567 - Notice of Articles - 2020-07-14.pdf'
COD_TITLE = 'Director Change'
CON_TITLE = 'Legal Name Change'


def test_business_not_found(session, app):
    """Assert that no documents are returned when the filing's business is not found."""
    document_meta = DocumentMetaService()
    factory_business(identifier='BC1234567', entity_type='BC')
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'DONT_CARE',
                    'name': 'changeOfAddress',
                    'availableOnPaperOnly': False,
                    'date': FILING_DATE
                },
                'business': {
                    'identifier': 'BC7654321'
                }
            }
        }
        assert len(document_meta.get_documents(filing)) == 0
        # also verify document class properties:
        assert document_meta._business_identifier == 'BC7654321'
        assert document_meta._legal_type is None


def test_wrong_filing_status(session, app):
    """Assert that no documents are returned for a non- PAID and COMPLETED filing."""
    document_meta = DocumentMetaService()
    factory_business(identifier='BC1234567', entity_type='BC')
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'NOT_PAID_OR_COMPLETE',
                    'name': 'changeOfAddress',
                    'availableOnPaperOnly': False,
                    'date': FILING_DATE
                },
                'business': {
                    'identifier': 'BC1234567'
                }
            }
        }
        assert len(document_meta.get_documents(filing)) == 0
        # also verify document class properties:
        assert document_meta._business_identifier == 'BC1234567'
        assert document_meta._legal_type == 'BC'


def test_available_on_paper_only(session, app):
    """Assert that no documents are returned for a paper-only filing."""
    document_meta = DocumentMetaService()
    factory_business(identifier='BC1234567', entity_type='BC')
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'COMPLETED',
                    'name': 'changeOfAddress',
                    'availableOnPaperOnly': True,
                    'date': FILING_DATE
                },
                'business': {
                    'identifier': 'BC1234567'
                }
            }
        }
        assert len(document_meta.get_documents(filing)) == 0


def test_coa_paid(session, app):
    """Assert that an Address Change document is returned for a PAID COA filing."""
    document_meta = DocumentMetaService()
    factory_business(identifier='BC1234567', entity_type='BC')
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'PAID',
                    'name': 'changeOfAddress',
                    'availableOnPaperOnly': False,
                    'date': FILING_DATE
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
        assert documents[0]['filingId'] == 12356
        assert documents[0]['title'] == COA_TITLE
        assert documents[0]['filename'] == 'BC1234567 - Address Change - 2020-07-14.pdf'


def test_coa_completed_bc(session, app):
    """Assert that Address Change + NOA documents are returned for a COMPLETED BCOMP COA filing."""
    document_meta = DocumentMetaService()
    factory_business(identifier='BC1234567', entity_type='BC')
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'COMPLETED',
                    'name': 'changeOfAddress',
                    'availableOnPaperOnly': False,
                    'date': FILING_DATE
                },
                'business': {
                    'identifier': 'BC1234567'
                }
            }
        }
        documents = document_meta.get_documents(filing)
        assert len(documents) == 2

        assert documents[0]['type'] == 'REPORT'
        assert documents[0]['reportType'] is None
        assert documents[0]['filingId'] == 12356
        assert documents[0]['title'] == COA_TITLE
        assert documents[0]['filename'] == 'BC1234567 - Address Change - 2020-07-14.pdf'

        assert documents[1]['type'] == 'REPORT'
        assert documents[1]['reportType'] == 'noa'
        assert documents[1]['filingId'] == 12356
        assert documents[1]['title'] == NOA_TITLE
        assert documents[1]['filename'] == NOA_FILENAME


def test_coa_completed_cp(session, app):
    """Assert that an Address Change document is returned for a COMPLETED COOP COA filing."""
    document_meta = DocumentMetaService()
    factory_business(identifier='CP1234567', entity_type='CP')
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'COMPLETED',
                    'name': 'changeOfAddress',
                    'availableOnPaperOnly': False,
                    'date': FILING_DATE
                },
                'business': {
                    'identifier': 'CP1234567'
                }
            }
        }
        documents = document_meta.get_documents(filing)
        assert len(documents) == 1

        assert documents[0]['type'] == 'REPORT'
        assert documents[0]['reportType'] is None
        assert documents[0]['filingId'] == 12356
        assert documents[0]['title'] == COA_TITLE
        assert documents[0]['filename'] == 'CP1234567 - Address Change - 2020-07-14.pdf'


def test_ar(session, app):
    """Assert that an Annual Report document is returned for an AR filing."""
    document_meta = DocumentMetaService()
    factory_business(identifier='BC1234567', entity_type='BC')
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'COMPLETED',
                    'name': 'annualReport',
                    'availableOnPaperOnly': False,
                    'date': FILING_DATE
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
        assert documents[0]['filingId'] == 12356
        assert documents[0]['title'] == 'Annual Report'
        assert documents[0]['filename'] == 'BC1234567 - Annual Report - 2020-07-14.pdf'


def test_cod_paid(session, app):
    """Assert that a Director Change document is returned for a PAID COD filing."""
    document_meta = DocumentMetaService()
    factory_business(identifier='BC1234567', entity_type='BC')
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'PAID',
                    'name': 'changeOfDirectors',
                    'availableOnPaperOnly': False,
                    'date': FILING_DATE
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
        assert documents[0]['filingId'] == 12356
        assert documents[0]['title'] == COD_TITLE
        assert documents[0]['filename'] == 'BC1234567 - Director Change - 2020-07-14.pdf'


def test_cod_completed_bc(session, app):
    """Assert that Director Change + NOA documents are returned for a COMPLETED BCOMP COD filing."""
    document_meta = DocumentMetaService()
    factory_business(identifier='BC1234567', entity_type='BC')
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'COMPLETED',
                    'name': 'changeOfDirectors',
                    'availableOnPaperOnly': False,
                    'date': FILING_DATE
                },
                'business': {
                    'identifier': 'BC1234567'
                }
            }
        }
        documents = document_meta.get_documents(filing)
        assert len(documents) == 2

        assert documents[0]['type'] == 'REPORT'
        assert documents[0]['reportType'] is None
        assert documents[0]['filingId'] == 12356
        assert documents[0]['title'] == COD_TITLE
        assert documents[0]['filename'] == 'BC1234567 - Director Change - 2020-07-14.pdf'

        assert documents[1]['type'] == 'REPORT'
        assert documents[1]['reportType'] == 'noa'
        assert documents[1]['filingId'] == 12356
        assert documents[1]['title'] == NOA_TITLE
        assert documents[1]['filename'] == NOA_FILENAME


def test_cod_completed_cp(session, app):
    """Assert that a Director Change document is returned for a COMPLETED COOP COD filing."""
    document_meta = DocumentMetaService()
    factory_business(identifier='CP1234567', entity_type='CP')
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'COMPLETED',
                    'name': 'changeOfDirectors',
                    'availableOnPaperOnly': False,
                    'date': FILING_DATE
                },
                'business': {
                    'identifier': 'CP1234567'
                }
            }
        }
        documents = document_meta.get_documents(filing)
        assert len(documents) == 1

        assert documents[0]['type'] == 'REPORT'
        assert documents[0]['reportType'] is None
        assert documents[0]['filingId'] == 12356
        assert documents[0]['title'] == COD_TITLE
        assert documents[0]['filename'] == 'CP1234567 - Director Change - 2020-07-14.pdf'


def test_con_paid(session, app):
    """Assert that a Legal Name Change document is returned for a PAID CON filing."""
    document_meta = DocumentMetaService()
    factory_business(identifier='BC1234567', entity_type='BC')
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'PAID',
                    'name': 'changeOfName',
                    'availableOnPaperOnly': False,
                    'date': FILING_DATE
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
        assert documents[0]['filingId'] == 12356
        assert documents[0]['title'] == CON_TITLE
        assert documents[0]['filename'] == 'BC1234567 - Legal Name Change - 2020-07-14.pdf'


def test_con_completed_bc(session, app):
    """Assert that Legal Name Change + NOA documents are returned for a COMPLETED BCOMP CON filing."""
    document_meta = DocumentMetaService()
    factory_business(identifier='BC1234567', entity_type='BC')
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'COMPLETED',
                    'name': 'changeOfName',
                    'availableOnPaperOnly': False,
                    'date': FILING_DATE
                },
                'business': {
                    'identifier': 'BC1234567'
                }
            }
        }
        documents = document_meta.get_documents(filing)
        assert len(documents) == 2

        assert documents[0]['type'] == 'REPORT'
        assert documents[0]['reportType'] is None
        assert documents[0]['filingId'] == 12356
        assert documents[0]['title'] == CON_TITLE
        assert documents[0]['filename'] == 'BC1234567 - Legal Name Change - 2020-07-14.pdf'

        assert documents[1]['type'] == 'REPORT'
        assert documents[1]['reportType'] == 'noa'
        assert documents[1]['filingId'] == 12356
        assert documents[1]['title'] == NOA_TITLE
        assert documents[1]['filename'] == NOA_FILENAME


def test_con_completed_cp(session, app):
    """Assert that a Legal Name Change document is returned for a COMPLETED COOP CON filing."""
    document_meta = DocumentMetaService()
    factory_business(identifier='CP1234567', entity_type='CP')
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'COMPLETED',
                    'name': 'changeOfName',
                    'availableOnPaperOnly': False,
                    'date': FILING_DATE
                },
                'business': {
                    'identifier': 'CP1234567'
                }
            }
        }
        documents = document_meta.get_documents(filing)
        assert len(documents) == 1

        assert documents[0]['type'] == 'REPORT'
        assert documents[0]['reportType'] is None
        assert documents[0]['filingId'] == 12356
        assert documents[0]['title'] == CON_TITLE
        assert documents[0]['filename'] == 'CP1234567 - Legal Name Change - 2020-07-14.pdf'


def test_special_resolution_paid(session, app):
    """Assert that no documents are returned for a PAID Special Resolution filing."""
    document_meta = DocumentMetaService()
    factory_business(identifier='BC1234567', entity_type='BC')
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'PAID',
                    'name': 'specialResolution',
                    'availableOnPaperOnly': False,
                    'date': FILING_DATE
                },
                'business': {
                    'identifier': 'BC1234567'
                }
            }
        }
        documents = document_meta.get_documents(filing)
        assert len(documents) == 0


def test_special_resolution_completed(session, app):
    """Assert that a Special Resolution document is returned for a COMPLETED Special Resolution filing."""
    document_meta = DocumentMetaService()
    factory_business(identifier='BC1234567', entity_type='BC')
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'COMPLETED',
                    'name': 'specialResolution',
                    'availableOnPaperOnly': False,
                    'date': FILING_DATE
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
        assert documents[0]['filingId'] == 12356
        assert documents[0]['title'] == 'Special Resolution'
        assert documents[0]['filename'] == 'BC1234567 - Special Resolution - 2020-07-14.pdf'


def test_voluntary_dissolution_paid(session, app):
    """Assert that no documents are returned for a PAID Voluntary Dissolution filing."""
    document_meta = DocumentMetaService()
    factory_business(identifier='BC1234567', entity_type='BC')
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'PAID',
                    'name': 'voluntaryDissolution',
                    'availableOnPaperOnly': False,
                    'date': FILING_DATE
                },
                'business': {
                    'identifier': 'BC1234567'
                }
            }
        }
        documents = document_meta.get_documents(filing)
        assert len(documents) == 0


def test_voluntary_dissolution_completed(session, app):
    """Assert that a Voluntary Dissolution document is returned for a COMPLETED Voluntary Dissolution filing."""
    document_meta = DocumentMetaService()
    factory_business(identifier='BC1234567', entity_type='BC')
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'COMPLETED',
                    'name': 'voluntaryDissolution',
                    'availableOnPaperOnly': False,
                    'date': FILING_DATE
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
        assert documents[0]['filingId'] == 12356
        assert documents[0]['title'] == 'Voluntary Dissolution'
        assert documents[0]['filename'] == 'BC1234567 - Voluntary Dissolution - 2020-07-14.pdf'


def test_correction(session, app):
    """Assert that no documents are returned for a Correction filing."""
    document_meta = DocumentMetaService()
    factory_business(identifier='BC1234567', entity_type='BC')
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'COMPLETED',
                    'name': 'correction',
                    'availableOnPaperOnly': False,
                    'date': FILING_DATE
                },
                'business': {
                    'identifier': 'BC1234567'
                }
            }
        }

        documents = document_meta.get_documents(filing)
        assert len(documents) == 0


def test_alteration(session, app):
    """Assert that no documents are returned for an Alteration filing."""
    document_meta = DocumentMetaService()
    factory_business(identifier='BC1234567', entity_type='BC')
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'COMPLETED',
                    'name': 'alteration',
                    'availableOnPaperOnly': False,
                    'date': FILING_DATE
                },
                'business': {
                    'identifier': 'BC1234567'
                }
            }
        }

        documents = document_meta.get_documents(filing)
        assert len(documents) == 1


def test_ia_fed(app):
    """Assert that an IA - FED document is returned for a future effective IA filing."""
    from legal_api.utils.legislation_datetime import LegislationDatetime
    document_meta = DocumentMetaService()
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'PAID',
                    'name': 'incorporationApplication',
                    'availableOnPaperOnly': False,
                    'effectiveDate': LegislationDatetime.tomorrow_midnight().isoformat(),
                    'date': FILING_DATE
                },
                'business': {
                    'identifier': 'T12345678'
                },
                'incorporationApplication': {
                    'nameRequest': {
                        'legalType': 'BC'
                    }
                }
            }
        }
        documents = document_meta.get_documents(filing)
        assert len(documents) == 1

        assert documents[0]['type'] == 'REPORT'
        assert documents[0]['reportType'] is None
        assert documents[0]['filingId'] == 12356
        assert documents[0]['title'] == 'Incorporation Application - Future Effective Incorporation'
        assert documents[0]['filename'] == 'T12345678 - Incorporation Application (Future Effective) - 2020-07-14.pdf'


def test_ia_paid(app):
    """Assert that an IA - Pending document is returned for a PAID IA filing."""
    document_meta = DocumentMetaService()
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'PAID',
                    'name': 'incorporationApplication',
                    'availableOnPaperOnly': False,
                    'effectiveDate': FILING_DATE,
                    'date': FILING_DATE
                },
                'business': {
                    'identifier': 'T12345678'
                },
                'incorporationApplication': {
                    'nameRequest': {
                        'legalType': 'BC'
                    }
                }
            }
        }
        documents = document_meta.get_documents(filing)
        assert len(documents) == 1

        assert documents[0]['type'] == 'REPORT'
        assert documents[0]['reportType'] is None
        assert documents[0]['filingId'] == 12356
        assert documents[0]['title'] == 'Incorporation Application - Pending'
        assert documents[0]['filename'] == 'T12345678 - Incorporation Application (Pending) - 2020-07-14.pdf'


def test_ia_completed(app):
    """Assert that IA + NOA + Certificate documents are returned for a COMPLETED IA filing."""
    document_meta = DocumentMetaService()
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'COMPLETED',
                    'name': 'incorporationApplication',
                    'availableOnPaperOnly': False,
                    'effectiveDate': FILING_DATE,
                    'date': FILING_DATE
                },
                'business': {
                    'identifier': 'T12345678'
                },
                'incorporationApplication': {
                    'nameRequest': {
                        'legalType': 'BC'
                    }
                }
            }
        }
        documents = document_meta.get_documents(filing)
        assert len(documents) == 3

        assert documents[0]['type'] == 'REPORT'
        assert documents[0]['reportType'] is None
        assert documents[0]['filingId'] == 12356
        assert documents[0]['title'] == 'Incorporation Application'
        assert documents[0]['filename'] == 'T12345678 - Incorporation Application - 2020-07-14.pdf'

        assert documents[1]['type'] == 'REPORT'
        assert documents[1]['reportType'] == 'noa'
        assert documents[1]['filingId'] == 12356
        assert documents[1]['title'] == 'Notice of Articles'
        assert documents[1]['filename'] == 'T12345678 - Notice of Articles - 2020-07-14.pdf'

        assert documents[2]['type'] == 'REPORT'
        assert documents[2]['reportType'] == 'certificate'
        assert documents[2]['filingId'] == 12356
        assert documents[2]['title'] == 'Certificate'
        assert documents[2]['filename'] == 'T12345678 - Certificate - 2020-07-14.pdf'


def test_ia_completed_bcomp(session, app):
    """Assert that IA + NOA + Certificate documents are returned for a COMPLETED IA filing when business is a BCOMP."""
    document_meta = DocumentMetaService()
    factory_business(identifier='BC1234567', entity_type='BC')
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'COMPLETED',
                    'name': 'incorporationApplication',
                    'availableOnPaperOnly': False,
                    'effectiveDate': FILING_DATE,
                    'date': FILING_DATE
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
        assert documents[0]['filingId'] == 12356
        assert documents[0]['title'] == 'Incorporation Application'
        assert documents[0]['filename'] == 'BC1234567 - Incorporation Application - 2020-07-14.pdf'

        assert documents[1]['type'] == 'REPORT'
        assert documents[1]['reportType'] == 'noa'
        assert documents[1]['filingId'] == 12356
        assert documents[1]['title'] == NOA_TITLE
        assert documents[1]['filename'] == NOA_FILENAME

        assert documents[2]['type'] == 'REPORT'
        assert documents[2]['reportType'] == 'certificate'
        assert documents[2]['filingId'] == 12356
        assert documents[2]['title'] == 'Certificate'
        assert documents[2]['filename'] == 'BC1234567 - Certificate - 2020-07-14.pdf'


def test_correction_ia(session, app):
    """Assert that no documents are returned for a Correction filing."""
    document_meta = DocumentMetaService()
    factory_business(identifier='BC1234567', entity_type='BC')
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12357,
                    'status': 'COMPLETED',
                    'name': 'correction',
                    'availableOnPaperOnly': False,
                    'date': FILING_DATE
                },
                'business': {
                    'identifier': 'BC1234567'
                },
                'correction': {
                    'correctedFilingId': 12356
                },
                'incorporationApplication': {
                    'nameRequest': {
                        'legalType': 'BC'
                    }
                }
            }
        }

        with patch.object(NameXService, 'has_correction_changed_name', return_value=False):
            documents = document_meta.get_documents(filing)

    assert len(documents) == 2
