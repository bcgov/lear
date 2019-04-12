import os

import pytest
from dotenv import load_dotenv, find_dotenv

#this will load all the envars from a .env file located in the project root (api)
load_dotenv(find_dotenv())


oracle_integration = pytest.mark.skipif((os.getenv('ORACLE_INTEGRATION_TESTING', False) is False),
                                                reason="requires access to a test version of Oracle CTST")
