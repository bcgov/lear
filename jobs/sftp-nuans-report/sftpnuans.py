"""The Notebook Report - This module is the API for the Filings Notebook Report."""

import fnmatch
import logging
import os
import shutil
import smtplib
import sys
import traceback
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import papermill as pm
from flask import Flask, current_app

from config import Config
from tasks.ftp_processor import FtpProcessor
from util.logging import setup_logging

setup_logging(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'logging.conf'))  # important to do this first

# Notebook Scheduler
# ---------------------------------------
# This script helps with the automated processing of Jupyter Notebooks via
# papermill (https://github.com/nteract/papermill/)


def create_app(config=Config):
    """Create app."""
    app = Flask(__name__)
    app.config.from_object(config)
    # db.init_app(app)
    app.app_context().push()
    current_app.logger.debug('created the Flask App and pushed the App Context')

    return app


def findfiles(directory, pattern):
    """Find files matched."""
    for filename in os.listdir(directory):
        if fnmatch.fnmatch(filename.lower(), pattern):
            yield os.path.join(directory, filename)


def send_email(note_book, errormessage):
    """Send email for results."""
    message = MIMEMultipart()
    date = datetime.strftime(datetime.now(), '%Y%m%d')

    ext = ''
    if not os.getenv('ENVIRONMENT', '') == 'prod':
        ext = ' on ' + os.getenv('ENVIRONMENT', '')

    subject = "SFTP NUANS Error Notification from LEAR for processing '" \
        + note_book + "' on " + date + ext
    recipients = os.getenv('ERROR_EMAIL_RECIPIENTS', '')
    message.attach(MIMEText('ERROR!!! \n' + errormessage, 'plain'))

    message['Subject'] = subject
    server = smtplib.SMTP(os.getenv('EMAIL_SMTP', ''))
    email_list = recipients.strip('][').split(', ')
    logging.info('Email recipients list is: %s', email_list)
    server.sendmail(os.getenv('SENDER_EMAIL', ''), email_list, message.as_string())
    logging.info("Email with subject \'%s\' has been sent successfully!", subject)
    server.quit()


def processnotebooks(notebookdirectory, data_dir):
    """Process data."""
    status = False

    logging.info('Start processing directory: %s', notebookdirectory)

    try:
        pm.execute_notebook(os.path.join(notebookdirectory, 'generate_files.ipynb'),
                            data_dir + 'temp.ipynb', parameters=None)
        os.remove(data_dir+'temp.ipynb')

        FtpProcessor.process_ftp(data_dir)

        status = True
    except Exception:  # noqa: B902
        logging.exception('Error processing notebook %s.', notebookdirectory)
        send_email(notebookdirectory, traceback.format_exc())
    return status


if __name__ == '__main__':
    start_time = datetime.utcnow()

    temp_dir = os.path.join(os.getcwd(), r'data/')
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    processnotebooks('notebook', temp_dir)
    # shutil.rmtree(temp_dir)

    end_time = datetime.utcnow()
    logging.info('job - jupyter notebook report completed in: %s', end_time - start_time)
    sys.exit()
