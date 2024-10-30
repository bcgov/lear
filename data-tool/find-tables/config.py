"""All of the configuration for the service is captured here."""
import os
from dotenv import find_dotenv, load_dotenv

# Load all the envars from a .env file located in the project root
load_dotenv(find_dotenv())

class Config():
    """Base configuration class"""
    # Colin connection
    ORACLE_USER = os.getenv('ORACLE_USER', '')
    ORACLE_PASSWORD = os.getenv('ORACLE_PASSWORD', '')
    ORACLE_DB_NAME = os.getenv('ORACLE_DB_NAME', '')
    ORACLE_HOST = os.getenv('ORACLE_HOST', '')
    ORACLE_PORT = os.getenv('ORACLE_PORT', '')
    ORACLE_INSTANT_CLIENT_DIR = os.getenv('ORACLE_INSTANT_CLIENT_DIR', '')

    # Mapping configs
    FILING_TYP_CD = os.getenv('FILING_TYP_CD', 'NOALU')
    MAX_FILINGS = int(os.getenv('MAX_FILINGS', 100))
    VERBOSE = int(os.getenv('VERBOSE', 0))
    MAX_MAPPING_DEPTH = int(os.getenv('MAX_MAPPING_DEPTH', 1))
