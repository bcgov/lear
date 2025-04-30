# # Copyright © 2025 Province of British Columbia
# #
# # Licensed under the BSD 3 Clause License, (the "License");
# # you may not use this file except in compliance with the License.
# # The template for the license can be found here
# #    https://opensource.org/license/bsd-3-clause/
# #
# # Redistribution and use in source and binary forms,
# # with or without modification, are permitted provided that the
# # following conditions are met:
# #
# # 1. Redistributions of source code must retain the above copyright notice,
# #    this list of conditions and the following disclaimer.
# #
# # 2. Redistributions in binary form must reproduce the above copyright notice,
# #    this list of conditions and the following disclaimer in the documentation
# #    and/or other materials provided with the distribution.
# #
# # 3. Neither the name of the copyright holder nor the names of its contributors
# #    may be used to endorse or promote products derived from this software
# #    without specific prior written permission.
# #
# # THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
# # AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# # THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# # ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# # LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# # CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# # SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# # INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# # CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# # ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# # POSSIBILITY OF SUCH DAMAGE.
# """decorators used to skip/run pytests based on local setup."""
# import os

# import pytest
# from dotenv import find_dotenv, load_dotenv


# # this will load all the envars from a .env file located in the project root (api)
# load_dotenv(find_dotenv())


# colin_api_integration = pytest.mark.skipif((os.getenv('RUN_COLIN_API', False) is False),
#                                            reason='requires access to COLIN API')

# integration_affiliation = pytest.mark.skipif((os.getenv('RUN_AFFILIATION_TESTS', False) is False),
#                                              reason='Account affiliation tests are only run when requested.')

# integration_namex_api = pytest.mark.skipif((os.getenv('RUN_NAMEX_API', False) is False),
#                                            reason='NameX tests are only run when requested.')

# skip_in_pod = pytest.mark.skipif((os.getenv('POD_TESTING', False) is False), reason='Skip test when running in pod')
