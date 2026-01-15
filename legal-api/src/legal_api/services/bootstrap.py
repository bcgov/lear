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
import json
import secrets
import string
from http import HTTPStatus
from typing import Optional, Union

import requests
from flask import current_app, has_request_context
from flask_babel import _ as babel
from sqlalchemy.orm.exc import FlushError

from legal_api.models import RegistrationBootstrap
from legal_api.services import Flags, flags
from legal_api.utils.auth import jwt


class RegistrationBootstrapService:
    """Provides services to bootstrap the IA registration and account affiliation."""

    @staticmethod
    def create_bootstrap(account: int) -> Union[dict, RegistrationBootstrap]:
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
                           nr_number: Optional[str] = None,
                           corp_type_code: str = "TMP",
                           corp_sub_type_code: Optional[str] = None) -> Union[HTTPStatus, dict]:
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


class AccountService:
    """Wrapper to call Authentication Services.

    @TODO Cache and refresh / retry token as needed to reduce calls.
    """

    BEARER: str = "Bearer "
    CONTENT_TYPE_JSON = {"Content-Type": "application/json"}

    try:
        timeout = int(current_app.config.get("ACCOUNT_SVC_TIMEOUT", 20))
    except Exception:
        timeout = 20

    @classmethod
    def get_bearer_token(cls):
        """Get a valid Bearer token for the service to use."""
        token_url = current_app.config.get("ACCOUNT_SVC_AUTH_URL")
        client_id = current_app.config.get("ACCOUNT_SVC_CLIENT_ID")
        client_secret = current_app.config.get("ACCOUNT_SVC_CLIENT_SECRET")

        data = "grant_type=client_credentials"

        # get service account token
        res = requests.post(url=token_url,
                            data=data,
                            headers={"content-type": "application/x-www-form-urlencoded"},
                            auth=(client_id, client_secret),
                            timeout=cls.timeout)

        try:
            return res.json().get("access_token")
        except Exception:
            return None

    @classmethod
    def create_affiliation(cls, account: int, # noqa: PLR0913
                           business_registration: str,
                           business_name: Optional[str] = None,
                           corp_type_code: str = "TMP",
                           corp_sub_type_code: Optional[str] = None,
                           pass_code: str = "",
                           details: Optional[dict] = None,
                           flags: Optional[any] = None):
        """Affiliate a business to an account."""
        current_app.logger.info(f"Creating affiliation of {business_registration} for {account}")
        auth_url = current_app.config.get("AUTH_SVC_URL")
        account_svc_entity_url = f"{auth_url}/entities"
        account_svc_affiliate_url = f"{auth_url}/orgs/{account}/affiliations"

        token = cls.get_bearer_token()

        if not token:
            current_app.logger.info("Missing token for affiliation call")
            return HTTPStatus.UNAUTHORIZED

        # Create an entity record
        entity_data = {
            "businessIdentifier": business_registration,
            "corpTypeCode": corp_type_code,
            "name": business_name or business_registration
        }
        if corp_sub_type_code:
            entity_data["corpSubTypeCode"] = corp_sub_type_code

        entity_record = requests.post(
            url=account_svc_entity_url,
            headers={**cls.CONTENT_TYPE_JSON,
                     "Authorization": cls.BEARER + token},
            data=json.dumps(entity_data),
            timeout=cls.timeout
        )

        # Create an account:business affiliation
        # headers with conditional sandbox override
        headers = {**cls.CONTENT_TYPE_JSON, "Authorization": cls.BEARER + token}
        if flags and isinstance(flags, Flags) and flags.is_on("enable-sandbox"):
            current_app.logger.info("Appending Environment-Override = sandbox header to create affiliation call")
            headers["Environment-Override"] = "sandbox"

        affiliate_data = {
            "businessIdentifier": business_registration,
            "passCode": pass_code
        }
        if details:
            affiliate_data["entityDetails"] = details
        affiliate = requests.post(
            url=account_svc_affiliate_url,
            headers=headers,
            data=json.dumps(affiliate_data),
            timeout=cls.timeout
        )

        # @TODO delete affiliation and entity record next sprint when affiliation service is updated
        if affiliate.status_code != HTTPStatus.CREATED or entity_record.status_code != HTTPStatus.CREATED:
            return HTTPStatus.BAD_REQUEST
        return HTTPStatus.OK

    @classmethod
    def update_entity(cls,
                      business_registration: str,
                      business_name: str,
                      corp_type_code: str,
                      state: Optional[str] = None):
        """Update an entity."""
        auth_url = current_app.config.get("AUTH_SVC_URL")
        account_svc_entity_url = f"{auth_url}/entities"

        token = cls.get_bearer_token()

        if not token:
            return HTTPStatus.UNAUTHORIZED

        # Create an entity record
        entity_data = {
            "businessIdentifier": business_registration,
            "corpTypeCode": corp_type_code,
            "name": business_name
        }
        if state:
            entity_data["state"] = state

        entity_record = requests.patch(
            url=account_svc_entity_url + "/" + business_registration,
            headers={**cls.CONTENT_TYPE_JSON,
                     "Authorization": cls.BEARER + token},
            data=json.dumps(entity_data),
            timeout=cls.timeout
        )

        if entity_record.status_code != HTTPStatus.OK:
            return HTTPStatus.BAD_REQUEST
        return HTTPStatus.OK

    @classmethod
    def delete_affiliation(cls, account: int, business_registration: str) -> dict:
        """Affiliate a business to an account.

        @TODO Update this when account affiliation is changed next sprint.
        """
        current_app.logger.info(f"Deleting affiliation of {business_registration} for {account}")
        auth_url = current_app.config.get("AUTH_SVC_URL")
        account_svc_entity_url = f"{auth_url}/entities"
        account_svc_affiliate_url = f"{auth_url}/orgs/{account}/affiliations"

        token = cls.get_bearer_token()

        # Delete an account:business affiliation
        affiliate = requests.delete(
            url=account_svc_affiliate_url + "/" + business_registration,
            headers={**cls.CONTENT_TYPE_JSON,
                     "Authorization": cls.BEARER + token},
            timeout=cls.timeout
        )
        # Delete an entity record
        entity_record = requests.delete(
            url=account_svc_entity_url + "/" + business_registration,
            headers={**cls.CONTENT_TYPE_JSON,
                     "Authorization": cls.BEARER + token},
            timeout=cls.timeout
        )

        if affiliate.status_code != HTTPStatus.OK \
                or entity_record.status_code not in (HTTPStatus.OK, HTTPStatus.NO_CONTENT):
            return HTTPStatus.BAD_REQUEST
        return HTTPStatus.OK

    @classmethod
    def get_account_by_affiliated_identifier(cls, identifier: str):
        """Return the account affiliated to the business."""
        token = cls.get_bearer_token()
        auth_url = current_app.config.get("AUTH_SVC_URL")
        url = f"{auth_url}/orgs?affiliation={identifier}"

        # headers with conditional sandbox override
        headers = {**cls.CONTENT_TYPE_JSON, "Authorization": cls.BEARER + token}
        if flags and isinstance(flags, Flags) and flags.is_on("enable-sandbox"):
            current_app.logger.info("Appending Environment-Override = sandbox header to get account affiliation info")
            headers["Environment-Override"] = "sandbox"
        res = requests.get(url=url, headers=headers)
        try:
            return res.json()
        except Exception:
            current_app.logger.error("Failed to get response")
            return None

    @classmethod
    def get_affiliations(cls, account: int):
        """Affiliate a business to an account."""
        auth_url = current_app.config.get("AUTH_SVC_URL")
        account_svc_affiliate_url = f"{auth_url}/orgs/{account}/affiliations"

        token = cls.get_bearer_token()

        if not token:
            current_app.logger.error("Not Authorized")
            return None

        affiliates = requests.get(
            url=account_svc_affiliate_url,
            headers={**cls.CONTENT_TYPE_JSON,
                     "Authorization": cls.BEARER + token},
            timeout=cls.timeout
        )

        if affiliates.status_code == HTTPStatus.OK:
            return affiliates.json().get("entities")

        return None
    
    @classmethod
    def get_contacts(cls, config, org_id: str, user_token: Optional[str] = None):
        """Get contacts for the business.
        Fetch Completing Party Details from Auth API.
        - GET /orgs/{org_id}/memeberships for user contacts details
        - GET /orgs/{org_id} for org contacts details
        """
        token = cls.get_bearer_token()
        auth_url = current_app.config.get("AUTH_SVC_URL")


        if user_token:
            token = user_token
        elif has_request_context():
            try:
                token = jwt.get_token_auth_header()
            except Exception:
                token = cls.get_bearer_token()

        else:
            token = cls.get_bearer_token()

        membership_response = requests.get(
            url=f"{auth_url}/users/orgs/{org_id}/membership",
            headers={**cls.CONTENT_TYPE_JSON,
                     "Authorization": cls.BEARER + token},
            timeout=cls.timeout
        )

        org_info_response = requests.get(
            url=f"{auth_url}/orgs/{org_id}",
            headers={**cls.CONTENT_TYPE_JSON,
                     "Authorization": cls.BEARER + token},
            timeout=cls.timeout
        )

        if membership_response.status_code != HTTPStatus.OK or org_info_response.status_code != HTTPStatus.OK:
            return None
        
        try:
            membership_data = membership_response.json()
            org_info = org_info_response.json()

            user_info = membership_data.get("user", {})
            first_name = user_info.get("firstname", "")
            last_name = user_info.get("lastname", "")

            user_contacts = user_info.get("contacts", [])
            user_contact = user_contacts[0] if user_contacts else {}
            email = user_contact.get("email", "")
            phone = user_contact.get("phone", "")

            org_contacts = org_info.get("contacts", [])
            org_contact = org_contacts[0] if org_contacts else {}

            contact = {
                "street": org_contact.get("street", ""),
                "city": org_contact.get("city", ""),
                "region": org_contact.get("region", ""),
                "country": org_contact.get("country", ""),
                "postalCode": org_contact.get("postalCode", ""),
                "firstName": first_name,
                "lastName": last_name,
                "email": email,
                "phone": phone,
                "streetAdditional": org_contact.get("streetAdditional", ""),
                "delieveryInstructions": org_contact.get("deliveryInstructions", "")
            }
            return {"contacts": [contact]}
        except Exception as e:
            current_app.logger.error(f"Error fetching contacts: {e}")
        return None