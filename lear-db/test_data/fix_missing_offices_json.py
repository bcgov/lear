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
""" Fix older filing json that was before the offices structure was used. The payment token is saved off and cleared so
that the filing can be changed without being "locked".

This was run once, on Feb 6 2020.

"""
from dotenv import load_dotenv, find_dotenv

from flask import Flask
from legal_api import db
from legal_api.config import get_named_config
from legal_api.models import Filing

import copy

load_dotenv(find_dotenv())

FLASK_APP = Flask(__name__)
FLASK_APP.config.from_object(get_named_config('production'))
db.init_app(FLASK_APP)


def do_stuff():
    """Iterate all business entries and associate a records office if needed."""

    #thelist = ['53477','53508','53530','53534','7131','53372','53514','156','26988','53529','53475','53533','53527','53516','53385','26998','154']
    filings = db.session.query(Filing).filter(Filing.id.in_(thelist)).all()

    for filing in filings:

        old_token = filing._payment_token
        filing._payment_token = None
        filing.save()

        filing_json = copy.deepcopy(filing.filing_json)

        deliv_addr = filing_json['filing']['changeOfAddress']['deliveryAddress']
        mail_addr  = filing_json['filing']['changeOfAddress']['mailingAddress']

        filing_json['filing']['changeOfAddress']['offices'] = {
            'registeredOffice': {
                'deliveryAddress': deliv_addr,
                'mailingAddress': mail_addr,
            }
        }
        del filing_json['filing']['changeOfAddress']['deliveryAddress']
        del filing_json['filing']['changeOfAddress']['mailingAddress']

        filing._payment_token = old_token
        filing._filing_json = None
        filing._filing_json = filing_json
        filing.save()

with FLASK_APP.app_context():
    do_stuff()
