# Traction Connection Message Sender

This is a generic script that will call a Traction instance with a supplied Tenant ID/API Key to send basic messages to supplied connections. It simply loops connection IDs from a supplied script, so take into account batching (could just run multiple times with different input lists) if numbers get high.

The python script will

- Read in a `connections.txt` list of connection IDs (one per line, no headers or delimiters)
- Get a Traction token
- Call the message endpoint looping per connection ID with a configured message
- Track each call and write them out at the end to an `audit.csv` file

Inputs and configuration could be passed in but can just be edited in the script.

## Requirements

- Python 3.7+
- `requests` library

Install dependencies:

```bash
pip install -r requirements.txt
```

A [Traction API key](https://github.com/bcgov/traction/blob/main/docs/USE-CASE-API-KEY.md) for the environment and Tenant you have control over

## Configuration

Update these constants at the top of the script to match your environment:

| Constant          | Description                                                                                                   |
| ----------------- | ------------------------------------------------------------------------------------------------------------- |
| `TENANT_ID`       | Your Traction tenant ID.                                                                                      |
| `API_KEY`         | API key for your Tenant.                                                                                      |
| `TRACTION_URL`    | Base URL for the Traction proxy API (e.g., `https://traction-tenant-proxy-dev.apps.silver.devops.gov.bc.ca`). |
| `TOKEN_URL`       | Automatically constructed from `TRACTION_URL` and `TENANT_ID`. Endpoint for retrieving the bearer token.      |
| `MESSAGE_URL`     | Endpoint for sending messages to a specific connection ID. Uses `TRACTION_URL` and the connection ID.         |
| `MESSAGE_CONTENT` | The message text that will be sent to each connection.                                                        |
| `ID_FILE`         | Path to the input file containing connection IDs (one per line). Default: `connections.txt`.                  |
| `AUDIT_FILE`      | Path to the output CSV file that logs message results. Default: `audit.csv`.                                  |

## Run

Ensure requirements are installed with pip, check configuration in the file.

Execute:

```bash
python message-sender.py
```

Will log out to console, at the end an audit file specified by `AUDIT_FILE` will be created.

## Pre-check for connections
Can run the `connection-check.py` script in the same manner with the same credentials and connections file as a check first to discover if any connection GUIDs cannot be found.