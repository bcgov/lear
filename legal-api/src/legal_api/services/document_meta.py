# Copyright © 2020 Province of British Columbia
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

"""This provides the service for filings documents meta data."""

from enum import Enum

from legal_api.models import Filing
from legal_api.utils.legislation_datetime import LegislationDatetime


class DocumentMetaService():
    """Provides service for document meta data."""

    class DocumentType(Enum):
        """Define an enum of document types."""

        REPORT = 'REPORT'

    class ReportType(Enum):
        """Define an enum of report types."""

        CERTIFICATE = 'certificate'
        NOTICE_OF_ARTICLES = 'noa'

    def get_documents(self, filing: dict):
        """Return an array of document meta for a filing."""
        business_identifier = filing['filing']['business']['identifier']
        filing_id = filing['filing']['header']['filingId']
        filing_date = filing['filing']['header']['date']
        filing_status = filing['filing']['header']['status']
        filing_type = filing['filing']['header']['name']
        paper_only = filing['filing']['header']['availableOnPaperOnly']
        documents = []

        if filing_status not in (Filing.Status.COMPLETED.value, Filing.Status.PAID.value) or paper_only:
            return []

        if filing_type == 'annualReport':
            documents = self.get_annual_report(filing_id, business_identifier, filing_date)
        elif filing_type == 'changeOfAddress':
            documents = self.get_coa_report(filing_id, business_identifier, filing_date)
        elif filing_type == 'changeOfDirectors':
            documents = self.get_cod_report(filing_id, business_identifier, filing_date)
        elif filing_type == 'changeOfName':
            documents = self.get_con_report(filing_id, business_identifier, filing_date)
        elif filing_type == 'specialResolution':
            documents = self.get_special_resolution_report(filing_id, business_identifier, filing_date)
        elif filing_type == 'voluntaryDissolution':
            documents = self.get_voluntary_dissolution_report(filing_id, business_identifier, filing_date)
        elif filing_type == 'incorporationApplication':
            documents = self.get_incorporation_application_report(filing)

        return documents

    def get_annual_report(self, filing_id, business_identifier, filing_date):
        """Return an annual report document meta object."""
        return [self.create_report_object(filing_id, 'Annual Report',
                                          self.get_general_filename(business_identifier,
                                                                    'Annual Report', filing_date, 'pdf'))]

    def get_coa_report(self, filing_id, business_identifier, filing_date):
        """Return a change of address report document meta object."""
        return [self.create_report_object(filing_id, 'Address Change',
                                          self.get_general_filename(business_identifier,
                                                                    'Address Change', filing_date, 'pdf'))]

    def get_cod_report(self, filing_id, business_identifier, filing_date):
        """Return a change of director report document meta object."""
        return [self.create_report_object(filing_id, 'Director Change',
                                          self.get_general_filename(business_identifier,
                                                                    'Director Change', filing_date, 'pdf'))]

    def get_con_report(self, filing_id, business_identifier, filing_date):
        """Return a change of name report document meta object."""
        return [self.create_report_object(filing_id, 'Legal Name Change',
                                          self.get_general_filename(business_identifier,
                                                                    'Legal Name Change', filing_date, 'pdf'))]

    def get_special_resolution_report(self, filing_id, business_identifier, filing_date):
        """Return a special resolution report document meta object."""
        return [self.create_report_object(filing_id, 'Special Resolution',
                                          self.get_general_filename(business_identifier,
                                                                    'Special Resolution', filing_date, 'pdf'))]

    def get_voluntary_dissolution_report(self, filing_id, business_identifier, filing_date):
        """Return a voluntary dissolution report document meta object."""
        return [self.create_report_object(filing_id, 'Voluntary Dissolution',
                                          self.get_general_filename(business_identifier,
                                                                    'Voluntary Dissolution', filing_date, 'pdf'))]

    def get_incorporation_application_report(self, filing: dict):
        """Return a incoporation application report document meta object."""
        filing_id = filing_id = filing['filing']['header']['filingId']
        business_identifier = filing['filing']['business']['identifier']
        filing_date = filing['filing']['header']['date']
        is_fed = LegislationDatetime.is_future(filing['filing']['header']['effectiveDate'])
        ia_name = 'Incorporation Application'
        certificate_name = 'Certificate'
        noa_name = 'Notice of Articles'
        if is_fed:
            return [
                self.create_report_object(filing_id,
                                          f'{ia_name} - Future Effective Incorporation',
                                          self.get_general_filename(business_identifier,
                                                                    f'{ia_name} (Future Effective)',
                                                                    filing_date,
                                                                    'pdf'
                                                                    )
                                          )
            ]
        return [
            self.create_report_object(filing_id, 'Incorporation Application',
                                      self.get_general_filename(business_identifier,
                                                                'Incorporation Application', filing_date, 'pdf')),
            self.create_report_object(filing_id, noa_name,
                                      self.get_general_filename(business_identifier,
                                                                'Notice of Articles', filing_date, 'pdf'),
                                      DocumentMetaService.ReportType.NOTICE_OF_ARTICLES.value),

            self.create_report_object(filing_id, certificate_name,
                                      self.get_general_filename(business_identifier,
                                                                'Certificate', filing_date, 'pdf'),
                                      DocumentMetaService.ReportType.CERTIFICATE.value)
        ]

    @staticmethod
    def create_report_object(filing_id, title, filename, report_type=None):
        """Return a populated document meta object."""
        return {
            'type': DocumentMetaService.DocumentType.REPORT.value,
            'reportType': report_type,
            'filingId': filing_id,
            'title': title,
            'filename': filename
        }

    @staticmethod
    def get_general_filename(business_identifier: str, name: str, filing_date: str, file_extension: str):
        """Return a general filename string."""
        filing_date_str = LegislationDatetime.format_as_legislation_date(filing_date)
        file_name = f'{business_identifier} - {name} - {filing_date_str}.{file_extension}'
        return file_name
