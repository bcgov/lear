# Copyright © 2022 Province of British Columbia
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

from sqlalchemy.sql.expression import text  # noqa: I001

from legal_api.models import Business, Filing, db
from legal_api.services.warnings.business.business_checks import WarningType

def check_business(business: Business) -> list:
    """Check for missing business data."""
    result = []

    result.extend(check_amalgamating_business(business))

    return result

def check_amalgamating_business(business: Business) -> list:
    """Check if business is currently pending amalgamation."""
    result = []

    # Construct a JSON containment check clause for the SQL query
    where_clause = text(
        "filing_json->'filing'->'amalgamationApplication'->'amalgamatingBusinesses'" +
        f' @>\'[{{"identifier": "{business.identifier}"}}]\'')

    # Query the database to find amalgamation filings
    filing = db.session.query(Filing). \
        filter( Filing._status == Filing.Status.PAID.value,
                Filing._filing_type == 'amalgamationApplication',  # Check for the filing type
                where_clause  # Apply the JSON containment check
                ).one_or_none()

    # Check if a matching filing was found and if its effective date is greater than payment completion date
    if filing and filing.effective_date > filing.payment_completion_date:
        result.append({
            "code": "AMALGAMATING_BUSINESS",
            "message": "This business is part of a future effective amalgamation.",
            "warningType": WarningType.FUTURE_EFFECTIVE_AMALGAMATION,
            "data": {
                "amalgamationDate": filing.effective_date
            }
        })

    return result
