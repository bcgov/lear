# Copyright © 2025 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
# an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
"""
Adds a blueprint for document_service import so that the documents from the document service api.

Specific to colin ids in the system can be imported and put into the table.
"""

import sys

import click
import requests
from flask import Blueprint, current_app

from legal_api.models import Filing, db
from legal_api.models.business import Business
from legal_api.models.colin_event_id import ColinEventId
from legal_api.models.document import Document
from legal_api.services import AccountService


document_service_bp = Blueprint('document_service', __name__)


@document_service_bp.cli.command('import')
@click.option('--business_identifier',
              default='',
              help='Business id to import documents for')
def import_documents(business_identifier):
    """Import documents from document service api."""
    # pylint: disable-msg=too-many-locals
    current_app.logger.info('Import documents started')
    url = current_app.config.get('DOCUMENT_API_URL')
    version = current_app.config.get('DOCUMENT_API_VERSION')
    request_base_url = f'{url}{version}/application-reports/events'
    token = AccountService.get_bearer_token()
    api_key = current_app.config.get('DOCUMENT_API_KEY')

    # This value doesn't affect the results, and is used for auditing purposes on the DRS side
    account_id = 'LEAR-IMPORT-SCRIPT'

    query = db.session.query(Filing).filter(Filing.source == 'COLIN')

    if business_identifier:
        business = Business.find_by_identifier(business_identifier)
        if business is None:
            current_app.logger.info(
              f'Business {business_identifier} not found')
            sys.exit(1)
        query = query.filter(Filing.business_id == business.id)

    colin_filings = query.all()
    count = 0
    num_filings = len(colin_filings)
    current_app.logger.info(
      f'Found {num_filings} filings to import documents for')
    imported = 0
    for filing in colin_filings:
        colin_event_id = ColinEventId.get_by_filing_id(filing.id)
        for event_id in colin_event_id:
            req_url = f'{request_base_url}/{event_id}'
            headers = {
                'X-ApiKey': api_key,
                'Account-Id': account_id,
                'Authorization': 'Bearer ' + token
            }
            response = requests.get(url=req_url, headers=headers)
            if response.status_code == 200:
                for report in response.json():
                    document = Document.find_one_by(
                        filing.business_id,
                        filing.id,
                        report['reportType']
                    )
                    if document is None:
                        imported += 1
                        new_document = Document(
                            business_id=filing.business_id,
                            filing_id=filing.id,
                            type=report['reportType'],
                            file_key=report['identifier'],
                            file_name=report['name'],
                        )
                        new_document.save()
                    else:
                        pass  # Already imported
            else:
                current_app.logger.info(
                  f'Failed to import documents for filing {filing.id}, status'
                  + f' code: {response.status_code}, {req_url}')
        count += 1
        if count % 100 == 0:
            current_app.logger.info(f'Processed {count} of {num_filings}')
    summary = 'Import documents completed'
    if business_identifier:
        summary += f' for business {business_identifier}'
    summary += f', {imported} documents imported from {num_filings} filings'
    current_app.logger.info(summary)
