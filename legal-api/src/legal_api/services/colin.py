# Copyright © 2024 Province of British Columbia
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

"""This provides the service for colin-api calls."""
from http import HTTPStatus

from flask import current_app
from requests import Response, Session, exceptions
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from business_account import AccountService
from legal_api.services.cache import cache


def get_colin_cache_key(path: str, token: str | None = None, use_cache = True) -> str:
    """Return the cache key for a colin call."""
    return f"colin-{path}-{token}"


def skip_colin_cache(func, path, token: str | None = None, use_cache = True) -> bool:
    """Bypass the cache entirely (no read, no write) when the caller opts out."""
    return not use_cache


def is_cacheable_response(result: tuple) -> bool:
    """Cache only definitive answers - never a failed call, a COLIN 5xx or an OK with no JSON body."""
    json_data, status_code = result
    if status_code is None or status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
        return False
    return not (status_code == HTTPStatus.OK and json_data is None)


def safe_json(response: Response | None) -> dict | None:
    """Return the response body as json, or None when there is no valid JSON body."""
    if response is None:
        return None
    try:
        return response.json()
    except ValueError:
        return None


class ColinService:
    """Provides services to use the colin-api."""

    @staticmethod
    @cache.cached(make_cache_key=get_colin_cache_key, unless=skip_colin_cache, response_filter=is_cacheable_response)
    def call_colin_api(path: str, token: str | None = None, use_cache = True) -> tuple[dict | None, int | None]:
        """Return (json body, status code) of the colin api response for the given endpoint path.

        Returns (None, None) when the call could not be made or colin was unreachable.
        """
        current_app.logger.debug(f"Colin get {path}...")
        timeout = current_app.config.get("COLIN_TIMEOUT", 20)
        template_url = current_app.config.get("COLIN_URL")
        if not template_url:
            current_app.logger.error(f"Colin call to {path} failed: COLIN_URL is not configured")
            return None, None
        colin_url = template_url + "/" if template_url[-1] != "/" else template_url
        colin_url += path

        try:
            token = token or AccountService.get_bearer_token()
            if not token:
                current_app.logger.error(f"Colin call to {path} failed: no service token")
                return None, None

            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token
            }
            http = Session()
            retries = Retry(total=5,
                            backoff_factor=0.1,
                            status_forcelist=[500, 502, 503, 504])
            http.mount("http://", HTTPAdapter(max_retries=retries))
            http.mount("https://", HTTPAdapter(max_retries=retries))
            resp = http.get(url=colin_url, headers=headers, timeout=timeout)
            current_app.logger.debug(f"Colin get {path} response status: {resp.status_code!s}")
            if not resp.ok and resp.status_code != HTTPStatus.NOT_FOUND:
                current_app.logger.error("%s call failed with status %s", path, resp.status_code)
            return safe_json(resp), resp.status_code

        except (exceptions.ConnectionError,
                exceptions.Timeout,
                Exception) as err:
            current_app.logger.debug(err.with_traceback(None))
            current_app.logger.error(f"Colin connection failure, url: {colin_url}")
            return None, None

    @staticmethod
    def query_business(identifier: str, use_cache: bool = True) -> tuple[dict | None, int | None]:
        """Return (json, status code) of the business information."""
        return ColinService.call_colin_api(f"businesses/{identifier}/public", use_cache=use_cache)

    @staticmethod
    def get_snapshot(identifier: str, use_cache: bool = True) -> tuple[dict | None, int | None]:
        """Return (json, status code) of the LEAR-shaped snapshot of a COLIN business."""
        return ColinService.call_colin_api(f"businesses/{identifier}/snapshot", use_cache=use_cache)
