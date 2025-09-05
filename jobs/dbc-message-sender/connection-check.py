import requests
import logging
from pathlib import Path

# Configuration
TENANT_ID = "TENANT ID HERE"
API_KEY = "API KEY HERE"
TRACTION_URL = "TRACTION ENV HERE"
TOKEN_URL = f"{TRACTION_URL}/multitenancy/tenant/{TENANT_ID}/token"
CONNECTION_URL = f"{TRACTION_URL}/connections/{{id}}"
ID_FILE = "connections.txt"

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)

# Retrieve Traction token
def get_token():
    try:
        response = requests.post(
            TOKEN_URL,
            headers={"accept": "application/json", "Content-Type": "application/json"},
            json={"api_key": API_KEY},
        )
        response.raise_for_status()
        token = response.json().get("token")
        if not token:
            raise ValueError("No token found in response.")
        logging.info("Token retrieved successfully.")
        return token
    except Exception as e:
        logging.error(f"Failed to retrieve token: {e}")
        raise

# Check if connection exists
def check_connection(id, token):
    url = CONNECTION_URL.format(id=id)
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return True
        else:
            return False
    except Exception as e:
        logging.error(f"Error checking connection {id}: {e}")
        return False

# Read connection IDs from input file
def read_ids(file_path):
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Input file not found: {file_path}")
    with open(file_path) as f:
        return [line.strip() for line in f if line.strip()]

# Main execution flow
def main():
    try:
        ids = read_ids(ID_FILE)
        logging.info(f"Loaded {len(ids)} connection IDs from {ID_FILE}")
    except Exception as e:
        logging.error(e)
        return

    try:
        token = get_token()
    except Exception:
        logging.error("Aborting due to token retrieval failure.")
        return

    found_count = 0
    not_found_count = 0

    for idx, id in enumerate(ids, start=1):
        found = check_connection(id, token)
        if found:
            found_count += 1
            logging.info(f"Counter: {idx}. Connection {id}: FOUND")
        else:
            not_found_count += 1
            logging.info(f"Counter: {idx}. Connection {id}: NOT FOUND")

    logging.info(f"SUMMARY: Found: {found_count}, Not Found: {not_found_count}")

if __name__ == "__main__":
    main()
