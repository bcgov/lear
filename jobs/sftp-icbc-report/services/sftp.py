# Copyright © 2019 Province of British Columbia
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
"""This module is a wrapper for SFTP Connection object."""
import os
import paramiko
import logging
from base64 import decodebytes
from pysftp import Connection, CnOpts


class SFTPService:  # pylint: disable=too-few-public-methods
    """SFTP  Service class."""

    @staticmethod
    def get_connection() -> Connection:
        # pylint: disable=protected-access
        return SFTPService._connect()

    @staticmethod
    def _connect() -> Connection:

        sftp_host = os.getenv('SFTP_HOST', 'localhost')
        sftp_port = os.getenv('SFTP_PORT', 22)
        logging.info('Start _connect sftp_host: %s', sftp_host)

        cnopts = CnOpts()
        # only for local development set this to false .
        if os.getenv('SFTP_VERIFY_HOST').lower() == 'false':
            cnopts.hostkeys = None
        else:
            ftp_host_key_data = os.getenv('SFTP_HOST_KEY', '').encode()
            key = paramiko.RSAKey(data=decodebytes(ftp_host_key_data))
            cnopts.hostkeys.add(sftp_host, 'ssh-rsa', key)

        sftp_priv_key_file = os.path.join(os.getcwd(), r'data/') + 'sftp_priv_key_file'

        # only create key file if it doesn't exist
        if not os.path.isfile(sftp_priv_key_file):
            with open(sftp_priv_key_file, 'w+') as fh:
                sftp_priv_key = os.getenv('BCREG_FTP_PRIVATE_KEY', '')
                fh.write(sftp_priv_key)

        sft_credentials = {
            'username': os.getenv('SFTP_USERNAME', 'foo'),
            # private_key should be the absolute path to where private key file lies since sftp
            'private_key': sftp_priv_key_file,
            'private_key_pass': os.getenv('BCREG_FTP_PRIVATE_KEY_PASSPHRASE', '')
        }

        sftp_connection = Connection(host=sftp_host, **sft_credentials, cnopts=cnopts, port=int(sftp_port))

        logging.info('sftp_connection successful')

        return sftp_connection
