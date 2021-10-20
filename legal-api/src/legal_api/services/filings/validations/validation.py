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
"""Common validation entry point for all filing submissions."""
from typing import Dict

from legal_api.errors import Error
from legal_api.models import Business, Filing

from .alteration import validate as alteration_validate
from .annual_report import validate as annual_report_validate
from .change_of_address import validate as coa_validate
from .change_of_directors import validate as cod_validate
from .change_of_name import validate as con_validate
from .correction import validate as correction_validate
from .court_order import validate as court_order_validate
from .dissolution import validate as dissolution_validate
from .incorporation_application import validate as incorporation_application_validate
from .incorporation_application import validate_correction_ia
from .registrars_notation import validate as registrars_notation_validate
from .registrars_order import validate as registrars_order_validate
from .schemas import validate_against_schema
from .special_resolution import validate as special_resolution_validate


def validate(business: Business, filing_json: Dict) -> Error:  # pylint: disable=too-many-branches
    """Validate the filing JSON."""
    err = validate_against_schema(filing_json)
    if err:
        return err

    err = None

    # check if this is a correction - if yes, ignore all other filing types in the filing since they will be validated
    # differently in a future version of corrections
    if 'correction' in filing_json['filing'].keys():
        err = correction_validate(business, filing_json)
        if err:
            return err

        # For now the correction validators will get called here, these might be the same rules
        # so these 2 sections could get collapsed
        for k in filing_json['filing'].keys():
            # Check if the JSON key exists in the FILINGS reference Dictionary
            if Filing.FILINGS.get(k, None):

                if k == Filing.FILINGS['changeOfAddress'].get('name'):
                    err = coa_validate(business, filing_json)

                elif k == Filing.FILINGS['incorporationApplication'].get('name'):
                    err = validate_correction_ia(filing_json)

        if err:
            return err

    else:
        for k in filing_json['filing'].keys():
            # Check if the JSON key exists in the FILINGS reference Dictionary
            if Filing.FILINGS.get(k, None):
                # The type of this Filing exists in the JSON, determine which
                # one it is (Annual Report, Change of Address, or Change of Directors)
                # and validate against the appropriate logic

                if k == Filing.FILINGS['annualReport'].get('name'):
                    err = annual_report_validate(business, filing_json)

                elif k == Filing.FILINGS['changeOfAddress'].get('name'):
                    err = coa_validate(business, filing_json)

                elif k == Filing.FILINGS['changeOfDirectors'].get('name'):
                    err = cod_validate(business, filing_json)

                elif k == Filing.FILINGS['changeOfName'].get('name'):
                    err = con_validate(business, filing_json)

                elif k == Filing.FILINGS['dissolution'].get('name'):
                    err = dissolution_validate(business, filing_json)

                elif k == Filing.FILINGS['specialResolution'].get('name'):
                    err = special_resolution_validate(business, filing_json)

                elif k == Filing.FILINGS['incorporationApplication'].get('name'):
                    err = incorporation_application_validate(filing_json)

                elif k == Filing.FILINGS['alteration'].get('name'):
                    err = alteration_validate(business, filing_json)

                elif k == Filing.FILINGS['courtOrder'].get('name'):
                    err = court_order_validate(business, filing_json)

                elif k == Filing.FILINGS['registrarsNotation'].get('name'):
                    err = registrars_notation_validate(business, filing_json)

                elif k == Filing.FILINGS['registrarsOrder'].get('name'):
                    err = registrars_order_validate(business, filing_json)

                if err:
                    return err

    return None
