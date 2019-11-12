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

        if not business:
            return jsonify({'message': f'{identifier} not found'}), HTTPStatus.NOT_FOUND

        rv = TaskListResource.construct_task_list(business)
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
        # If no filings exist in legal API db this year will be used as the start year.
        todo_start_date = (datetime(2019, 1, 1)).date() if check_agm else business.next_anniversary.date()

        # Retrieve filings that are either incomplete, or drafts
        pending_filings = Filing.get_filings_by_status(business.id, [Filing.Status.DRAFT.value,
                                                                     Filing.Status.PENDING.value,
                                                                     Filing.Status.ERROR.value,
                                                                     Filing.Status.PAID.value])
        # Create a todo item for each pending filing
        for filing in pending_filings:
            task = {'task': filing.json, 'order': order, 'enabled': True}
            tasks.append(task)
            order += 1

        if check_agm:
            last_ar_date = business.last_ar_date
            if last_ar_date:
                todo_start_date = (datetime(last_ar_date.year + 1, 1, 1)).date()

        # Retrieve all previous annual report filings. If there are existing AR filings, determine
        # the latest date of filing
        annual_report_filings = Filing.get_filings_by_type(business.id, 'annualReport')
        if annual_report_filings:
            if check_agm:
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
                todo_start_date = (datetime(last_ar_date.year+1, 1, 1)).date()

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
