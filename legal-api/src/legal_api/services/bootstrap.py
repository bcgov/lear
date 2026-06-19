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

"""This is a service to bootstrap the Incorporation Application process."""
import contextlib
import secrets
import string
from http import HTTPStatus

from flask_babel import _ as babel
from sqlalchemy.orm.exc import FlushError

from business_account import AccountService
from business_model.models import RegistrationBootstrap
from legal_api.services import flags


class RegistrationBootstrapService:
    """Provides services to bootstrap the IA registration and account affiliation."""

    @staticmethod
    def create_bootstrap(account: int) -> dict | RegistrationBootstrap:
        """Return either a new bootstrap registration or an error struct."""
        if not account:
            return {"error": babel("An account number must be provided.")}

        bootstrap = RegistrationBootstrap(account=account)

        # try to create a bootstrap registration with a unique ID
        for _ in range(5):
            try:
                bootstrap.identifier = RegistrationBootstrapService._generate_temp_identifier()
                bootstrap.save()
                return bootstrap
            except FlushError:
                pass  # we try again
            except Exception:
                break

        return {"error": babel("Unable to create bootstrap registration.")}

    @staticmethod
    def _generate_temp_identifier():
        """Generate a 10 character string which starts with `T` and have at least 1 digit."""
        allowed_encoded = string.ascii_letters + string.digits
        identifier = None
        while True:
            identifier = "T" + "".join(secrets.choice(allowed_encoded) for _ in range(9))
            if any(c.isdigit() for c in identifier):  # identifier requires at least 1 digit (as per auth-api)
                break
        return identifier

    @staticmethod
    def delete_bootstrap(bootstrap: RegistrationBootstrap):
        """Delete the bootstrap registration."""
        with contextlib.suppress(Exception):
            bootstrap.delete()
        return HTTPStatus.OK

    @staticmethod
    def register_bootstrap(bootstrap: RegistrationBootstrap,
                           business_name: str,
                           nr_number: str | None = None,
                           corp_type_code: str = "TMP",
                           corp_sub_type_code: str | None = None) -> HTTPStatus | dict:
        """Return either a new bootstrap registration or an error struct."""
        if not bootstrap:
            return {"error": babel("An account number must be provided.")}

        details = {
            "bootstrapIdentifier": bootstrap.identifier,
            "identifier": None,
            "nrNumber": nr_number
        }

        rv = AccountService.create_affiliation(account=bootstrap.account,
                                               business_registration=bootstrap.identifier,
                                               business_name=business_name,
                                               corp_type_code=corp_type_code,
                                               corp_sub_type_code=corp_sub_type_code,
                                               details=details,
                                               flags=flags)

        if rv == HTTPStatus.OK:
            return HTTPStatus.OK

        with contextlib.suppress(Exception):
            AccountService.delete_affiliation(account=bootstrap.account,
                                              business_registration=bootstrap.identifier)
        return {"error": babel("Unable to create bootstrap registration.")}

    @staticmethod
    def deregister_bootstrap(bootstrap: RegistrationBootstrap) -> HTTPStatus:
        """Remove the bootstrap registration."""
        affiliation_status = AccountService.delete_affiliation(account=bootstrap.account,
                                                               business_registration=bootstrap.identifier)
        return affiliation_status
