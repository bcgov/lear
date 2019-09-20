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
from datetime import date, datetime
import datedelta
from http import HTTPStatus

from flask import jsonify
from flask_restplus import Resource, cors

from legal_api.models import Business, Filing
from legal_api.utils.util import cors_preflight
from legal_api.services.filings import validations
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
    
    """
    Method to retrieve all current pending tasks to do. First retrieves filings that are 
    either drafts, or incomplete, then populate AR filings that have not been started for
    years that are due. 
    
    Rules for AR filings:
        - Co-ops must file one AR per year. The next AR date must be AFTER the most recent
          AGM date. The calendar year of the filing is the first contiguous year following
          the last AGM date

        - Corporations must file one AR per year, on or after the anniversary of the founding date 
    """
    @staticmethod
    def construct_task_list(business):
        tasks = []
        order = 1
        checkAgm = validations.annual_report.RequiresAGM(business)
        # If no filings exist in legal API db this year will be used as the start year.
        todo_start_date = (datetime(2019,1,1)).date() if checkAgm else business.nextAnniversary.date()  
       
        
        # Retrieve filings that are either incomplete, or drafts
        pending_filings = Filing.get_filings_by_status(business.id, [Filing.Status.DRAFT.value,
                                                                     Filing.Status.PENDING.value,
                                                                     Filing.Status.ERROR.value])
        # Create a todo item for each pending filing
        for filing in pending_filings:
            task = {'task': filing.json, 'order': order, 'enabled': True}
            tasks.append(task)
            order += 1

        # Retrieve all previous annual report filings. If there are existing AR filings, determine
        # the latest date of filing
        annual_report_filings = Filing.get_filings_by_type(business.id, 'annualReport')
        if annual_report_filings:
            last_filing = annual_report_filings[0].filing_json['filing']['annualReport']
                              
            if checkAgm:
                date = datetime.strptime(last_filing['annualGeneralMeetingDate'],'%Y-%m-%d')
                todo_start_date=(datetime(date.year+1,1,1)).date()
            else:
                todo_start_date = business.nextAnniversary.date()

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