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
Adds a blueprint for document_service import so that the documents from the document service api
specific to colin ids in the system can be imported and put into the table.
"""
import requests

from flask import Blueprint, current_app

from legal_api.models import db, Filing
from legal_api.models.db import init_db
from legal_api.models.colin_event_id import ColinEventId
from legal_api.models.document import Document
from legal_api.services import AccountService

document_service_bp = Blueprint('document_service', __name__)

@document_service_bp.cli.command('import')
def import_documents():
    """
    Import documents from document service api.
    """
    current_app.logger.info("Import documents started")
    init_db(current_app)
    url = current_app.config.get('DOCUMENT_API_URL')
    version = current_app.config.get('DOCUMENT_API_VERSION')
    requestBaseUrl = f'{url}{version}/application-reports/events'
    token = AccountService.get_bearer_token()
    api_key = current_app.config.get('DOCUMENT_API_KEY')
    account_id = "LEAR-API"

    colin_filings = db.session\
        .query(Filing)\
        .filter(Filing.source == 'COLIN')\
        .all()
    count = 0
    num_filings = len(colin_filings)
    imported = 0
    for filing in colin_filings:
        colin_event_id = ColinEventId.get_by_filing_id(filing.id)
        for event_id in colin_event_id:
            event_id = 5775561
            req_url = f'{requestBaseUrl}/{event_id}'
            headers = {
                'X-ApiKey': api_key,
                'X-Api-Key': api_key,
                'Account-Id': account_id,
                'Authorization': 'Bearer ' + token
            }
            response = requests.get(url=req_url, headers=headers)
            if response.status_code == 200:
                for report in response.json():
                    imported += 1
                    new_document = Document(
                        business_id=filing.business_id,
                        filing_id=filing.id,
                        type=report['reportType'],
                        file_key=report['identifier'],
                        file_name=report['name'],
                    )
                    new_document.save()
        count += 1
        if (count % 100 == 0):
            current_app.logger.info(f'Processed {count} of {num_filings}')
    current_app.logger.info(f"Import documents completed, {imported} documents imported")
