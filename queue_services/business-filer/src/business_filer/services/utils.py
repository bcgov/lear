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
"""Common utilities used by the services."""
from datetime import date
import copy
import json
from http import HTTPStatus

from business_model.models import Filing
from document_record_service import DocumentRecordService, RequestInfo as DrsRequestInfo, DOCUMENT_TYPES, get_document_class
from flask import current_app

from business_filer.services import flags

import dpath.util


def get_date(filing: dict, path: str) -> date:
    """Extract a date from the JSON filing, at the provided path.

    Args:
        filing (dict): A valid registry_schema filing.
        path (str): The path to the date, which is in ISO Format.

    Examples:
        >>>get_date(
            filing={'filing':{'header':{'date': '2001-08-05'}}},
            path='filing/header/date')
        date(2001, 8, 5)

    """
    try:
        raw = dpath.util.get(filing, path)
        return date.fromisoformat(raw)
    except (IndexError, KeyError, TypeError, ValueError):
        return None


def get_str(filing: dict, path: str) -> str:
    """Extract a str from the JSON filing, at the provided path.

    Args:
        filing (dict): A valid registry_schema filing.
        path (str): The path to the date, which is in ISO Format.

    Examples:
        >>>get_str(
            filing={'filing':{'header':{'name': 'annualReport'}}},
            path='filing/header/name')
        'annualReport'

    """
    try:
        raw = dpath.util.get(filing, path)
        return str(raw)
    except (IndexError, KeyError, TypeError, ValueError):
        return None


def get_bool(filing: dict, path: str) -> str:
    """Extract a boolean from the JSON filing, at the provided path.

    Args:
        filing (dict): A valid registry_schema filing.
        path (str): The path to the property.
    """
    try:
        raw = dpath.util.get(filing, path)
        return bool(raw)
    except (IndexError, KeyError, TypeError, ValueError):
        return None


def get_int(filing: dict, path: str) -> str:
    """Extract int from the JSON filing, at the provided path.

    Args:
        filing (dict): A valid registry_schema filing.
        path (str): The path to the property.
    """
    try:
        raw = dpath.util.get(filing, path)
        return int(raw)
    except (IndexError, KeyError, TypeError, ValueError):
        return None

def sync_drs(filing_submission: Filing): # noqa: PLR0915, PLR0912
    document_id_state = filing_submission.filing_json['filing']['header'].get('documentIdState', {})
    legal_type = filing_submission.filing_json['filing']['business'].get('legalType')

    if  document_id_state and flags.is_on('enable-document-records'):
        filing_type = filing_submission.filing_json['filing']['header']['name']
        temp_reg = filing_submission.temp_reg

        if filing_type in ['incorporationApplication', 'continuationIn']:
            # Get existing document on DRS
            doc_list = DocumentRecordService().get_document(
                DrsRequestInfo(
                    document_class=DOCUMENT_TYPES[filing_type]['class'],
                    consumer_identifier=temp_reg
                )
            )

            if not isinstance(doc_list, list):
                current_app.logger.error(
                    f"No associated documents found for temporary registration ID: {temp_reg}"
                )
            else:
                # Update missing consumer document id
                if document_id_state['valid'] and document_id_state['consumerDocumentId'] == '':
                    copied_json = copy.deepcopy(filing_submission.filing_json)
                    copied_json['filing']['header']['documentIdState']['consumerDocumentId'] = doc_list[0]['consumerDocumentId']
                    filing_submission._filing_json = copied_json
                # Replace temp registration id with business identifier:
                for associated_document in doc_list:
                    doc_service_id = associated_document['documentServiceId']
                    DocumentRecordService().update_document(
                        DrsRequestInfo(
                            document_service_id=doc_service_id,
                            consumer_identifier=filing_submission.filing_json['filing']['business']['identifier'],
                            consumer_reference_id=str(filing_submission.id)
                        )
                    )

        else:
            if filing_type and document_id_state['valid']:
                try:
                    document_class = get_document_class(legal_type)
                    if DOCUMENT_TYPES.get(filing_type, ''):
                        document_type = DOCUMENT_TYPES[filing_type]
                    else:
                        document_type = DOCUMENT_TYPES['systemIsTheRecord']

                    response_json = DocumentRecordService().post_class_document(
                        request_info=DrsRequestInfo(
                            document_class=document_class,
                            document_type=document_type,
                            consumer_reference_id=filing_submission.id,
                            consumer_doc_id=document_id_state['consumerDocumentId'],
                            consumer_identifier=filing_submission.filing_json['filing']['business']['identifier']
                        ),
                        has_file=False
                    )
                    if document_id_state['consumerDocumentId'] == '' and response_json:
                        # Update consumerDocumentId
                        copied_json = copy.deepcopy(filing_submission.filing_json)
                        copied_json['filing']['header']['documentIdState']['consumerDocumentId'] = response_json['consumerDocumentId']
                        filing_submission._filing_json = copied_json
                    else:
                        current_app.logger.error(
                            f"Document Record Creation Error: {filing_submission.id}, {response_json['rootCause']}", exc_info=True)

                except Exception as error:
                    current_app.logger.error(f"Document Record Creation Error: {error}")                    
