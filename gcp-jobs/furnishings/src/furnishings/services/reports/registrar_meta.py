# Copyright © 2020 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
# an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
"""Holds the registrar meta data.

NOTE: This is copied from legal-api.
It was decided not to turn this into a common service as it is only used in 2 places."""
import base64
import datetime

from flask import current_app


class RegistrarInfo:
    """Utility to get the relevant registrar info for a filing."""

    registrar_info = [  # noqa: RUF012
        {
            "name": "RON TOWNSHEND",
            "title": "Registrar of Companies",
            "signatureImage": "registrar_signature_1.png",
            "signatureImageAndText": "",
            "startDate": "1970-01-01T00:00:00",
            "endDate": "2012-05-31T23:59:59"
        },
        {
            "name": "ANGELO COCCO",
            "title": "A/Registrar of Companies",
            "signatureImage": "registrar_signature_2.png",
            "signatureImageAndText": "",
            "startDate": "2012-06-01T00:00:00",
            "endDate": "2012-07-12T23:59:59"
        },
        {
            "name": "CAROL PREST",
            "title": "Registrar of Companies",
            "signatureImage": "registrar_signature_3.png",
            "signatureImageAndText": "registrar_signature_and_text_3.png",
            "startDate": "2012-07-13T00:00:00",
            "endDate": "2022-05-31T23:59:59"
        },
        {
            "name": "T.K. SPARKS",
            "title": "Registrar of Companies",
            "signatureImage": "registrar_signature_4.png",
            "signatureImageAndText": "registrar_signature_and_text_4.png",
            "startDate": "2022-06-01T00:00:00",
            'endDate': '2025-04-17T23:59:59'
        },
        {
            'name': "S. O\'CALLAGHAN",
            'title': 'Registrar of Companies',
            'signatureImage': 'registrar_signature_5.png',
            'signatureImageAndText': 'registrar_signature_and_text_5.png',
            'startDate': '2025-04-18T00:00:00',
            'endDate': None
        }
    ]

    @staticmethod
    def get_registrar_info(filing_effective_date) -> dict:
        """Return the registrar for a filing."""
        filing_effective_date = filing_effective_date.replace(tzinfo=None)
        registrar = next(x for x in RegistrarInfo.registrar_info
                          if (filing_effective_date >= datetime.datetime.strptime(x["startDate"], "%Y-%m-%dT%H:%M:%S") and
                              (x["endDate"] is None or
                               filing_effective_date <= datetime.datetime.strptime(x["endDate"], "%Y-%m-%dT%H:%M:%S"))))
        signature = RegistrarInfo.encode_registrar_signature(registrar["signatureImage"])
        registrar["signature"] = f"data:image/png;base64,{signature}"
        if registrar["signatureImageAndText"]:
            signature_and_text = RegistrarInfo.encode_registrar_signature(registrar["signatureImageAndText"])
            registrar["signatureAndText"] = f"data:image/png;base64,{signature_and_text}"
        return registrar

    @staticmethod
    def encode_registrar_signature(signature_image) -> str:
        """Return the encoded registrar signature."""
        template_path = current_app.config.get("REPORT_TEMPLATE_PATH")
        image_path = f"{template_path}/registrar_signatures/{signature_image}"
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read())
            return encoded_string.decode("utf-8")
