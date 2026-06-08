
import subprocess
import os

def connect_to_db():
    print("Generating fresh GCP IAM token...")
    try:
        token = subprocess.check_output(
            ["gcloud", "sql", "generate-login-token"], 
            text=True
        ).strip()
    except subprocess.CalledProcessError as e:
        print("Error: Make sure you are authenticated with 'gcloud auth login'")
        return

    os.environ["GCP_IAM_TOKEN"] = token

    print("Connecting to test_dev via DbSchemaCLI...")

if __name__ == "__main__":
    connect_to_db()
