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
"""Sets the business_id for all lear_epoch filings. (Should only need to be run once)"""
from dotenv import load_dotenv, find_dotenv

from flask import Flask
from legal_api import db
from legal_api.config import get_named_config
from legal_api.models import Filing


load_dotenv(find_dotenv())

FLASK_APP = Flask(__name__)
FLASK_APP.config.from_object(get_named_config('production'))
db.init_app(FLASK_APP)

rowcount = 0

with FLASK_APP.app_context():
    epoch_ids = db.session.execute(
        """
        select filings.id as filing_id, businesses.id as business_id
        from businesses 
        join businesses_version on businesses.identifier = businesses_version.identifier 
        join filings on filings.transaction_id = businesses_version.transaction_id 
        where filing_type = 'lear_epoch';
        """
    )
    for epoch_id_pair in epoch_ids:
        rowcount += 1
        filing = Filing.find_by_id(epoch_id_pair['filing_id'])
        filing.business_id = epoch_id_pair['business_id']
        filing.save()


print(f'processed: {rowcount} rows')
