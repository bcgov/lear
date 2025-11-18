# Copyright © 2021 Province of British Columbia
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
"""This module is a wrapper for Minio."""

import uuid
from datetime import timedelta

from flask import current_app
from minio import Minio


class MinioService:
    """Document Storage class."""

    @staticmethod
    def create_signed_put_url(file_name: str) -> dict:
        """Return a pre-signed URL for new doc upload."""
        current_app.logger.debug(f"Creating pre-signed URL for {file_name}")
        minio_client: Minio = MinioService._get_client()
        file_extension: str = file_name.split(".")[-1]
        key = f"{str(uuid.uuid4())}.{file_extension}"
        bucket = current_app.config["MINIO_BUCKET_BUSINESSES"]
        signed_url_details = {
            "preSignedUrl": minio_client.presigned_put_object(bucket, key, timedelta(minutes=5)),
            "key": key,
        }

        return signed_url_details

    @staticmethod
    def create_signed_get_url(key: str) -> str:
        """Return a pre-signed URL for uploaded document."""
        minio_client: Minio = MinioService._get_client()
        current_app.logger.debug(f"Creating pre-signed GET URL for {key}")
        bucket = current_app.config["MINIO_BUCKET_BUSINESSES"]

        return minio_client.presigned_get_object(bucket, key, timedelta(hours=1))

    @staticmethod
    def get_file_info(key: str):
        """Fetch file info from Minio."""
        minio_client: Minio = MinioService._get_client()
        bucket = current_app.config["MINIO_BUCKET_BUSINESSES"]
        return minio_client.stat_object(bucket, key)

    @staticmethod
    def get_file(key: str):
        """
        Fetch file from Minio.

        Example::
            try:
                response = minio.get_file(key)
                :- `Read data from response.`
            finally:
                response.close()
                response.release_conn()
        """
        minio_client: Minio = MinioService._get_client()
        bucket = current_app.config["MINIO_BUCKET_BUSINESSES"]
        return minio_client.get_object(bucket, key)

    @staticmethod
    def delete_file(key: str):
        """Delete file from Minio."""
        minio_client: Minio = MinioService._get_client()
        bucket = current_app.config["MINIO_BUCKET_BUSINESSES"]
        minio_client.remove_object(bucket, key)

    @staticmethod
    def _get_client() -> Minio:
        """Return a minio client."""
        minio_endpoint = current_app.config["MINIO_ENDPOINT"]
        minio_key = current_app.config["MINIO_ACCESS_KEY"]
        minio_secret = current_app.config["MINIO_ACCESS_SECRET"]
        minio_secure = current_app.config["MINIO_SECURE"]
        return Minio(minio_endpoint, access_key=minio_key, secret_key=minio_secret, secure=minio_secure)

    @staticmethod
    def put_file(key: str, data: str, length: str):
        """Put file to Minio."""
        minio_client: Minio = MinioService._get_client()
        bucket = current_app.config["MINIO_BUCKET_BUSINESSES"]
        minio_client.put_object(bucket, key, data, length)
