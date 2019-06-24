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
        super(GenericException, self).__init__(*args, **kwargs)
        self.error = error
        self.status_code = status_code


class BusinessNotFoundException(GenericException):
    """Exception with defined error code and messaging."""

    def __init__(self, *args, identifier=None, **kwargs):
        """Return a valid BusinessNotFoundException."""
        super(BusinessNotFoundException, self).__init__(*args, **kwargs)
        if identifier:
            self.error = f'{identifier} not found'
        else:
            self.error = 'Entity not found'
        self.status_code = 404


class FilingNotFoundException(GenericException):
    """Exception with defined error code and messaging."""

    def __init__(self, *args, identifier=None, filing_type=None, **kwargs):
        """Return a valid FilingNotFoundException."""
        super(FilingNotFoundException, self).__init__(*args, **kwargs)
        if identifier and filing_type:
            self.error = f'{filing_type} not found for {identifier}'
        else:
            self.error = 'Filing not found'
        self.status_code = 404


class AddressNotFoundException(GenericException):
    """Exception with defined error code and messaging."""

    def __init__(self, *args, identifier=None, address_type=None, **kwargs):
        """Return a valid AddressNotFoundException."""
        super(AddressNotFoundException, self).__init__(*args, **kwargs)
        if identifier and address_type:
            self.error = f'{address_type} not found with id: {identifier}'
        else:
            self.error = 'Address not found'
        self.status_code = 404


class DirectorsNotFoundException(GenericException):
    """Exception with defined error code and messaging."""

    def __init__(self, *args, identifier=None, **kwargs):
        """Return a valid DirectorsNotFoundException."""
        super(DirectorsNotFoundException, self).__init__(*args, **kwargs)
        if identifier:
            self.error = f'Directors not found for: {identifier}'
        else:
            self.error = 'Directors not found'
        self.status_code = 404


class InvalidFilingTypeException(GenericException):
    """Exception with defined error code and messaging."""

    def __init__(self, *args, filing_type=None, **kwargs):
        """Return a valid InvalidFilingTypeException."""
        super(InvalidFilingTypeException, self).__init__(*args, **kwargs)
        if filing_type:
            self.error = f'{filing_type} is an invalid filing type'
        else:
            self.error = 'Filing type invalid'
        self.status_code = 400
