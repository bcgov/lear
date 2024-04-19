"""The Notebook Report - This module is the API for the Filings Notebook Report."""

import ast
import fnmatch
import logging
import os
import smtplib
import sys
import traceback
import papermill as pm
import shutil

from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from config import Config
from util.logging import setup_logging
from tasks.ftp_processor import FtpProcessor

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


def archive_files(data_dir, dest_dir):
    for file in os.listdir(data_dir):
        shutil.move(data_dir + file, dest_dir + file)
    logging.info("Data files were archived successfully!")


def send_email(note_book, emailtype, errormessage):
    """Send email for results."""
    date = datetime.strftime(datetime.now(), '%Y-%m-%d')

    ext = ''
    if not Config.ENVIRONMENT == 'prod':
        ext = ' on ' + Config.ENVIRONMENT

    message = MIMEMultipart()

    if emailtype == 'ERROR':
        subject = "SFTP Gazette Error Notification from LEAR for processing '" \
            + note_book + "' on " + date + ext
        recipients = Config.ERROR_EMAIL_RECIPIENTS
        message.attach(MIMEText('ERROR!!! \n' + errormessage, 'plain'))
    else:
        subject = 'SFTP Gazette Report ' + note_book + "' on " + date + ext
        filename = 'sent_to_gazette.xml'
        recipients = Config.SFTP_GAZETTE_RECIPIENTS
        # Add body to email
        message.attach(MIMEText('Please see the attachment(s).', 'plain'))

        # Open file in binary mode
        with open(os.path.join(os.getcwd(), r'data/')+filename, 'rb') as attachment:
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
    server = smtplib.SMTP(Config.EMAIL_SMTP)
    email_list = recipients.strip('][').split(', ')
    logging.info('Email recipients list is: %s', email_list)
    server.sendmail(Config.SENDER_EMAIL, email_list, message.as_string())
    logging.info("Email with subject \'%s\' has been sent successfully!", subject)
    server.quit()


def processnotebooks(notebookdirectory, data_dir):
    """Process data."""
    
    logging.info('Start processing directory: %s', notebookdirectory)

    try:
        pm.execute_notebook(os.path.join(notebookdirectory, "generate_files.ipynb"),
                            data_dir + 'temp.ipynb', parameters=None)
        os.remove(data_dir+'temp.ipynb')

        FtpProcessor.process_ftp(data_dir)

        pm.execute_notebook(os.path.join(notebookdirectory, "update_database.ipynb"),
                            data_dir + 'temp.ipynb', parameters=None)
        send_email(notebookdirectory, '', '')
        os.remove(data_dir+'temp.ipynb')

    except Exception:
        logging.exception('Error processing notebook %s.', notebookdirectory)
        send_email(notebookdirectory, 'ERROR', traceback.format_exc())


if __name__ == '__main__':
    start_time = datetime.utcnow()

    temp_dir = os.path.join(os.getcwd(), r'data/')
    # Check if the subfolders for notebooks exist, and create them if they don't
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    for subdir in ['weekly']:
        processnotebooks(subdir, temp_dir)

    end_time = datetime.utcnow()
    logging.info('job - jupyter notebook report completed in: %s', end_time - start_time)
    sys.exit()
