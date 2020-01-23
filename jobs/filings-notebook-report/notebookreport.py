import os
import sys
import ast
import time
import smtplib
import email
import traceback
import argparse
import fnmatch
import logging
import papermill as pm
import shutil
from datetime import datetime, timedelta
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import Flask, g, current_app
from config import Config
from legal_api.utils.logging import setup_logging
from legal_api.models import db

setup_logging(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'logging.conf'))  # important to do this first

# Notebook Scheduler
# ---------------------------------------
# This script helps with the automated processing of Jupyter Notebooks via
# papermill (https://github.com/nteract/papermill/)

snapshotDir = 'snapshots'


def create_app(config=Config):
    app = Flask(__name__)
    app.config.from_object(config)
    db.init_app(app)
    app.app_context().push()
    current_app.logger.debug('created the Flask App and pushed the App Context')

    return app


def findfiles(directory, pattern):
    # Lists all files in the specified directory that match the specified pattern
    for filename in os.listdir(directory):
        if fnmatch.fnmatch(filename.lower(), pattern):
            yield os.path.join(directory, filename)


def send_email(subject, filename, emailtype, errormessage):
    message = MIMEMultipart()
    message["Subject"] = subject
    sender_email = os.getenv('SENDER_EMAIL', '')

    if emailtype == "ERROR":
        recipients = os.getenv('ERROR_EMAIL_RECIPIENTS', '')
        message.attach(MIMEText("ERROR!!! \n" + errormessage, "plain"))
    else:
        recipients = os.getenv('REPORT_RECIPIENTS', '')
        # Add body to email
        message.attach(MIMEText("Please see attached.", "plain"))

        # Open file in binary mode
        with open(filename, "rb") as attachment:
            # Add file as application/octet-stream
            # Email client can usually download this automatically as attachment
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())

        # Encode file in ASCII characters to send by email
        encoders.encode_base64(part)

        # Add header as key/value pair to attachment part
        part.add_header(
            "Content-Disposition",
            f"attachment; filename= {filename}",
        )

        # Add attachment to message and convert message to string
        message.attach(part)

    server = smtplib.SMTP(os.getenv('EMAIL_SMTP', ''))
    email_list = []
    email_list = recipients.strip('][').split(', ')
    logging.info('Email recipients list is: {}'.format(email_list))
    server.sendmail(sender_email, email_list, message.as_string())
    logging.info('Email with subject \'' + subject + '\' has been sent successfully!')
    server.quit()


def processnotebooks(notebookdirectory, days=[], months=[]):
    status = False
    now = datetime.now()
    date = datetime.strftime(datetime.now() - timedelta(1), '%Y-%m-%d')
    ext = ''
    if not os.getenv('ENVIRONMENT', '') == 'prod':
        ext = ' on ' + os.getenv('ENVIRONMENT', '')

    try:
        retry_times = int(os.getenv('RETRY_TIMES', '1'))
        retry_interval = int(os.getenv('RETRY_INTERVAL', '60'))

        if len(days) == 0:
            days = ast.literal_eval(os.getenv('REPORT_DATES', ''))
    except Exception:
        logging.exception("Error processing notebook for {}.".format(notebookdirectory))
        # we failed all the attempts
        subject = "Filings Jupyter Notebook Error Notification for " + notebookdirectory + " on " + date + ext
        filename = ''
        send_email(subject, filename, "ERROR", traceback.format_exc())
        return status

    if len(months) == 0 and len(days) > 0 and now.day in days:

        logging.info('Processing: ' + notebookdirectory)

        # Each time a notebook is processed a snapshot is saved to a snapshot sub-directory
        # This checks the sub-directory exists and creates it if not
        if not os.path.isdir(os.path.join(notebookdirectory, snapshotDir)):
            os.mkdir(os.path.join(notebookdirectory, snapshotDir))

        for file in findfiles(notebookdirectory, '*.ipynb'):
            for attempt in range(retry_times):
                try:
                    nb = os.path.basename(file)

                    # Within the snapshot directory, each notebook output is stored in its own sub-directory
                    notebooksnapshot = os.path.join(notebookdirectory, snapshotDir, nb.split('.ipynb')[0])

                    if not os.path.isdir(notebooksnapshot):
                        os.mkdir(notebooksnapshot)

                    # The output will be saved in a timestamp directory (snapshots/notebook/timestamp)
                    rundir = os.path.join(notebooksnapshot, now.strftime("%Y-%m-%d %H.%M.%S.%f"))
                    if not os.path.isdir(rundir):
                        os.mkdir(rundir)

                    # The snapshot file includes a timestamp
                    output_file = os.path.join(rundir, nb)

                    # Execute the notebook and save the snapshot
                    pm.execute_notebook(
                        file,
                        output_file,
                        parameters=dict(snapshotDir=rundir + os.sep)
                    )

                    if notebookdirectory == 'monthly' or notebookdirectory == '../monthly':
                        subject = "Filings Monthly Stats till " + date + ext
                        filename = 'monthly_total_till_' + date + '.csv'
                    # send email to receivers and remove files/directories which we don't want to keep
                    send_email(subject, filename, "", "")
                    os.remove(filename)
                    shutil.rmtree(os.path.join(notebookdirectory, snapshotDir), ignore_errors=True)
                    status = True
                    break
                except Exception:
                    if attempt + 1 == retry_times:
                        # If any errors occur with the notebook processing they will be logged to the log file
                        logging.exception(
                            "Error processing notebook {0} at {1}/{2} try.".format(notebookdirectory, attempt + 1,
                                                                                   retry_times))
                        # we failed all the attempts
                        subject = "Filings Jupyter Notebook Error Notification for " + notebookdirectory + " on " \
                                  + date + ext
                        filename = ''
                        send_email(subject, filename, "ERROR", traceback.format_exc())
                    else:
                        # If any errors occur with the notebook processing they will be logged to the log file
                        logging.exception("Error processing notebook {0} at {1}/{2} try. "
                                          "Sleeping for {3} secs before next try".format(notebookdirectory, attempt + 1,
                                                                                         retry_times, retry_interval))
                        time.sleep(retry_interval)
                        continue
            if not status:
                break
        return status
    else:
        return True


if __name__ == '__main__':
    start_time = datetime.utcnow()

    # Check if the subfolders for notebooks exist, and create them if they don't
    if not os.path.isdir('monthly'):
        os.mkdir('monthly')

    processnotebooks('monthly')

    end_time = datetime.utcnow()
    logging.info("job - jupyter notebook report completed in: {}".format(end_time - start_time))
    exit(0)
