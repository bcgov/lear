# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Searching on a business tasks.

Provides all the search and retrieval from the business filings datastore.
"""

from datetime import datetime
from http import HTTPStatus

import datedelta
from flask import jsonify
from flask_restplus import Resource, cors

from legal_api.models import Business, Filing
from legal_api.services import namex
from legal_api.services.filings import validations
from legal_api.utils.util import cors_preflight

from .api_namespace import API


@cors_preflight('GET,')
@API.route('/<string:identifier>/tasks', methods=['GET', 'OPTIONS'])
class TaskListResource(Resource):
    """Business Tasks service - Lists all incomplete filings and to-dos."""

    @staticmethod
    @cors.crossdomain(origin='*')
    def get(identifier):
        """Return a JSON object with meta information about the Service."""
        business = Business.find_by_identifier(identifier)
        is_nr = identifier.startswith('NR')

        # Check if this is a NR
        if is_nr:
            # Fetch NR Data
            nr_response = namex.query_nr_number(identifier)
            # Validate NR data
            validation_result = namex.validate_nr(nr_response.json())

            # Return error if the NR is not consumable (invalid)
            if not validation_result['is_consumable']:
                return jsonify({
                    'message': f'{identifier} is invalid', 'validation': validation_result
                    }), HTTPStatus.FORBIDDEN

        if not business:
            # Create Incorporate using NR to-do item
            if is_nr:
                rv = []
                rv.append(TaskListResource.create_incorporate_nr_todo(nr_response.json(), 1, True))
            # business does not exist and not an nr so return empty task list
            else:
                rv = []
        else:
            rv = TaskListResource.construct_task_list(business)
            if not rv and is_nr:
                rv.append(TaskListResource.create_incorporate_nr_todo(nr_response.json(), 1, True))

        return jsonify(tasks=rv)

    @staticmethod
    def construct_task_list(business):
        """
        Return all current pending tasks to do.

        First retrieves filings that are either drafts, or incomplete,
        then populate AR filings that have not been started for
        years that are due.

        Rules for AR filings:
            - Co-ops must file one AR per year. The next AR date must be AFTER the most recent
              AGM date. The calendar year of the filing is the first contiguous year following
              the last AGM date

            - Corporations must file one AR per year, on or after the anniversary of the founding date
        """
        tasks = []
        order = 1
        check_agm = validations.annual_report.requires_agm(business)

        # If no filings exist in legal API db (set after this line), use the business' next anniversary date
        todo_start_date = business.next_anniversary.date()

        # Retrieve filings that are either incomplete, or drafts
        pending_filings = Filing.get_filings_by_status(business.id, [Filing.Status.DRAFT.value,
                                                                     Filing.Status.PENDING.value,
                                                                     Filing.Status.PENDING_CORRECTION.value,
                                                                     Filing.Status.ERROR.value])
        # Create a todo item for each pending filing
        for filing in pending_filings:
            task = {'task': filing.json, 'order': order, 'enabled': True}
            tasks.append(task)
            order += 1

        last_ar_date = business.last_ar_date
        if check_agm:
            # If this is a CO-OP, set the start date to the first day of the year, since an AR filing
            # is available as of Jan/01
            if last_ar_date:
                todo_start_date = (datetime(last_ar_date.year + 1, 1, 1)).date()
            else:
                # If this is the first calendar year since incorporation, there is no
                # previous ar date. Use the next anniversary year.
                todo_start_date = (datetime(todo_start_date.year, 1, 1)).date()

        # Retrieve all previous annual report filings. If there are existing AR filings, determine
        # the latest date of filing
        annual_report_filings = Filing.get_filings_by_type(business.id, 'annualReport')
        if annual_report_filings:
            # get last AR date from annualReportDate; if not present in json, try annualGeneralMeetingDate and
            # finally filing date
            last_ar_date = \
                annual_report_filings[0].filing_json['filing']['annualReport'].get('annualReportDate', None)
            if not last_ar_date:
                last_ar_date = annual_report_filings[0].filing_json['filing']['annualReport']\
                    .get('annualGeneralMeetingDate', None)
            if not last_ar_date:
                last_ar_date = annual_report_filings[0].filing_date
            last_ar_date = datetime.fromisoformat(last_ar_date)
            if check_agm:
                todo_start_date = (datetime(last_ar_date.year+1, 1, 1)).date()
            else:
                todo_start_date = (last_ar_date+datedelta.YEAR).date()

        start_year = todo_start_date.year

        while todo_start_date <= datetime.now().date():
            enabled = not pending_filings and todo_start_date.year == start_year
            tasks.append(TaskListResource.create_todo(business, todo_start_date.year, order, enabled))
            todo_start_date += datedelta.YEAR
            order += 1
        return tasks

    @staticmethod
    def create_todo(business, todo_year, order, enabled):
        """Return a to-do JSON object."""
        todo = {
            'task': {
                'todo': {
                    'business': business.json(),
                    'header': {
                        'name': 'annualReport',
                        'ARFilingYear': todo_year,
                        'status': 'NEW'
                    }
                }
            },
            'order': order,
            'enabled': enabled
        }
        return todo

    @staticmethod
    def create_incorporate_nr_todo(name_request, order, enabled):
        """Return a to-do JSON object."""
        todo = {
            'task': {
                'todo': {
                    'nameRequest': name_request,
                    'header': {
                        'name': 'nameRequest',
                        'status': 'NEW'
                    }
                }
            },
            'order': order,
            'enabled': enabled
        }
        return todo
