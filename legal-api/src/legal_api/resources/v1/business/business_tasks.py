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

import requests
from requests import exceptions  # noqa I001
from flask import current_app, jsonify
from flask_restx import Resource, cors

from legal_api.models import Business, Filing
from legal_api.services import namex
from legal_api.utils.auth import jwt
from legal_api.utils.util import cors_preflight

from .api_namespace import API


@cors_preflight("GET,")
@API.route("/<string:identifier>/tasks", methods=["GET", "OPTIONS"])
class TaskListResource(Resource):
    """Business Tasks service - Lists all incomplete filings and to-dos."""

    @staticmethod
    @cors.crossdomain(origin="*")
    @jwt.requires_auth
    def get(identifier):
        """Return a JSON object with meta information about the Service."""
        business = Business.find_by_identifier(identifier)
        is_nr = identifier.startswith("NR")

        # Check if this is a NR
        if is_nr:
            # Fetch NR Data
            nr_response = namex.query_nr_number(identifier)
            # Validate NR data
            validation_result = namex.validate_nr(nr_response.json())

            # Return error if the NR is not consumable (invalid)
            if not validation_result["is_consumable"]:
                return jsonify(
                    {"message": f"{identifier} is invalid", "validation": validation_result}
                ), HTTPStatus.FORBIDDEN

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
                paid_completed_filings = Filing.get_filings_by_status(
                    business.id, [Filing.Status.PAID.value, Filing.Status.COMPLETED.value]
                )
                # Append NR todo if there are no tasks and PAID or COMPLETED filings
                if not paid_completed_filings:
                    rv.append(TaskListResource.create_incorporate_nr_todo(nr_response.json(), 1, True))
            elif rv == "pay_connection_error":
                return {
                    "message": "Failed to get payment details for a filing. Please try again later."
                }, HTTPStatus.SERVICE_UNAVAILABLE

        return jsonify(tasks=rv)

    @staticmethod
    def construct_task_list(business):  # pylint: disable=too-many-locals; only 2 extra
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

        # Retrieve filings that are either incomplete, or drafts
        pending_filings = Filing.get_filings_by_status(
            business.id,
            [
                Filing.Status.DRAFT.value,
                Filing.Status.PENDING.value,
                Filing.Status.PENDING_CORRECTION.value,
                Filing.Status.ERROR.value,
            ],
        )
        # Create a todo item for each pending filing
        for filing in pending_filings:
            filing_json = filing.json
            if filing.payment_status_code == "CREATED" and filing.payment_token:
                # get current pay details from pay-api
                try:
                    headers = {
                        "Authorization": f"Bearer {jwt.get_token_auth_header()}",
                        "Content-Type": "application/json",
                    }
                    pay_response = requests.get(
                        url=f"{current_app.config.get('PAYMENT_SVC_URL')}/{filing.payment_token}", headers=headers
                    )
                    pay_details = {
                        "isPaymentActionRequired": pay_response.json().get("isPaymentActionRequired", False),
                        "paymentMethod": pay_response.json().get("paymentMethod", ""),
                    }
                    filing_json["filing"]["header"].update(pay_details)

                except (exceptions.ConnectionError, exceptions.Timeout) as err:
                    current_app.logger.error(f"Payment connection failure for {business.identifier} task list. ", err)
                    return "pay_connection_error"

            task = {"task": filing_json, "order": order, "enabled": True}
            tasks.append(task)
            order += 1

        # If this is the first calendar year since incorporation, there is no previous ar year.
        next_ar_year = (business.last_ar_year if business.last_ar_year else business.founding_date.year) + 1

        # Checking for pending ar
        annual_report_filings = Filing.get_incomplete_filings_by_type(business.id, "annualReport")
        if annual_report_filings:
            # Consider each filing as each year and add to find next ar year
            next_ar_year += len(annual_report_filings)

        ar_min_date, ar_max_date = business.get_ar_dates(next_ar_year)

        start_year = next_ar_year
        while next_ar_year <= datetime.utcnow().year and ar_min_date <= datetime.utcnow().date():
            # while next_ar_year <= datetime.utcnow().date():
            enabled = not pending_filings and ar_min_date.year == start_year
            tasks.append(TaskListResource.create_todo(business, next_ar_year, ar_min_date, ar_max_date, order, enabled))

            # Include all ar's to todo from last ar filing
            next_ar_year += 1
            ar_min_date, ar_max_date = business.get_ar_dates(next_ar_year)
            order += 1
        return tasks

    @staticmethod
    def create_todo(business, ar_year, ar_min_date, ar_max_date, order, enabled):  # pylint: disable=too-many-arguments
        """Return a to-do JSON object."""
        todo = {
            "task": {
                "todo": {
                    "business": business.json(),
                    "header": {
                        "name": "annualReport",
                        "ARFilingYear": ar_year,
                        "status": "NEW",
                        "arMinDate": ar_min_date.isoformat(),
                        "arMaxDate": ar_max_date.isoformat(),
                    },
                }
            },
            "order": order,
            "enabled": enabled,
        }
        return todo

    @staticmethod
    def create_incorporate_nr_todo(name_request, order, enabled):
        """Return a to-do JSON object."""
        todo = {
            "task": {"todo": {"nameRequest": name_request, "header": {"name": "nameRequest", "status": "NEW"}}},
            "order": order,
            "enabled": enabled,
        }
        return todo
