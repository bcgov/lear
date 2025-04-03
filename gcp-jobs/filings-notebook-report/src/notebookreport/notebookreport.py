"""The Notebook Report - This module is the API for the Filings Notebook Report."""

import ast
import fnmatch
import logging
import os
import smtplib
import sys
import time
import traceback
import warnings
from datetime import datetime, timedelta
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import papermill as pm
from dateutil.relativedelta import relativedelta
from flask import Flask, current_app

from .config import Config
from .util.logging import setup_logging

setup_logging(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'logging.conf'))  # important to do this first

# Notebook Scheduler
# ---------------------------------------
# This script helps with the automated processing of Jupyter Notebooks via
# papermill (https://github.com/nteract/papermill/)


def create_app(config=Config):
    """Create app."""
    app = Flask(__name__)
    app.config.from_object(config)
    app.app_context().push()
    current_app.logger.debug('created the Flask App and pushed the App Context')

    return app


def findfiles(directory, pattern):
    """Find files matched."""
    for filename in os.listdir(directory):
        if fnmatch.fnmatch(filename.lower(), pattern):
            yield os.path.join(directory, filename)


def send_email(note_book, data_directory, emailtype, errormessage):  # pylint: disable-msg=too-many-locals
    """Send email for results."""
    message = MIMEMultipart()
    date = datetime.strftime(datetime.now() - timedelta(1), '%Y-%m-%d')
    last_month = datetime.now() - relativedelta(months=1)
    ext = ''
    filename = ''
    if not os.getenv('ENVIRONMENT', '') == 'prod':
        ext = ' on ' + os.getenv('ENVIRONMENT', '')

    if emailtype == 'ERROR':
        subject = "Jupyter Notebook Error Notification from LEAR for processing '" \
            + note_book + "' on " + date + ext
        recipients = os.getenv('ERROR_EMAIL_RECIPIENTS', '')
        message.attach(MIMEText('ERROR!!! \n' + errormessage, 'plain'))
    else:
        file_processing = note_book.split('.ipynb')[0]

        if file_processing == 'incorpfilings':
            subject = 'Incorporation Filings Daily Stats ' + date + ext
            filename = 'incorporation_filings_daily_stats_' + date + '.csv'
            recipients = os.getenv('INCORPORATION_FILINGS_DAILY_REPORT_RECIPIENTS', '')
        elif file_processing == 'coopfilings':
            subject = 'COOP Filings Monthly Stats for ' + format(last_month, '%B %Y') + ext
            filename = 'coop_filings_monthly_stats_for_' + format(last_month, '%B_%Y') + '.csv'
            recipients = os.getenv('COOP_FILINGS_MONTHLY_REPORT_RECIPIENTS', '')
        elif file_processing == 'cooperative':
            subject = 'Cooperative Monthly Stats for ' + format(last_month, '%B %Y') + ext
            filename = 'cooperative_monthly_stats_for_' + format(last_month, '%B_%Y') + '.csv'
            recipients = os.getenv('COOPERATIVE_MONTHLY_REPORT_RECIPIENTS', '')
        elif file_processing == 'firm-registration-filings':
            subject = 'BC STATS FIRMS for ' + format(last_month, '%B %Y') + ext
            filename = 'bc_stats_firms_for_' + format(last_month, '%B_%Y') + '.csv'
            recipients = os.getenv('BC_STATS_MONTHLY_REPORT_RECIPIENTS', '')

        # Add body to email
        message.attach(MIMEText('Please see the attachment(s).', 'plain'))

        # Open file in binary mode
        with open(data_directory+filename, 'rb') as attachment:
            # Add file as application/octet-stream
            # Email client can usually download this automatically as attachment
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())

        # Encode file in ASCII characters to send by email
        encoders.encode_base64(part)

        # Add header as key/value pair to attachment part
        part.add_header(
            'Content-Disposition',
            f'attachment; filename= {filename}',
        )

        # Add attachment to message and convert message to string
        message.attach(part)

    message['Subject'] = subject
    server = smtplib.SMTP(os.getenv('EMAIL_SMTP', ''))
    server.connect()
    email_list = recipients.strip('][').split(', ')
    logging.info('Email recipients list is: %s', email_list)
    server.sendmail(os.getenv('SENDER_EMAIL', ''), email_list, message.as_string())
    logging.info('Email with subject %s has been sent successfully!', subject)
    server.quit()
    if filename != '':
        os.remove(os.path.join(os.getcwd(), r'data/')+filename)


def processnotebooks(notebookdirectory, data_directory):
    """Process Notebook."""
    status = False
    now = datetime.now()
    warnings.filterwarnings('ignore', category=DeprecationWarning)

    try:
        retry_times = int(os.getenv('RETRY_TIMES', '1'))
        retry_interval = int(os.getenv('RETRY_INTERVAL', '60'))
        if notebookdirectory == 'monthly':
            days = ast.literal_eval(os.getenv('MONTH_REPORT_DATES', ''))
    except Exception:  # noqa: B902
        logging.exception('Error processing notebook for %s', notebookdirectory)
        send_email(notebookdirectory, data_directory, 'ERROR', traceback.format_exc())
        return status

    # For monthly tasks, we only run on the specified days
    if notebookdirectory == 'daily' or (notebookdirectory == 'monthly' and now.day in days):
        notebookdirectory = os.path.join(os.path.dirname(__file__), notebookdirectory)
        logging.info('Processing: %s', notebookdirectory)

        num_files = len(os.listdir(notebookdirectory))
        file_processed = 0

        for file in findfiles(notebookdirectory, '*.ipynb'):
            file_processed += 1
            note_book = os.path.basename(file)
            for attempt in range(retry_times):
                try:
                    pm.execute_notebook(file, data_directory+'temp.ipynb', parameters=None)
                    send_email(note_book, data_directory, '', '')
                    os.remove(data_directory+'temp.ipynb')
                    status = True
                    break
                except Exception:  # noqa: B902
                    if attempt + 1 == retry_times:
                        # If any errors occur with the notebook processing they will be logged to the log file
                        logging.exception(
                            'Error processing notebook %s at %s/%s try.', notebookdirectory, attempt + 1,
                            retry_times)
                        send_email(notebookdirectory, data_directory, 'ERROR', traceback.format_exc())
                    else:
                        # If any errors occur with the notebook processing they will be logged to the log file
                        logging.exception('Error processing notebook %s at %s/%s try. '
                                          'Sleeping for %s secs before next try', notebookdirectory, attempt + 1,
                                          retry_times, retry_interval)
                        time.sleep(retry_interval)
                        continue
            if not status and num_files == file_processed:
                break
    return status


if __name__ == '__main__':
    start_time = datetime.utcnow()

    data_dir = os.path.join(os.getcwd(), r'data/')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    # Check if the subfolders for notebooks exist, and create them if they don't
    for subdir in ['daily', 'monthly']:
        if not os.path.isdir(subdir):
            os.mkdir(subdir)

        processnotebooks(subdir, data_dir)

    # shutil.rmtree(data_dir)
    end_time = datetime.utcnow()
    logging.info('job - jupyter notebook report completed in: %s', end_time - start_time)
    sys.exit()
