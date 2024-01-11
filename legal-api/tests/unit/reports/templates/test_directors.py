# Copyright © 2021 Province of British Columbia
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
"""Directors template tests."""

from pathlib import Path
from typing import Final

import pytest
from flask import current_app
from jinja2 import Template


def get_template(template):
    """Returns the template."""
    template_path = current_app.config.get("REPORT_TEMPLATE_PATH")
    template_code = Path(f"{template_path}{template}").read_text()
    return Template(template_code)


@pytest.mark.parametrize(
    "parties,template",
    [
        (
            [
                {
                    "id": "462008",
                    "roles": [
                        {"id": "Completing Party", "roleType": "Completing Party", "appointmentDate": "2021-10-06"},
                        {"id": "Director", "roleType": "Director", "appointmentDate": "2021-10-06"},
                    ],
                    "officer": {
                        "id": "441465",
                        "email": "andre.pestana@aot-technologies.com",
                        "lastName": "FORTYSIX",
                        "firstName": "BCREGTEST LEAH",
                        "partyType": "person",
                    },
                    "mailingAddress": {
                        "postalCode": "V8L 5V4",
                        "addressCity": "North Saanich",
                        "addressRegion": "BC",
                        "streetAddress": "123-1640 Electra Blvd",
                        "addressCountry": "Canada",
                        "deliveryInstructions": "",
                        "streetAddressAdditional": "",
                        "addressCountryDescription": "Canada",
                    },
                    "deliveryAddress": {
                        "postalCode": "V8L 5V4",
                        "addressCity": "North Saanich",
                        "addressRegion": "BC",
                        "streetAddress": "123-1640 Electra Blvd",
                        "addressCountry": "Canada",
                        "deliveryInstructions": "",
                        "streetAddressAdditional": "",
                        "addressCountryDescription": "Canada",
                    },
                },
                {
                    "id": "441466",
                    "roles": [{"roleType": "Incorporator", "appointmentDate": "2021-10-06"}],
                    "officer": {"id": "462009", "partyType": "organization", "organizationName": "KJHGF 1234"},
                    "mailingAddress": {
                        "postalCode": "V6A 4H6",
                        "addressCity": "Vancouver",
                        "addressRegion": "BC",
                        "streetAddress": "432-289 Alexander St",
                        "addressCountry": "Canada",
                        "deliveryInstructions": "",
                        "streetAddressAdditional": "",
                        "addressCountryDescription": "Canada",
                    },
                },
            ],
            "/template-parts/common/directors.html",
        ),
        (
            [
                {
                    "officer": {"firstName": "FREDERICKSSON", "lastName": "SCHWARTZ", "partyType": "person"},
                    "deliveryAddress": {
                        "streetAddress": "123-1640 Electra Blvd",
                        "streetAddressAdditional": "",
                        "addressCity": "North Saanich",
                        "addressRegion": "BC",
                        "addressCountry": "CA",
                        "addressCountryDescription": "Canada",
                        "postalCode": "V8L 5V4",
                        "deliveryInstructions": "",
                    },
                    "mailingAddress": {
                        "streetAddress": "123-1640 Electra Blvd",
                        "streetAddressAdditional": "",
                        "addressCity": "North Saanich",
                        "addressRegion": "BC",
                        "addressCountry": "CA",
                        "addressCountryDescription": "Canada",
                        "postalCode": "V8L 5V4",
                        "deliveryInstructions": "",
                    },
                    "id": "441465",
                    "appointmentDate": "2021-10-04",
                    "cessationDate": None,
                    "role": "completing_party",
                },
                {
                    "officer": {"firstName": "BCREGTEST LEAH", "lastName": "FORTYSIX", "partyType": "person"},
                    "deliveryAddress": {
                        "streetAddress": "123-1640 Electra Blvd",
                        "streetAddressAdditional": "",
                        "addressCity": "North Saanich",
                        "addressRegion": "BC",
                        "addressCountry": "CA",
                        "addressCountryDescription": "Canada",
                        "postalCode": "V8L 5V4",
                        "deliveryInstructions": "",
                    },
                    "mailingAddress": {
                        "streetAddress": "123-1640 Electra Blvd",
                        "streetAddressAdditional": "",
                        "addressCity": "North Saanich",
                        "addressRegion": "BC",
                        "addressCountry": "CA",
                        "addressCountryDescription": "Canada",
                        "postalCode": "V8L 5V4",
                        "deliveryInstructions": "",
                    },
                    "id": "441465",
                    "appointmentDate": "2021-10-04",
                    "cessationDate": None,
                    "role": "director",
                },
                {
                    "officer": {"organizationName": "KJHGF 1234", "partyType": "organization"},
                    "mailingAddress": {
                        "streetAddress": "123-1640 Electra Blvd",
                        "streetAddressAdditional": "",
                        "addressCity": "North Saanich",
                        "addressRegion": "BC",
                        "addressCountry": "CA",
                        "addressCountryDescription": "Canada",
                        "postalCode": "V8L 5V4",
                        "deliveryInstructions": "",
                    },
                    "cessationDate": None,
                    "appointmentDate": "2021-10-04",
                    "id": "441466",
                    "role": "incorporator",
                },
            ],
            "/template-parts/notice-of-articles/directors.html",
        ),
    ],
)
def test_render_directors(session, parties, template):
    """Test Directors rendering."""
    template = get_template(template)
    rendered = template.render(parties=parties)

    assert "KJHGF 1234" not in rendered
    assert "FREDERICKSSON" not in rendered
    assert "BCREGTEST LEAH" in rendered
