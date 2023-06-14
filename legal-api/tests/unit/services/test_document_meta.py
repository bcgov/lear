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
import copy
from unittest.mock import patch

import pytest
from registry_schemas.example_data import (
    CORRECTION_INCORPORATION,
    INCORPORATION_FILING_TEMPLATE,
    TRANSITION_FILING_TEMPLATE,
)

from legal_api.models import Business, Filing
from legal_api.services import DocumentMetaService
from tests.unit.models import factory_business, factory_filing


FILING_DATE = '2020-07-14'
EFFECTIVE_DATE = '2020-07-14T11:41:07.230473-07:00'
COA_TITLE = 'Address Change'
NOA_TITLE = 'Notice of Articles'
NOA_FILENAME = 'BC1234567 - Notice of Articles - 2020-07-14.pdf'
COD_TITLE = 'Director Change'
CON_TITLE = 'Legal Name Change'


def test_business_not_found(session, app):
    """Assert that no documents are returned when the filing's business is not found."""
    document_meta = DocumentMetaService()
    factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.BCOMP.value)
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'DONT_CARE',
                    'name': 'changeOfAddress',
                    'availableOnPaperOnly': False,
                    'inColinOnly': False,
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
    factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.BCOMP.value)
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'NOT_PAID_OR_COMPLETE',
                    'name': 'changeOfAddress',
                    'availableOnPaperOnly': False,
                    'inColinOnly': False,
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
        assert document_meta._legal_type == Business.LegalTypes.BCOMP.value


def test_available_on_paper_only(session, app):
    """Assert that no documents are returned for a paper-only filing."""
    document_meta = DocumentMetaService()
    factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.BCOMP.value)
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'COMPLETED',
                    'name': 'changeOfAddress',
                    'availableOnPaperOnly': True,
                    'inColinOnly': False,
                    'date': FILING_DATE
                },
                'business': {
                    'identifier': 'BC1234567'
                }
            }
        }
        assert len(document_meta.get_documents(filing)) == 0


def test_available_in_colin_only(session, app):
    """Assert that no documents are returned for a colin-only filing."""
    document_meta = DocumentMetaService()
    factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.BCOMP.value)
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'COMPLETED',
                    'name': 'changeOfAddress',
                    'availableOnPaperOnly': False,
                    'inColinOnly': True,
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
    factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.BCOMP.value)
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'PAID',
                    'name': 'changeOfAddress',
                    'inColinOnly': False,
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
    factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.BCOMP.value)
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'COMPLETED',
                    'name': 'changeOfAddress',
                    'inColinOnly': False,
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
                    'inColinOnly': False,
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
    factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.BCOMP.value)
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'COMPLETED',
                    'name': 'annualReport',
                    'inColinOnly': False,
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
    factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.BCOMP.value)
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'PAID',
                    'name': 'changeOfDirectors',
                    'inColinOnly': False,
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
    factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.BCOMP.value)
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'COMPLETED',
                    'name': 'changeOfDirectors',
                    'inColinOnly': False,
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
                    'inColinOnly': False,
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
    factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.BCOMP.value)
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'PAID',
                    'name': 'changeOfName',
                    'inColinOnly': False,
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
    factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.BCOMP.value)
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'COMPLETED',
                    'name': 'changeOfName',
                    'inColinOnly': False,
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
                    'inColinOnly': False,
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
    factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.BCOMP.value)
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'PAID',
                    'name': 'specialResolution',
                    'inColinOnly': False,
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
    factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.BCOMP.value)
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'COMPLETED',
                    'name': 'specialResolution',
                    'inColinOnly': False,
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
    factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.BCOMP.value)
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'PAID',
                    'name': 'voluntaryDissolution',
                    'inColinOnly': False,
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
    factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.BCOMP.value)
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'COMPLETED',
                    'name': 'voluntaryDissolution',
                    'inColinOnly': False,
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
    factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.BCOMP.value)
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'COMPLETED',
                    'name': 'correction',
                    'inColinOnly': False,
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


@pytest.mark.parametrize(
    'status, filing_id, business_identifier, expected_number, alteration_json',
    [
        ('COMPLETED', 12355, 'BC1234567', 2, {'nameRequest':
                                              {'nrNumber': 'NR 8798956',
                                               'legalName': 'HAULER MEDIA INC.',
                                               'legalType': 'BC'}}),
        ('COMPLETED', 12356, 'BC1234567', 3, {'nameRequest':
                                              {'nrNumber': 'NR 8798956',
                                               'legalName': 'New Name.',
                                               'legalType': 'BC'}}),
        ('COMPLETED', 12357, 'BC1234567', 2, {'contactPoint': {'email': 'no_one@never.get'}}),
        ('PENDING', 12358, 'BC1234567', 0, {})
    ]
)
def test_alteration(status, filing_id, business_identifier, expected_number, alteration_json, session, app):
    """Assert that the correct number of documents are returned for alterations in 3 scenarios."""
    document_meta = DocumentMetaService()
    factory_business(identifier=business_identifier, entity_type=Business.LegalTypes.BCOMP.value)
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': filing_id,
                    'status': status,
                    'name': 'alteration',
                    'inColinOnly': False,
                    'availableOnPaperOnly': False,
                    'date': FILING_DATE
                },
                'business': {
                    'identifier': business_identifier,
                    'legalName': 'HAULER MEDIA INC.',
                    'legalType': 'BC'
                },
                'alteration': alteration_json
            }
        }

        documents = document_meta.get_documents(filing)
        assert len(documents) == expected_number


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
                    'inColinOnly': False,
                    'availableOnPaperOnly': False,
                    'effectiveDate': LegislationDatetime.tomorrow_midnight().isoformat(),
                    'date': FILING_DATE
                },
                'business': {
                    'identifier': 'T12345678'
                },
                'incorporationApplication': {
                    'nameRequest': {
                        'legalType': Business.LegalTypes.BCOMP.value
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
                    'inColinOnly': False,
                    'availableOnPaperOnly': False,
                    'effectiveDate': EFFECTIVE_DATE,
                    'date': FILING_DATE
                },
                'business': {
                    'identifier': 'T12345678'
                },
                'incorporationApplication': {
                    'nameRequest': {
                        'legalType': Business.LegalTypes.BCOMP.value
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


@pytest.mark.parametrize('status, number_of_docs',
                         [
                             ('COMPLETED', 3),
                             ('CORRECTED', 3),
                             ('UNKNOWN', 0)
                         ])
def test_ia_status(session, app, status, number_of_docs):
    """Assert that IA + NOA + Certificate documents are returned for a COMPLETED IA filing."""
    document_meta = DocumentMetaService()
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': status,
                    'name': 'incorporationApplication',
                    'inColinOnly': False,
                    'availableOnPaperOnly': False,
                    'effectiveDate': EFFECTIVE_DATE,
                    'date': FILING_DATE
                },
                'business': {
                    'identifier': 'T12345678'
                },
                'incorporationApplication': {
                    'nameRequest': {
                        'legalType': Business.LegalTypes.BCOMP.value
                    }
                }
            }
        }

        with patch.object(Filing, 'find_by_id', return_value=Filing()):
            documents = document_meta.get_documents(filing)
            assert len(documents) == number_of_docs

            if number_of_docs:
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
    factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.BCOMP.value)
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'COMPLETED',
                    'name': 'incorporationApplication',
                    'inColinOnly': False,
                    'availableOnPaperOnly': False,
                    'effectiveDate': EFFECTIVE_DATE,
                    'date': FILING_DATE
                },
                'business': {
                    'identifier': 'BC1234567'
                }
            }
        }

        with patch.object(Filing, 'find_by_id', return_value=Filing()):
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


def test_ia_completed_bcomp_original(session, app):
    """Assert that IA + Certificate documents with (Original) are returned for a COMPLETED IA."""
    document_meta = DocumentMetaService()
    b = factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.BCOMP.value)
    with app.app_context():
        original_filing = factory_filing(b, INCORPORATION_FILING_TEMPLATE)
        CORRECTION_INCORPORATION['filing']['correction']['correctedFilingId'] = original_filing.id
        corrected_filing = factory_filing(b, CORRECTION_INCORPORATION)
        filing = {
            'filing': {
                'header': {
                    'filingId': original_filing.id,
                    'status': 'COMPLETED',
                    'name': 'incorporationApplication',
                    'inColinOnly': False,
                    'availableOnPaperOnly': False,
                    'effectiveDate': EFFECTIVE_DATE,
                    'date': FILING_DATE
                },
                'business': {
                    'identifier': 'BC1234567'
                }
            }
        }
        original_filing.parent_filing_id = corrected_filing.id
        original_filing.save()
        documents = document_meta.get_documents(filing)
        assert len(documents) == 3

        assert documents[0]['type'] == 'REPORT'
        assert documents[0]['reportType'] is None
        assert documents[0]['filingId'] == original_filing.id
        assert documents[0]['title'] == 'Incorporation Application (Original)'
        assert documents[0]['filename'] == 'BC1234567 - Incorporation Application (Original) - 2020-07-14.pdf'

        assert documents[1]['type'] == 'REPORT'
        assert documents[1]['reportType'] == 'noa'
        assert documents[1]['filingId'] == original_filing.id
        assert documents[1]['title'] == NOA_TITLE
        assert documents[1]['filename'] == NOA_FILENAME

        assert documents[2]['type'] == 'REPORT'
        assert documents[2]['reportType'] == 'certificate'
        assert documents[2]['filingId'] == original_filing.id
        assert documents[2]['title'] == 'Certificate'
        assert documents[2]['filename'] == 'BC1234567 - Certificate - 2020-07-14.pdf'


def test_correction_ia(session, app):
    """Assert that IA + NOA documents are returned for a Correction filing without name change."""
    document_meta = DocumentMetaService()
    b = factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.BCOMP.value)
    with app.app_context():
        original_filing = factory_filing(b, INCORPORATION_FILING_TEMPLATE)
        filing = {
            'filing': {
                'header': {
                    'filingId': 12357,
                    'status': 'COMPLETED',
                    'name': 'correction',
                    'inColinOnly': False,
                    'availableOnPaperOnly': False,
                    'date': FILING_DATE
                },
                'business': {
                    'identifier': 'BC1234567'
                },
                'correction': {
                    'correctedFilingId': original_filing.id
                },
                'incorporationApplication': {
                    'nameRequest': {
                        'legalType': Business.LegalTypes.BCOMP.value
                    }
                }
            }
        }

        documents = document_meta.get_documents(filing)

        assert len(documents) == 2

        assert documents[0]['type'] == 'REPORT'
        assert documents[0]['reportType'] is None
        assert documents[0]['filingId'] == 12357
        assert documents[0]['title'] == 'Incorporation Application (Corrected)'
        assert documents[0]['filename'] == 'BC1234567 - Incorporation Application (Corrected) - 2020-07-14.pdf'

        assert documents[1]['type'] == 'REPORT'
        assert documents[1]['reportType'] == 'noa'
        assert documents[1]['filingId'] == 12357
        assert documents[1]['title'] == NOA_TITLE
        assert documents[1]['filename'] == NOA_FILENAME


def test_correction_ia_with_cert_nr_change(session, app):
    """Assert that IA + NOA + Certificate documents are returned for a Correction filing with name change."""
    document_meta = DocumentMetaService()
    b = factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.BCOMP.value)
    initial_filing_json = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    initial_filing_json['filing']['incorporationApplication']['nameRequest'] = {}
    initial_filing_json['filing']['incorporationApplication']['nameRequest']['legalName'] = 'New Name'
    initial_filing_json['filing']['incorporationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'
    original_filing = factory_filing(b, INCORPORATION_FILING_TEMPLATE)
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12357,
                    'status': 'COMPLETED',
                    'name': 'correction',
                    'inColinOnly': False,
                    'availableOnPaperOnly': False,
                    'date': FILING_DATE
                },
                'business': {
                    'identifier': 'BC1234567'
                },
                'correction': {
                    'correctedFilingId': original_filing.id
                },
                'incorporationApplication': {
                    'nameRequest': {
                        'legalType': Business.LegalTypes.BCOMP.value,
                        'nrNumber': 'NR 3456789'
                    }
                }
            }
        }
        documents = document_meta.get_documents(filing)

        assert len(documents) == 3

        assert documents[0]['type'] == 'REPORT'
        assert documents[0]['reportType'] is None
        assert documents[0]['filingId'] == 12357
        assert documents[0]['title'] == 'Incorporation Application (Corrected)'
        assert documents[0]['filename'] == 'BC1234567 - Incorporation Application (Corrected) - 2020-07-14.pdf'

        assert documents[1]['type'] == 'REPORT'
        assert documents[1]['reportType'] == 'certificate'
        assert documents[1]['filingId'] == 12357
        assert documents[1]['title'] == 'Certificate (Corrected)'
        assert documents[1]['filename'] == 'BC1234567 - Certificate (Corrected) - 2020-07-14.pdf'

        assert documents[2]['type'] == 'REPORT'
        assert documents[2]['reportType'] == 'noa'
        assert documents[2]['filingId'] == 12357
        assert documents[2]['title'] == NOA_TITLE
        assert documents[2]['filename'] == NOA_FILENAME


def test_correction_ia_with_cert_name_correction(session, app):
    """Assert that IA + NOA + Certificate documents are returned for a Correction filing with name change."""
    document_meta = DocumentMetaService()
    b = factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.BCOMP.value)
    original_filing_json = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    original_filing_json['filing']['incorporationApplication']['nameRequest'] = {}
    original_filing_json['filing']['incorporationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'
    original_filing_json['filing']['incorporationApplication']['nameRequest']['legalName'] = 'abc'
    original_filing = factory_filing(b, original_filing_json)
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12357,
                    'status': 'COMPLETED',
                    'name': 'correction',
                    'inColinOnly': False,
                    'availableOnPaperOnly': False,
                    'date': FILING_DATE
                },
                'business': {
                    'identifier': 'BC1234567'
                },
                'correction': {
                    'correctedFilingId': original_filing.id
                },
                'incorporationApplication': {
                    'nameRequest': {
                        'legalType': Business.LegalTypes.BCOMP.value,
                        'nrNumber': 'NR 1234567',
                        'legalName': 'abc.'
                    }
                }
            }
        }
        documents = document_meta.get_documents(filing)

        assert len(documents) == 3

        assert documents[0]['type'] == 'REPORT'
        assert documents[0]['reportType'] is None
        assert documents[0]['filingId'] == 12357
        assert documents[0]['title'] == 'Incorporation Application (Corrected)'
        assert documents[0]['filename'] == 'BC1234567 - Incorporation Application (Corrected) - 2020-07-14.pdf'

        assert documents[1]['type'] == 'REPORT'
        assert documents[1]['reportType'] == 'certificate'
        assert documents[1]['filingId'] == 12357
        assert documents[1]['title'] == 'Certificate (Corrected)'
        assert documents[1]['filename'] == 'BC1234567 - Certificate (Corrected) - 2020-07-14.pdf'

        assert documents[2]['type'] == 'REPORT'
        assert documents[2]['reportType'] == 'noa'
        assert documents[2]['filingId'] == 12357
        assert documents[2]['title'] == NOA_TITLE
        assert documents[2]['filename'] == NOA_FILENAME


def test_correction_ia_with_named_to_numbered(session, app):
    """Assert that IA + NOA + Certificate documents are returned for a Correction filing with name change."""
    document_meta = DocumentMetaService()
    b = factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.BCOMP.value)
    original_filing_json = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    original_filing_json['filing']['incorporationApplication']['nameRequest'] = {}
    original_filing_json['filing']['incorporationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'
    original_filing_json['filing']['incorporationApplication']['nameRequest']['legalName'] = 'abc'
    original_filing = factory_filing(b, original_filing_json)
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12357,
                    'status': 'COMPLETED',
                    'name': 'correction',
                    'inColinOnly': False,
                    'availableOnPaperOnly': False,
                    'date': FILING_DATE
                },
                'business': {
                    'identifier': 'BC1234567'
                },
                'correction': {
                    'correctedFilingId': original_filing.id
                },
                'incorporationApplication': {
                    'nameRequest': {
                        'legalType': Business.LegalTypes.BCOMP.value
                    }
                }
            }
        }
        documents = document_meta.get_documents(filing)

        assert len(documents) == 3

        assert documents[0]['type'] == 'REPORT'
        assert documents[0]['reportType'] is None
        assert documents[0]['filingId'] == 12357
        assert documents[0]['title'] == 'Incorporation Application (Corrected)'
        assert documents[0]['filename'] == 'BC1234567 - Incorporation Application (Corrected) - 2020-07-14.pdf'

        assert documents[1]['type'] == 'REPORT'
        assert documents[1]['reportType'] == 'certificate'
        assert documents[1]['filingId'] == 12357
        assert documents[1]['title'] == 'Certificate (Corrected)'
        assert documents[1]['filename'] == 'BC1234567 - Certificate (Corrected) - 2020-07-14.pdf'

        assert documents[2]['type'] == 'REPORT'
        assert documents[2]['reportType'] == 'noa'
        assert documents[2]['filingId'] == 12357
        assert documents[2]['title'] == NOA_TITLE
        assert documents[2]['filename'] == NOA_FILENAME


def test_transition_bcomp_paid(session, app):
    """Assert that Transition Application document is returned for a filing."""
    document_meta = DocumentMetaService()
    factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.BCOMP.value)
    with app.app_context():
        filing = copy.deepcopy(TRANSITION_FILING_TEMPLATE)
        filing['filing']['header']['date'] = FILING_DATE
        filing['filing']['header']['status'] = 'PAID'
        filing['filing']['header']['availableOnPaperOnly'] = False
        filing['filing']['header']['inColinOnly'] = False

        documents = document_meta.get_documents(filing)

        assert len(documents) == 1

        assert documents[0]['type'] == 'REPORT'
        assert documents[0]['reportType'] is None
        assert documents[0]['filingId'] == 1
        assert documents[0]['title'] == 'Transition Application - Pending'
        assert documents[0]['filename'] == 'BC1234567 - Transition Application (Pending) - 2020-07-14.pdf'


def test_transition_bcomp_completed(session, app):
    """Assert that Transition Application + NOA documents are returned for a filing."""
    document_meta = DocumentMetaService()
    factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.BCOMP.value)
    with app.app_context():
        filing = copy.deepcopy(TRANSITION_FILING_TEMPLATE)
        filing['filing']['header']['date'] = FILING_DATE
        filing['filing']['header']['status'] = 'COMPLETED'
        filing['filing']['header']['availableOnPaperOnly'] = False
        filing['filing']['header']['inColinOnly'] = False
        documents = document_meta.get_documents(filing)

        assert len(documents) == 2

        assert documents[0]['type'] == 'REPORT'
        assert documents[0]['reportType'] is None
        assert documents[0]['filingId'] == 1
        assert documents[0]['title'] == 'Transition Application'
        assert documents[0]['filename'] == 'BC1234567 - Transition Application - 2020-07-14.pdf'

        assert documents[1]['type'] == 'REPORT'
        assert documents[1]['reportType'] == 'noa'
        assert documents[1]['filingId'] == 1
        assert documents[1]['title'] == NOA_TITLE
        assert documents[1]['filename'] == NOA_FILENAME


def test_ia_completed_coop(session, app):
    """Assert that documents are returned for a COMPLETED IA filing when business is a COOP."""
    document_meta = DocumentMetaService()
    factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.COOP.value)
    with app.app_context():
        filing = {
            'filing': {
                'header': {
                    'filingId': 12356,
                    'status': 'COMPLETED',
                    'name': 'incorporationApplication',
                    'inColinOnly': False,
                    'availableOnPaperOnly': False,
                    'effectiveDate': EFFECTIVE_DATE,
                    'date': FILING_DATE
                },
                'business': {
                    'identifier': 'BC1234567'
                }
            }
        }

        with patch.object(Filing, 'find_by_id', return_value=Filing()):
            documents = document_meta.get_documents(filing)
            assert len(documents) == 4

            assert documents[0]['type'] == 'REPORT'
            assert documents[0]['reportType'] is None
            assert documents[0]['filingId'] == 12356
            assert documents[0]['title'] == 'Incorporation Application'
            assert documents[0]['filename'] == 'BC1234567 - Incorporation Application - 2020-07-14.pdf'

            assert documents[1]['type'] == 'REPORT'
            assert documents[1]['reportType'] == 'certificate'
            assert documents[1]['filingId'] == 12356
            assert documents[1]['title'] == 'Certificate'
            assert documents[1]['filename'] == 'BC1234567 - Certificate - 2020-07-14.pdf'

            assert documents[2]['type'] == 'REPORT'
            assert documents[2]['reportType'] == 'certifiedRules'
            assert documents[2]['filingId'] == 12356
            assert documents[2]['title'] == 'Certified Rules'
            assert documents[2]['filename'] == 'BC1234567 - Certified Rules - 2020-07-14.pdf'

            assert documents[3]['type'] == 'REPORT'
            assert documents[3]['reportType'] == 'certifiedMemorandum'
            assert documents[3]['filingId'] == 12356
            assert documents[3]['title'] == 'Certified Memorandum'
            assert documents[3]['filename'] == 'BC1234567 - Certified Memorandum - 2020-07-14.pdf'
