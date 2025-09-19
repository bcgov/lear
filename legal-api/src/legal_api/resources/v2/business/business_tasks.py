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
import requests
from flask import current_app, jsonify
from flask_cors import cross_origin
from requests import exceptions  # noqa I001

from legal_api.models import Business, Filing
from legal_api.services import check_warnings, namex
from legal_api.services.warnings.business.business_checks import BusinessWarningCodes, WarningType
from legal_api.utils.auth import jwt
from legal_api.utils.legislation_datetime import LegislationDatetime

from .bp import bp


@bp.route('/<string:identifier>/tasks', methods=['GET', 'OPTIONS'])
@cross_origin(origin='*')
@jwt.requires_auth
def get_tasks(identifier):
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
            rv.append(create_incorporate_nr_todo(nr_response.json(), 1, True))
        # business does not exist and not an nr so return empty task list
        else:
            rv = []
    else:
        rv = construct_task_list(business)
        if not rv and is_nr:
            paid_completed_filings = Filing.get_filings_by_status(business.id, [Filing.Status.PAID.value,
                                                                                Filing.Status.COMPLETED.value])
            # Append NR todo if there are no tasks and PAID or COMPLETED filings
            if not paid_completed_filings:
                rv.append(create_incorporate_nr_todo(nr_response.json(), 1, True))
        elif rv == 'pay_connection_error':
            return {
                'message': 'Failed to get payment details for a filing. Please try again later.'
            }, HTTPStatus.SERVICE_UNAVAILABLE

    return jsonify(tasks=rv)


def construct_task_list(business: Business):  # pylint: disable=too-many-locals; only 2 extra
    """
    Return all current pending tasks to do.

    First retrieves filings that are either drafts, or incomplete,
    then populate AR filings that have not been started for years that are due.
    Transparency Register tasks are added below the corresponding AR tasks

    Transition Application todo task appears below the Annual Report (and TR) tasks

    Rules for AR filings:
        - Co-ops must file one AR per year. The next AR date must be AFTER the most recent
            AGM date. The calendar year of the filing is the first contiguous year following
            the last AGM date

        - Corporations must file one AR per year, on or after the anniversary of the founding date
    """
    entity_types_no_ar = ['SP', 'GP']
    tasks = []
    order = 1

    warnings = check_warnings(business)
    if any(x['warningType'] == WarningType.MISSING_REQUIRED_BUSINESS_INFO for x in warnings):
        # TODO remove compliance warning line when UI has been integrated to use warnings instead of complianceWarnings
        business.compliance_warnings = warnings
        business.warnings = warnings

        # Checking for draft or pending conversion
        if not Filing.get_incomplete_filings_by_type(business.id, 'conversion'):
            tasks.append(create_conversion_filing_todo(business, order, True))
            order += 1

    # Retrieve filings that are either incomplete, or drafts
    pending_filings = Filing.get_filings_by_status(business.id, [Filing.Status.DRAFT.value,
                                                                 Filing.Status.PENDING.value,
                                                                 Filing.Status.PENDING_CORRECTION.value,
                                                                 Filing.Status.ERROR.value])
    # Create a todo item for each pending filing
    pending_tr_type: str = None
    for filing in pending_filings:
        if filing.filing_type == 'transparencyRegister':
            pending_tr_type = filing.filing_sub_type

        filing_json = filing.json
        if filing.payment_status_code == 'CREATED' and filing.payment_token:
            # get current pay details from pay-api
            try:
                headers = {
                    'Authorization': f'Bearer {jwt.get_token_auth_header()}',
                    'Content-Type': 'application/json'
                }
                pay_response = requests.get(
                    url=f'{current_app.config.get("PAYMENT_SVC_URL")}/{filing.payment_token}',
                    headers=headers
                )
                pay_details = {
                    'isPaymentActionRequired': pay_response.json().get('isPaymentActionRequired', False),
                    'paymentMethod': pay_response.json().get('paymentMethod', '')
                }
                filing_json['filing']['header'].update(pay_details)

            except (exceptions.ConnectionError, exceptions.Timeout) as err:
                current_app.logger.error(
                    f'Payment connection failure for {business.identifier} task list. ', err)
                return 'pay_connection_error'

        task = {'task': filing_json, 'order': order, 'enabled': True}
        tasks.append(task)
        order += 1

    if business.legal_type not in entity_types_no_ar:
        # If this is the first calendar year since incorporation, there is no previous ar year.
        next_ar_year = (business.last_ar_year if business.last_ar_year else business.founding_date.year) + 1

        # Checking for pending ar
        annual_report_filings = Filing.get_incomplete_filings_by_type(business.id, 'annualReport')
        if annual_report_filings:
            # Consider each filing as each year and add to find next ar year
            next_ar_year += len(annual_report_filings)

        ar_min_date, ar_max_date = business.get_ar_dates(next_ar_year)

        start_year = next_ar_year
        while next_ar_year <= datetime.utcnow().year and ar_min_date <= datetime.utcnow().date():
            # while next_ar_year <= datetime.utcnow().date():
            enabled = not pending_filings and ar_min_date.year == start_year
            tasks.append(create_todo(business, next_ar_year, ar_min_date, ar_max_date, order, enabled))

            # Include all ar's to todo from last ar filing
            next_ar_year += 1
            ar_min_date, ar_max_date = business.get_ar_dates(next_ar_year)
            order += 1

    tasks, order = add_tr_tasks(business, tasks, order, pending_tr_type)

    # Transition Application todo task appears below overdue Annual Reports before the restoration date causing the warning
    # and it does not affect the 'enabled' status of other todo items.
    if any(x['code'] == BusinessWarningCodes.TRANSITION_NOT_FILED.value for x in warnings):
        if not Filing.get_incomplete_filings_by_type(business.id, 'transition'):
            # Gets all completed restorations of the business (most recent first)
            restorations = Filing.get_filings_by_types(business.id, ['restoration', 'restorationApplication'])
            if not restorations:
                # Should never get here
                current_app.logger.error(f'Error - Business id: {business.id}. TRANSITION_NOT_FILED warning and no restoration filing on record.')
                return tasks
            # Use the first restoration in the list for the most recent completed restoration date
            last_restoration_date = restorations[0].effective_date
            last_ar_date = business.last_ar_date or business.founding_date
            # Get the transition application todo order based on the ar tasks, last restoration date, and ar date information
            transition_order, transition_enabled = _find_task_order_for_ta(tasks, order, last_restoration_date, last_ar_date)
            # Bump all the task orders by one that are at and above transition_order
            tasks = _bump_task_order(tasks, transition_order)
            # Append the TA task at with order: transition_order. Disable if there are any incomplete filings
            tasks.append(create_transition_todo(business, transition_order, (transition_enabled and not pending_filings)))
            order += 1

    return tasks


def add_tr_tasks(business: Business, tasks: list, order: int, pending_tr_type: str = None):
    """Add Transparency Register tasks to the tasks list."""
    entity_types_no_tr = ['SP', 'GP', 'CP']
    tr_required = business.state != Business.State.HISTORICAL.value and business.legal_type not in entity_types_no_tr
    if tr_required and (tr_start_date := current_app.config.get('TR_START_DATE', None)):
        # Initial TR todo
        if not pending_tr_type:
            tr_start_datetime = LegislationDatetime.as_legislation_timezone_from_date(
                datetime.fromisoformat(tr_start_date))
            initial_filing: Filing = Filing.get_most_recent_filing(business.id, 'transparencyRegister', 'initial')
            last_restoration_datetime = None
            if restoration_filing := Filing.get_most_recent_filing(business.id, 'restoration'):
                if restoration_filing.effective_date:
                    last_restoration_datetime = LegislationDatetime.as_legislation_timezone(
                        restoration_filing.effective_date)
                else:
                    last_restoration_datetime = LegislationDatetime.as_legislation_timezone(
                        restoration_filing.filing_date)

            if (
                last_restoration_datetime and
                not (initial_filing and initial_filing.effective_date > last_restoration_datetime)
            ):
                pending_tr_type = 'initial'
                tasks, order = _add_tr_task(tasks,
                                            order,
                                            True,
                                            business,
                                            'initial',
                                            last_restoration_datetime + datedelta.datedelta(months=6))

            elif business.founding_date > tr_start_datetime and not initial_filing:
                pending_tr_type = 'initial'
                tasks, order = _add_tr_task(tasks,
                                            order,
                                            True,
                                            business,
                                            'initial',
                                            business.founding_date + datedelta.datedelta(months=6))

        # Annual TR todos
        if (LegislationDatetime.now() + datedelta.datedelta(months=2)) > business.next_annual_tr_due_datetime:
            # the next annual tr due datetime is within 2 months so add task for annual TR
            annual_year = (business.next_annual_tr_due_datetime - datedelta.datedelta(months=2)).year
            if pending_tr_type != 'annual':
                tasks, order = _add_tr_task(tasks,
                                            order,
                                            not pending_tr_type,
                                            business,
                                            'annual',
                                            business.next_annual_tr_due_datetime,
                                            annual_year)
            # add any other outstanding annual TRs to the list
            now = LegislationDatetime.now()
            years_offset = 0
            while annual_year < now.year:
                years_offset += 1
                annual_year += 1
                # NOTE: can't just replace with annual_year due to 2 month offset (could be off by 1)
                due_date = business.next_annual_tr_due_datetime + datedelta.datedelta(years=years_offset)
                if (now + datedelta.datedelta(months=2)) > due_date:
                    tasks, order = _add_tr_task(tasks, order, False, business, 'annual', due_date, annual_year)

    return tasks, order


def _by_order(e: dict):
    """Return the order value of the given task."""
    return e['order']


def _find_task_order_for_ta(tasks: list, order: int, restoration_date: datetime, last_ar_date: datetime) -> int:
    """Find the appropriate task order value for the Transition Application filing in the task list."""
    prioritize_ar_before_year = restoration_date.year
    # add 1 if the restoration happened after the AR was scheduled for this year
    if restoration_date > last_ar_date:
        year_diff = restoration_date.year - last_ar_date.year
        adjusted_ar_date = last_ar_date + datedelta.datedelta(years=year_diff)
        if restoration_date > adjusted_ar_date:
            prioritize_ar_before_year += 1

    enabled = True
    ar_todo_tasks = [task for task in tasks if task['task'].get('todo', {}).get('header', {}).get('ARFilingYear')]
    if not ar_todo_tasks:
        # default order will be after any pending tasks
        return order, enabled

    ar_todo_tasks.sort(key=_by_order)
    for ar_task in ar_todo_tasks:
        if prioritize_ar_before_year <= ar_task['task']['todo']['header']['ARFilingYear']:
            # Will be before this ar task
            return ar_task['order'], enabled
        else:
            # There is at least 1 overdue AR task that should be filed before the TA task is enabled
            enabled = False

    # will be after all existing AR tasks
    return order, enabled


def _find_task_order_for_tr(tasks: list, order: int, tr_sub_type: str, year: int) -> int:
    """Find the appropriate task order value for the TR filing in the task list."""
    ar_todo_tasks = [task for task in tasks if task['task'].get('todo', {}).get('header', {}).get('ARFilingYear')]
    if not ar_todo_tasks:
        # default order will be after any pending tasks
        return order

    ar_todo_tasks.sort(key=_by_order)
    if tr_sub_type == 'initial':
        # Should be directly after any AR in the same year as initial
        # (not possible to have ARs outstanding in previous years)
        if ar_todo_tasks[0]['task']['todo']['header']['ARFilingYear'] == year:
            # Will be directly after this task
            return ar_todo_tasks[0]['order'] + 1
        # Will be ahead of this task
        return ar_todo_tasks[0]['order']
    else:
        # tr annual task, should be directly after the AR task of the same year
        for ar_task in ar_todo_tasks:
            if ar_task['task']['todo']['header']['ARFilingYear'] == year:
                # Will be directly after this task
                return ar_task['order'] + 1
            elif ar_task['task']['todo']['header']['ARFilingYear'] > year:
                # Will be ahead of this task
                return ar_task['order']

    # is an annual task and should after all existing AR tasks
    return order


def _bump_task_order(tasks: list, bump_start_point: int) -> list:
    """Bump the order of the task list down from the start point."""
    for task in tasks:
        if task['order'] >= bump_start_point:
            task['order'] += 1
    return tasks


def _add_tr_task(tasks: list, order: int, enabled: bool,  # pylint: disable=too-many-arguments
                 business: Business, sub_type: str, due_date: datetime, year: int = None):
    """Add a TR task to the list of tasks in the correct order."""
    tr_order = _find_task_order_for_tr(tasks, order, sub_type, year)
    # bump the order of all the tasks after the tr by 1
    tasks = _bump_task_order(tasks, tr_order)
    tasks.append(create_tr_todo(business, tr_order, enabled, sub_type, due_date, year))
    order += 1
    return tasks, order


def create_todo(business, ar_year, ar_min_date, ar_max_date, order, enabled):  # pylint: disable=too-many-arguments
    """Return a to-do JSON object."""
    todo = {
        'task': {
            'todo': {
                'business': business.json(),
                'header': {
                    'name': 'annualReport',
                    'ARFilingYear': ar_year,
                    'status': 'NEW',
                    'arMinDate': ar_min_date.isoformat(),
                    'arMaxDate': ar_max_date.isoformat()
                }
            }
        },
        'order': order,
        'enabled': enabled
    }
    return todo


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


def create_conversion_filing_todo(business, order, enabled):
    """Return a to-do JSON object."""
    todo = {
        'task': {
            'todo': {
                'business': business.json(),
                'header': {
                    'name': 'conversion',
                    'status': 'NEW'
                }
            }
        },
        'order': order,
        'enabled': enabled
    }
    return todo


def create_transition_todo(business, order, enabled):
    """Return a to-do JSON object for transition application filing."""
    todo = {
        'task': {
            'todo': {
                'business': business.json(),
                'header': {
                    'name': 'transition',
                    'status': 'NEW'
                }
            }
        },
        'order': order,
        'enabled': enabled
    }
    return todo


def create_tr_todo(business: Business, order: int, enabled: bool,  # pylint: disable=too-many-arguments
                   sub_type: str, due_date: datetime, year: int = None):
    """Return a to-do JSON object for a Tranparency Register todo item."""
    return {
        'task': {
            'todo': {
                'business': business.json(),
                'header': {
                    'TRFilingYear': year,
                    'dueDate': LegislationDatetime.as_legislation_timezone(due_date).isoformat(),
                    'name': 'tranparencyRegister',
                    'status': 'NEW',
                    'subType': sub_type
                }
            }
        },
        'order': order,
        'enabled': enabled
    }
