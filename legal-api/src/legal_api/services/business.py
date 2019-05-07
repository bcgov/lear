# Copyright © 2019 Province of remotetish Columbia
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
"""The Business service.

This module manages the Business's Legal Information.
"""
from datetime import datetime
from typing import Any, Dict, Tuple

from legal_api import status as http_status
from legal_api.exceptions import BusinessException
from legal_api.models import Business as BusinessModel

from .colin import Colin


class Business():  # pylint: disable=too-many-instance-attributes
    """Manages all aspects of the Business Entity.

    This manages storing the Business in the cache,
    ensuring that the local cache is up to date,
    submitting changes back to all storage systems as needed.
    """

    def __init__(self):
        """Return a Business Service object."""
        self.__dao = None
        self._dissolution_date: datetime = None
        self._fiscal_year_end_date: datetime = None
        self._founding_date: datetime = None
        self._identifier: str = None
        self._last_ledger_timestamp: datetime = None
        self._last_remote_ledger_timestamp: datetime = None
        self._legal_name: str = None
        self._tax_id: str = None

    @property
    def _dao(self):
        if not self.__dao:
            self.__dao = BusinessModel()
        return self.__dao

    @_dao.setter
    def _dao(self, value):
        self.__dao = value
        self.dissolution_date = self._dao.dissolution_date
        self.fiscal_year_end_date = self._dao.fiscal_year_end_date
        self.founding_date = self._dao.founding_date
        self.identifier = self._dao.identifier
        self.last_ledger_timestamp = self._dao.last_ledger_timestamp
        self.last_remote_ledger_timestamp = self._dao.last_remote_ledger_timestamp
        self.legal_name = self._dao.legal_name
        self.tax_id = self._dao.tax_id

    @property
    def dissolution_date(self):
        """Return the business dissolution_date."""
        return self._dissolution_date

    @dissolution_date.setter
    def dissolution_date(self, value: datetime):
        """Set the business dissolution_date."""
        self._dissolution_date = value
        self._dao.dissolution_date = value

    @property
    def fiscal_year_end_date(self):
        """Return the business fiscal year end date."""
        return self._fiscal_year_end_date

    @fiscal_year_end_date.setter
    def fiscal_year_end_date(self, value: datetime):
        """Set the business fiscal year end date."""
        self._fiscal_year_end_date = value
        self._dao.fiscal_year_end_date = value

    @property
    def founding_date(self):
        """Return the founding_date of the business."""
        return self._founding_date

    @founding_date.setter
    def founding_date(self, value: datetime):
        """Set the business founding_date."""
        self._founding_date = value
        self._dao.founding_date = value

    @property
    def identifier(self):
        """Return the unique business identifier."""
        return self._identifier

    @identifier.setter
    def identifier(self, value: str):
        """Set the business identifier."""
        if Business.validate_identifier(value):
            self._identifier = value
            self._dao.identifier = value
        else:
            raise BusinessException('invalid-identifier-format', 406)

    @property
    def last_ledger_timestamp(self):
        """Return the last date-time the business was altered."""
        return self._last_ledger_timestamp

    @last_ledger_timestamp.setter
    def last_ledger_timestamp(self, value: datetime):
        """Set the business last_update."""
        self._last_ledger_timestamp = value
        self._dao.last_ledger_timestamp = value

    @property
    def last_remote_ledger_timestamp(self):
        """Return the last date-time the business was altered."""
        return self._last_remote_ledger_timestamp

    @last_remote_ledger_timestamp.setter
    def last_remote_ledger_timestamp(self, value: datetime):
        """Set the business last_update."""
        self._last_remote_ledger_timestamp = value
        self._dao.last_remote_ledger_timestamp = value

    @property
    def legal_name(self):
        """Return the business legal_name."""
        return self._legal_name

    @legal_name.setter
    def legal_name(self, value: str):
        """Set the business legal_name."""
        self._legal_name = value
        self._dao.legal_name = value

    @property
    def tax_id(self):
        """Return the business tax_id."""
        return self._tax_id

    @tax_id.setter
    def tax_id(self, value: str):
        """Set the business tax_id."""
        self._tax_id = value
        self._dao.tax_id = value

    def asdict(self):
        """Return the Business as a python dict.

        None fields are not included in the dict.
        """
        d = {
            'founding_date': self.founding_date.isoformat(),
            'identifier': self.identifier,
            'legal_name': self.legal_name,
        }
        if self.last_remote_ledger_timestamp:
            # this is not a typo, we want the external facing view object ledger timestamp to be the remote one
            d['last_ledger_timestamp'] = self.last_remote_ledger_timestamp.isoformat()
        else:
            d['last_ledger_timestamp'] = None

        if self.dissolution_date:
            d['dissolution_date'] = datetime.date(self.dissolution_date).isoformat()
        if self.fiscal_year_end_date:
            d['fiscal_year_end_date'] = datetime.date(self.fiscal_year_end_date).isoformat()
        if self.tax_id:
            d['tax_id'] = self.tax_id
        return d

    def save(self):
        """Save the business information to the local cache."""
        self._dao.save()

    @staticmethod
    def validate_identifier(identifier: str) -> bool:
        """Validate the identifier meets the Registry naming standards.

        CP = BC COOPS or XCP = Expro COOP + 7 digits.
        ie: CP1234567 or XCP1234567
        All legal entities with BC Reg are PREFIX + 7 digits
        """
        if len(identifier) < 9:
            return False

        try:
            d = int(identifier[-7:])
            if d == 0:
                return False
        except ValueError:
            return False

        if identifier[:-7] not in ('CP', 'XCP'):
            return False

        return True

    @classmethod
    def find_by_legal_name(cls, legal_name: str = None) -> Tuple[object, int]:
        """Given a legal_name, this will return an Active Business or None."""
        if not legal_name:
            return None, http_status.HTTP_400_BAD_REQUEST

        # find locally
        business_dao = None
        business_dao = BusinessModel.find_by_legal_name(legal_name)

        # TODO check if timestamp is valid in Colin

        if not business_dao:
            return None

        b = Business()
        b._dao = business_dao  # pylint: disable=protected-access
        return b

    @classmethod
    def find_by_identifier(cls, identifier: str = None) -> Tuple[object, int]:
        """Given a business identifier, this will return an Active Business or None."""
        if not identifier:
            return None, http_status.HTTP_400_BAD_REQUEST

        # find locally
        business_dao = None
        business_dao = BusinessModel.find_by_identifier(identifier)

        business_remote = Colin.get_business_by_identifier(identifier)

        return Business._coalesce_cache(business_dao, business_remote)

    @staticmethod
    def _coalesce_cache(business_dao: BusinessModel, business_remote: Tuple[Dict[str, Any], int]) -> Tuple[object, int]:
        """Return the Business object and Status from the cache and remote api.

        This gets the cache respones and remote, if available,
        and if necessary the cache of the business info is updated.
        The comparison of the remote and cache ledger timestamp defines the state of the cache.
        """
        if not business_dao and not business_remote[0]:
            return None, http_status.HTTP_404_NOT_FOUND

        if business_remote[0] and business_remote[1] == 200:
            remote = business_remote[0].get('business_info')
            if not remote:

                return None, http_status.HTTP_204_NO_CONTENT

            b = Business()
            if not business_dao:
                b.identifier = remote.get('identifier')
                b.last_remote_ledger_timestamp = datetime.fromisoformat(remote.get('last_ledger_timestamp'))
                b.legal_name = remote.get('legal_name')
                b.founding_date = datetime.fromisoformat(remote.get('founding_date'))
                b.tax_id = remote.get('tax_id')
                b.save()

            elif business_dao.last_remote_ledger_timestamp.isoformat() \
                    == remote.get('last_ledger_timestamp'):
                b._dao = business_dao  # pylint: disable=protected-access

            elif business_dao.last_remote_ledger_timestamp.isoformat() \
                    < remote.get('last_ledger_timestamp'):
                b._dao = business_dao  # pylint: disable=protected-access
                b.last_remote_ledger_timestamp = datetime.fromisoformat(remote.get('last_ledger_timestamp'))
                b.legal_name = remote.get('legal_name')
                b.founding_date = datetime.fromisoformat(remote.get('founding_date'))
                b.tax_id = remote.get('tax_id')
                b.save()

            return b, http_status.HTTP_200_OK

        if business_dao:
            b = Business()
            b._dao = business_dao  # pylint: disable=protected-access

            return b, http_status.HTTP_203_NON_AUTHORITATIVE_INFORMATION

        return None, http_status.HTTP_404_NOT_FOUND
