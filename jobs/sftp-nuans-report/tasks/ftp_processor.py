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
import os
import logging
from typing import List
from services.sftp import SFTPService


class FtpProcessor:  # pylint:disable=too-few-public-methods

    @classmethod
    def process_ftp(cls, data_dir):
        with SFTPService.get_connection() as sftp_client:
            try:
                file_list = os.listdir(data_dir)
                logging.info(f'Found {len(file_list)-1} to be copied.')

                for file in file_list:
                    if not file.startswith("sftp_priv_key_file"):
                        file_full_name = data_dir + file
                        sftp_client.put(file_full_name)
                        logging.info('SFTP to NUANS completed for file: %s', file_full_name)

            except Exception as e:  # NOQA # pylint: disable=broad-except
                logging.error(e)
