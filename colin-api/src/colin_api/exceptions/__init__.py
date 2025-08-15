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
"""Application Specific Exceptions, to manage the business errors.

@log_error - a decorator to automatically log the exception to the logger provided

"""


class GenericException(Exception):
    """Exception that adds error code and error name, that can be used for i18n support."""

    def __init__(self, error, status_code, *args, **kwargs):
        """Return a valid GenericException."""
        super().__init__(*args, **kwargs)
        self.error = error
        self.status_code = status_code

    def __str__(self):
        """Return the string representation of the exception."""
        return f'Error: {self.error}, Status Code: {self.status_code}'


class BusinessNotFoundException(GenericException):
    """Exception with defined error code and messaging."""

    def __init__(self, *args, identifier=None, **kwargs):
        """Return a valid BusinessNotFoundException."""
        super().__init__(None, None, *args, **kwargs)
        if identifier:
            self.error = f'{identifier} not found'
        else:
            self.error = 'Entity not found'
        self.status_code = 404


class FilingNotFoundException(GenericException):
    """Exception with defined error code and messaging."""

    def __init__(self, *args, identifier: str, filing_type: str, **kwargs):
        """Return a valid FilingNotFoundException."""
        super().__init__(None, None, *args, **kwargs)
        self.error = f'{filing_type} not found for {identifier}'
        self.status_code = 404


class OfficeNotFoundException(GenericException):
    """Exception with defined error code and messaging."""

    def __init__(self, *args, identifier: str = None, **kwargs):
        """Return a valid AddressNotFoundException."""
        super().__init__(None, None, *args, **kwargs)
        if identifier:
            self.error = f'Office not found for {identifier}'
        else:
            self.error = 'Office not found'
        self.status_code = 404


class AddressNotFoundException(GenericException):
    """Exception with defined error code and messaging."""

    def __init__(self, *args, address_id, **kwargs):
        """Return a valid AddressNotFoundException."""
        super().__init__(None, None, *args, **kwargs)
        if address_id:
            self.error = f'Address not found with id: {address_id}'
        else:
            self.error = 'Address not found'
        self.status_code = 404


class PartiesNotFoundException(GenericException):
    """Exception with defined error code and messaging."""

    def __init__(self, *args, identifier: str = None, **kwargs):
        """Return a valid PartiesNotFoundException."""
        super().__init__(None, None, *args, **kwargs)
        if identifier:
            self.error = f'Parties not found for {identifier}'
        else:
            self.error = 'Parties not found'
        self.status_code = 404


class NamesNotFoundException(GenericException):
    """Exception with defined error code and messaging."""

    def __init__(self, *args, identifier: str = None, **kwargs):
        """Return a valid NamesNotFoundException."""
        super().__init__(None, None, *args, **kwargs)
        if identifier:
            self.error = f'Corp names not found for {identifier}'
        else:
            self.error = 'Corp names not found'
        self.status_code = 404


class InvalidFilingTypeException(GenericException):
    """Exception with defined error code and messaging."""

    def __init__(self, *args, filing_type=None, **kwargs):
        """Return a valid InvalidFilingTypeException."""
        super().__init__(None, None, *args, **kwargs)
        if filing_type:
            self.error = f'{filing_type} is an invalid filing type'
        else:
            self.error = 'Filing type invalid'
        self.status_code = 400


class UnableToDetermineCorpTypeException(GenericException):
    """Exception with defined error code and messaging."""

    def __init__(self, *args, filing_type=None, **kwargs):
        """Return a valid UnableToDetermineCorpTypeException."""
        super().__init__(None, None, *args, **kwargs)
        if filing_type:
            self.error = f'Unable to determine corp type for {filing_type} filing type'
        else:
            self.error = 'Unable to determine corp type for filing type'
        self.status_code = 400
