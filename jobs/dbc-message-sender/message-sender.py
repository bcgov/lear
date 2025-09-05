import requests
import csv
import time
import logging
from datetime import datetime
from pathlib import Path

# Configuration
TENANT_ID = "TENANT ID HERE"
API_KEY = "API KEY HERE"
TRACTION_URL = "TRACTION ENV HERE"
TOKEN_URL = f"{TRACTION_URL}/multitenancy/tenant/{TENANT_ID}/token"
MESSAGE_URL = f"{TRACTION_URL}/connections/{{id}}/send-message"
MESSAGE_CONTENT = "Hello, your message content here"
ID_FILE = "connections.txt"
AUDIT_FILE = "audit.csv"

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("message_sender.log"), logging.StreamHandler()],
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


# Send message to a specific connection ID
def send_message(id, token):
    url = MESSAGE_URL.format(id=id)
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    payload = {"content": MESSAGE_CONTENT}
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return {"status": "PASS", "error": "None"}
    except Exception as e:
        return {"status": "FAIL", "error": str(e)}


# Read connection IDs from input file
def read_ids(file_path):
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Input file not found: {file_path}")
    with open(file_path) as f:
        return [line.strip() for line in f if line.strip()]


# Write audit results to CSV file
def write_audit_log(rows, file_path):
    with open(file_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["id", "timestamp", "status", "message", "error"]
        )
        writer.writeheader()
        writer.writerows(rows)


# Main execution flow
def main():
    # Generate timestamped audit file name if desired
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audit_file = f"audit_{timestamp}.csv"

    # Check if audit file already exists
    if Path(audit_file).exists():
        logging.warning(
            f"Audit file '{audit_file}' already exists. Aborting to prevent overwrite."
        )
        return

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

    audit_rows = []
    success_count = 0
    fail_count = 0

    for id in ids:
        result = send_message(id, token)
        status = result["status"]
        if status == "PASS":
            success_count += 1
        else:
            fail_count += 1

        logging.info(f"Sent message to ID {id}: {status}")
        audit_rows.append(
            {
                "id": id,
                "timestamp": datetime.now().isoformat(),
                "status": status,
                "message": MESSAGE_CONTENT,
                "error": result["error"],
            }
        )
        time.sleep(0.05)

    write_audit_log(audit_rows, audit_file)
    logging.info(f"DONE. Success: {success_count}, Failures: {fail_count}")
    logging.info(f"Audit log written to {audit_file}")


if __name__ == "__main__":
    main()
