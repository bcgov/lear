# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
# an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.

from .report import Report


class ReportOtann(Report):
    def __init__(self, filing):
        super().__init__(filing)

    def _get_template_filename(self):
        return 'OTANN.html'

    def _get_template_data(self):
        return {
            'agmDate': self.filing.filing_json['filing']['annualReport']['annualGeneralMeetingDate'],
            'annualReportYear': 'TODO',
            'businessNumber': 'TODO',
            'certifyingAuthor': 'TODO',
            'city': 'TODO',
            'cooperativeName': 'TODO',
            'filingDateTime': 'TODO',
            'incorporationNumber': 'TODO',
            'line_items': [
                {
                    'city': 'NOPE',
                    'directorFirstName': 'NOPE',
                    'directorLastName': 'NOPE',
                    'directorMiddleName': 'NOPE',
                    'postalCode': 'NOPE',
                    'region': 'NOPE',
                    'street': 'NOPE'
                },
                {
                    'city': 'NOPE',
                    'directorFirstName': 'NOPE',
                    'directorLastName': 'NOPE',
                    'directorMiddleName': 'NOPE',
                    'postalCode': 'NOPE',
                    'region': 'NOPE',
                    'street': 'NOPE'
                },
                {
                    'city': 'NOPE',
                    'directorFirstName': 'NOPE',
                    'directorLastName': 'NOPE',
                    'directorMiddleName': 'NOPE',
                    'postalCode': 'NOPE',
                    'region': 'NOPE',
                    'street': 'NOPE'
                }
            ],
            'postalCode': 'TODO',
            'region': 'TODO',
            'street': 'TODO'
        }
