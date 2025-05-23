"""The Notebook Report - This module is the API for the Filings Notebook Report."""

import ast
import base64
import fnmatch
import os
import shutil
import sys
import time
import traceback
import warnings
from datetime import UTC, datetime, timedelta

import papermill as pm
import requests
from business_account.AccountService import AccountService
from dateutil.relativedelta import relativedelta
from dotenv import find_dotenv, load_dotenv
from flask import Flask

from structured_logging import StructuredLogging

try:
    from config.config import Config
except ImportError:
    from notebookreport.config.config import Config

# this will load all the envars from a .env file located in the project root (api)
load_dotenv(find_dotenv())

HTTP_OK = 200

logging = StructuredLogging().get_logger()

def findfiles(directory, pattern):
    """Find files matched."""
    for filename in os.listdir(directory):
        if fnmatch.fnmatch(filename.lower(), pattern):
            yield os.path.join(directory, filename)


def send_email(note_book, data_directory, emailtype, errormessage):  # noqa: PLR0915
    """Send email for results."""
    email = {
      "content": {}
    }
    date = datetime.strftime(datetime.now() - timedelta(1), "%Y-%m-%d")
    last_month = datetime.now() - relativedelta(months=1)
    ext = ""
    filename = ""
    env = os.getenv("DEPLOYMENT_ENV", "dev")
    if env != "prod":
        ext = " on " + env

    if emailtype == "ERROR":
        subject = "Jupyter Notebook Error Notification from LEAR for processing '" \
            + note_book + "' on " + date + ext
        recipients = os.getenv("ERROR_EMAIL_RECIPIENTS", "")
        email["content"]["body"] = "ERROR!!! \n" + errormessage
    else:
        file_processing = note_book.split(".ipynb")[0]

        if file_processing == "incorpfilings":
            subject = "Incorporation Filings Daily Stats " + date + ext
            filename = "incorporation_filings_daily_stats_" + date + ".csv"
            recipients = os.getenv("INCORPORATION_FILINGS_DAILY_REPORT_RECIPIENTS", "")
        elif file_processing == "coopfilings":
            subject = "COOP Filings Monthly Stats for " + format(last_month, "%B %Y") + ext
            filename = "coop_filings_monthly_stats_for_" + format(last_month, "%B_%Y") + ".csv"
            recipients = os.getenv("COOP_FILINGS_MONTHLY_REPORT_RECIPIENTS", "")
        elif file_processing == "cooperative":
            subject = "Cooperative Monthly Stats for " + format(last_month, "%B %Y") + ext
            filename = "cooperative_monthly_stats_for_" + format(last_month, "%B_%Y") + ".csv"
            recipients = os.getenv("COOPERATIVE_MONTHLY_REPORT_RECIPIENTS", "")
        elif file_processing == "firm-registration-filings":
            subject = "BC STATS FIRMS for " + format(last_month, "%B %Y") + ext
            filename = "bc_stats_firms_for_" + format(last_month, "%B_%Y") + ".csv"
            recipients = os.getenv("BC_STATS_MONTHLY_REPORT_RECIPIENTS", "")

        # Add body to email
        email["content"]["body"] = "Please see the attachment(s)."

        # Open file in binary mode
        with open(data_directory+filename, "rb") as attachment:
            part = base64.b64encode(attachment.read())

        # Add attachment to message and convert message to string
        email["content"]["attachments"] = [{
                "fileName": filename,
                "fileBytes": part,
                "fileUrl": "",
                "attachOrder": str(1)
        }]

    email["content"]["subject"] = subject
    email_list = recipients.strip("][")
    logging.info("Email recipients list is: %s", email_list)
    email["recipients"] = email_list
    email["requestBy"] = os.getenv("SENDER_EMAIL", "")
    notify_api= os.getenv("NOTIFY_API_URL", "")
    notify_version = os.getenv("NOTIFY_API_VERSION", "")
    notify_url = notify_api + notify_version + "/notify"
    token = AccountService.get_bearer_token()
    errored = False
    try:
        resp = requests.post(
            f"{notify_url}",
            json=email,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }
        )
        if resp.status_code != HTTP_OK:
            errored = True
            logging.error("Email %s error %s", subject, resp.text)
    except Exception:
        logging.exception("Error sending email for %s", subject)
        errored = True

    if errored:
        logging.exception("Email with subject %s has failed to send!", subject)
    else:
        logging.info("Email with subject %s has been sent successfully!", subject)
        if filename != "":
            os.remove(os.path.join(os.getcwd(), r"data/")+filename)


def processnotebooks(notebookdirectory, data_directory):
    """Process Notebook."""
    status = False
    now = datetime.now()
    warnings.filterwarnings("ignore", category=DeprecationWarning)

    try:
        retry_times = int(os.getenv("RETRY_TIMES", "1"))
        retry_interval = int(os.getenv("RETRY_INTERVAL", "60"))
        if notebookdirectory == "monthly":
            days = ast.literal_eval(os.getenv("MONTH_REPORT_DATES", ""))
    except Exception:
        logging.exception("Error processing notebook for %s", notebookdirectory)
        send_email(notebookdirectory, data_directory, "ERROR", traceback.format_exc())
        return status

    # For monthly tasks, we only run on the specified days
    if notebookdirectory == "daily" or (notebookdirectory == "monthly" and now.day in days):
        notebookdirectory = os.path.join(os.path.dirname(__file__), notebookdirectory)
        logging.info("Processing: %s", notebookdirectory)

        num_files = len(os.listdir(notebookdirectory))
        file_processed = 0

        for file in findfiles(notebookdirectory, "*.ipynb"):
            file_processed += 1
            note_book = os.path.basename(file)
            for attempt in range(retry_times):
                try:
                    pm.execute_notebook(file, data_directory+"temp.ipynb", parameters=None)
                    send_email(note_book, data_directory, "", "")
                    os.remove(data_directory+"temp.ipynb")
                    status = True
                    break
                except Exception:
                    if attempt + 1 == retry_times:
                        # If any errors occur with the notebook processing they will be logged to the log file
                        logging.exception(
                            "Error processing notebook %s at %s/%s try.", notebookdirectory, attempt + 1,
                            retry_times)
                        send_email(notebookdirectory, data_directory, "ERROR", traceback.format_exc())
                    else:
                        # If any errors occur with the notebook processing they will be logged to the log file
                        logging.exception("Error processing notebook %s at %s/%s try. "
                                          "Sleeping for %s secs before next try", notebookdirectory, attempt + 1,
                                          retry_times, retry_interval)
                        time.sleep(retry_interval)
                        continue
            if not status and num_files == file_processed:
                break
    return status

def create_app():
    app = Flask(__name__)
    app.app_context().push()
    app.logger = StructuredLogging(app).get_logger()
    app.config.from_object(Config)
    return app

if __name__ == "__main__":
    start_time = datetime.now(UTC)
    app = create_app()
    data_dir = os.path.join(os.getcwd(), r"data/")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    # Check if the subfolders for notebooks exist, and create them if they don't
    for subdir in ["daily", "monthly"]:
        if not os.path.isdir(subdir):
            os.mkdir(subdir)

        processnotebooks(subdir, data_dir)

    shutil.rmtree(data_dir)
    end_time = datetime.now(UTC)
    logging.info("job - jupyter notebook report completed in: %s", end_time - start_time)
    sys.exit()