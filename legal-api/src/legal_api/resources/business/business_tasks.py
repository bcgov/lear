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

from flask import jsonify
from flask_restplus import Resource, cors

from legal_api.models import Business, Filing
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
        """Return a task list object."""
        tasks = []
        order = 1
        todo_start_year = 2019  # If no filings exist in legal API db this year will be used as the start year.

        pending_filings = Filing.get_filings_by_status(business.id, [Filing.Status.DRAFT.value,
                                                                     Filing.Status.PENDING.value,
                                                                     Filing.Status.ERROR.value])
        for filing in pending_filings:
            task = {'task': filing.json, 'order': order, 'enabled': True}
            tasks.append(task)
            order += 1

        annual_report_filings = Filing.get_filings_by_type(business.id, 'annualReport')
        if annual_report_filings:
            last_filing = annual_report_filings[0].filing_json
            todo_start_year = datetime.strptime(last_filing['filing']['annualReport']['annualGeneralMeetingDate'],
                                                '%Y-%m-%d').year + 1

        if todo_start_year <= datetime.now().year:
            for todo_year in range(todo_start_year, datetime.now().year+1):
                enabled = not pending_filings and todo_year == todo_start_year
                tasks.append(TaskListResource.create_todo(business, todo_year, order, enabled))
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
