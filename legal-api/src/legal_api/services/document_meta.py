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

from legal_api.models import Business, Filing
from legal_api.utils.legislation_datetime import LegislationDatetime

from .namex import NameXService


class DocumentMetaService():
    """Provides service for document meta data."""

    NOTICE_OF_ARTICLES = 'Notice of Articles'

    class DocumentType(Enum):
        """Define an enum of document types."""

        REPORT = 'REPORT'

    class ReportType(Enum):
        """Define an enum of report types."""

        CERTIFICATE = 'certificate'
        NOTICE_OF_ARTICLES = 'noa'
        ALTERATION_NOTICE = 'alterationNotice'

    def __init__(self):
        """Create the document meta instance."""
        # init global attributes
        self._business_identifier = None
        self._legal_type = None
        self._filing_status = None
        self._filing_id = None
        self._filing_date = None

    def get_documents(self, filing: dict):
        """Return an array of document meta for a filing."""
        # look up legal type
        self._business_identifier = filing['filing']['business']['identifier']
        # if this is a temp registration then there is no business, so get legal type from filing
        if self._business_identifier.startswith('T'):
            self._legal_type = filing['filing']['incorporationApplication']['nameRequest']['legalType']
        else:
            business = Business.find_by_identifier(self._business_identifier)
            if not business:
                return []  # business not found
            self._legal_type = business.legal_type

        self._filing_status = filing['filing']['header']['status']
        is_paper_only = filing['filing']['header']['availableOnPaperOnly']

        if self._filing_status not in (Filing.Status.COMPLETED.value, Filing.Status.PAID.value) or is_paper_only:
            return []  # wrong filing status

        return self.get_documents2(filing)

    def get_documents2(self, filing: dict):
        """Return an array of document meta for a filing."""
        filing_type = filing['filing']['header']['name']
        self._filing_id = filing['filing']['header']['filingId']
        self._filing_date = filing['filing']['header']['date']

        documents = []
        if filing_type == 'incorporationApplication':
            documents = self.get_incorporation_application_reports(filing)
        elif filing_type == 'annualReport':
            documents = self.get_ar_reports()
        elif filing_type == 'changeOfAddress':
            documents = self.get_coa_reports()
        elif filing_type == 'changeOfDirectors':
            documents = self.get_cod_reports()
        elif filing_type == 'changeOfName':
            documents = self.get_con_reports()
        elif filing_type == 'specialResolution':
            documents = self.get_special_resolution_reports()
        elif filing_type == 'voluntaryDissolution':
            documents = self.get_voluntary_dissolution_reports()
        elif filing_type == 'correction':
            documents = self.get_correction_reports(filing)
        elif filing_type == 'alteration':
            documents = self.get_alteration_reports(filing)
        elif filing_type == 'transition':
            documents = self.get_transition_reports()

        return documents

    def get_ar_reports(self):
        """Return annual report meta object(s)."""
        # whether PAID or COMPLETED, whether BCOMP or COOP, return just AR object
        return [
            self.create_report_object(
                'Annual Report',
                self.get_general_filename('Annual Report')
            )
        ]

    def get_coa_reports(self):
        """Return change of address meta object(s)."""
        reports = [
            self.create_report_object(
                'Address Change',
                self.get_general_filename('Address Change')
            )
        ]

        # when BCOMP filing is completed, also return NOA
        if self.is_bcomp() and self.is_completed():
            reports.append(
                self.create_report_object(
                    DocumentMetaService.NOTICE_OF_ARTICLES,
                    self.get_general_filename(DocumentMetaService.NOTICE_OF_ARTICLES),
                    DocumentMetaService.ReportType.NOTICE_OF_ARTICLES.value
                )
            )

        return reports

    def get_cod_reports(self):
        """Return change of director meta object(s)."""
        reports = [
            self.create_report_object(
                'Director Change',
                self.get_general_filename('Director Change')
            )
        ]

        # when BCOMP filing is completed, also return NOA
        if self.is_bcomp() and self.is_completed():
            reports.append(
                self.create_report_object(
                    DocumentMetaService.NOTICE_OF_ARTICLES,
                    self.get_general_filename(DocumentMetaService.NOTICE_OF_ARTICLES),
                    DocumentMetaService.ReportType.NOTICE_OF_ARTICLES.value
                )
            )

        return reports

    def get_con_reports(self):
        """Return change of name object(s)."""
        reports = [
            self.create_report_object(
                'Legal Name Change',
                self.get_general_filename('Legal Name Change')
            )
        ]

        # when BCOMP filing is completed, also return NOA
        if self.is_bcomp() and self.is_completed():
            reports.append(
                self.create_report_object(
                    DocumentMetaService.NOTICE_OF_ARTICLES,
                    self.get_general_filename(DocumentMetaService.NOTICE_OF_ARTICLES),
                    DocumentMetaService.ReportType.NOTICE_OF_ARTICLES.value
                )
            )

        return reports

    def get_special_resolution_reports(self):
        """Return special resolution meta object(s)."""
        reports = []

        if self.is_completed():
            reports.append(
                self.create_report_object(
                    'Special Resolution',
                    self.get_general_filename('Special Resolution')
                )
            )

        return reports

    def get_voluntary_dissolution_reports(self):
        """Return voluntary dissolution meta object(s)."""
        reports = []

        if self.is_completed():
            reports.append(
                self.create_report_object(
                    'Voluntary Dissolution',
                    self.get_general_filename('Voluntary Dissolution')
                )
            )

        return reports

    def get_correction_reports(self, filing: dict):
        """Return correction meta object(s)."""
        reports = []

        if Filing.FILINGS['incorporationApplication'].get('name') in filing['filing'].keys():
            reports = self.get_corrected_ia_reports(filing)

        return reports

    def get_corrected_ia_reports(self, filing: dict):
        """Return corrected incorporation application meta object(s)."""
        reports = []

        reports.append(self.create_report_object(
            'Incorporation Application (Corrected)',
            self.get_general_filename('Incorporation Application (Corrected)')
        ))

        if self.is_completed():
            if NameXService.has_correction_changed_name(filing):
                reports.append(self.create_report_object(
                    'Certificate (Corrected)',
                    self.get_general_filename('Certificate (Corrected)'),
                    DocumentMetaService.ReportType.CERTIFICATE.value
                ))

            reports.append(self.create_report_object(
                DocumentMetaService.NOTICE_OF_ARTICLES,
                self.get_general_filename(DocumentMetaService.NOTICE_OF_ARTICLES),
                DocumentMetaService.ReportType.NOTICE_OF_ARTICLES.value
            ))

        return reports

    def get_transition_reports(self):  # pylint: disable=no-self-use
        """Return transition meta object(s)."""
        reports = []

        if self.is_paid():
            reports.append(
                self.create_report_object(
                    'Transition Application - Pending',
                    self.get_general_filename('Transition Application (Pending)')
                )
            )
        else:
            reports.append(
                self.create_report_object(
                    'Transition Application',
                    self.get_general_filename('Transition Application')
                )
            )

        if self.is_completed():
            reports.append(
                self.create_report_object(
                    DocumentMetaService.NOTICE_OF_ARTICLES,
                    self.get_general_filename(DocumentMetaService.NOTICE_OF_ARTICLES),
                    DocumentMetaService.ReportType.NOTICE_OF_ARTICLES.value
                )
            )

        return reports

    def get_alteration_reports(self, filing: dict):  # pylint: disable=no-self-use
        """Return alteration meta object(s)."""
        reports = []

        if self.is_completed():
            reports.append(
                self.create_report_object(
                    DocumentMetaService.NOTICE_OF_ARTICLES,
                    self.get_general_filename(DocumentMetaService.NOTICE_OF_ARTICLES),
                    DocumentMetaService.ReportType.NOTICE_OF_ARTICLES.value
                )
            )

            reports.append(
                self.create_report_object(
                    'Alteration Notice',
                    self.get_general_filename('Alteration Notice')
                )
            )
            if 'nameRequest' in filing['filing']['alteration']:
                reports.append(
                    self.create_report_object(
                        'Change of Name Certificate',
                        self.get_general_filename('Change of Name Certificate')
                    )
                )

        return reports

    def get_incorporation_application_reports(self, filing: dict):
        """Return incorporation application meta object(s)."""
        is_fed = LegislationDatetime.is_future(filing['filing']['header']['effectiveDate'])

        # return FED instead of PAID or COMPLETED
        if is_fed:
            return [
                self.create_report_object(
                    'Incorporation Application - Future Effective Incorporation',
                    self.get_general_filename('Incorporation Application (Future Effective)')
                )
            ]

        if self.is_paid():
            return [
                self.create_report_object(
                    'Incorporation Application - Pending',
                    self.get_general_filename('Incorporation Application (Pending)')
                )
            ]

        filing_data = Filing.find_by_id(filing['filing']['header']['filingId'])
        has_corrected = filing_data.parent_filing_id is not None  # Identify whether it is corrected
        label_original = ' (Original)' if has_corrected else ''
        label_certificate_original = ' (Original)' if has_corrected and NameXService.\
            has_correction_changed_name(Filing.find_by_id(filing_data.parent_filing_id).json) else ''

        # else status is COMPLETED
        return [
            self.create_report_object(
                f'Incorporation Application{label_original}',
                self.get_general_filename(f'Incorporation Application{label_original}')
            ),
            self.create_report_object(
                DocumentMetaService.NOTICE_OF_ARTICLES,
                self.get_general_filename(DocumentMetaService.NOTICE_OF_ARTICLES),
                DocumentMetaService.ReportType.NOTICE_OF_ARTICLES.value
            ),

            self.create_report_object(
                f'Certificate{label_certificate_original}',
                self.get_general_filename(f'Certificate{label_certificate_original}'),
                DocumentMetaService.ReportType.CERTIFICATE.value
            )
        ]

    def create_report_object(self, title: str, filename: str, report_type=None):
        """Return a populated document meta object."""
        return {
            'type': DocumentMetaService.DocumentType.REPORT.value,
            'reportType': report_type,
            'filingId': self._filing_id,
            'title': title,
            'filename': filename
        }

    def get_general_filename(self, name: str):
        """Return a general filename string."""
        filing_date_str = LegislationDatetime.format_as_legislation_date(self._filing_date)
        file_name = f'{self._business_identifier} - {name} - {filing_date_str}.pdf'
        return file_name

    def is_bcomp(self):
        """Return True if this entity is a BCOMP."""
        return self._legal_type == Business.LegalTypes.BCOMP.value

    def is_paid(self):
        """Return True if this filing is PAID."""
        return self._filing_status == Filing.Status.PAID.value

    def is_completed(self):
        """Return True if this filing is COMPLETED."""
        return self._filing_status == Filing.Status.COMPLETED.value
