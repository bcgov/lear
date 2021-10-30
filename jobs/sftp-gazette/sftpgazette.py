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
    message = MIMEMultipart()
    date = datetime.strftime(datetime.now(), '%Y%m%d')
    
    ext = ''
    if not os.getenv('ENVIRONMENT', '') == 'prod':
        ext = ' on ' + os.getenv('ENVIRONMENT', '')

    if emailtype == 'ERROR':
        subject = "SFTP Gazette Error Notification from LEAR for processing '" \
            + note_book + "' on " + date + ext
        recipients = os.getenv('ERROR_EMAIL_RECIPIENTS', '')
        message.attach(MIMEText('ERROR!!! \n' + errormessage, 'plain'))
    else:
        subject = 'SFTP Gazette Files ' + date + ext
        # filename = 'COOP_GAZETTE_CHANGEOFNAME_' + date + '.TXT'
        recipients = os.getenv('SFTP_GAZETTE_RECIPIENTS', '')

        # Add body to email
        message.attach(MIMEText('Please see attached.', 'plain'))

        for filename in os.listdir(os.getenv('DATA_DIR', '/opt/app-root/data')):            
            # Open file in binary mode
            with open(os.getenv('DATA_DIR', '')+filename, 'rb') as attachment:
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
    email_list = recipients.strip('][').split(', ')
    logging.info('Email recipients list is: %s', email_list)
    server.sendmail(os.getenv('SENDER_EMAIL', ''), email_list, message.as_string())
    logging.info("Email with subject \'%s\' has been sent successfully!", subject)
    server.quit()


def processnotebooks(notebookdirectory):
    """Process data."""
    status = False
         
    logging.info('Start processing: %s', notebookdirectory)        
    data_dir = os.getenv('DATA_DIR', '/opt/app-root/data') 
    dest_dir = os.getenv('SFTP_ARCHIVE_DIRECTORY', '/opt/app-root/archive/') 
    for file in findfiles(notebookdirectory, '*.ipynb'):        
        note_book = os.path.basename(file)        
        
        try:       
            pm.execute_notebook(file, data_dir +'temp.ipynb', parameters=None)   
            os.remove(data_dir+'temp.ipynb') 
            
            FtpProcessor.process_ftp(data_dir)                
            logging.info('SFTP to Gazette completed')

            send_email(note_book, '', '')   
            archive_files (data_dir, dest_dir)            
                                    
            status = True                    
        except Exception:            
            logging.exception('Error processing notebook %s.', notebookdirectory)
            send_email(notebookdirectory, 'ERROR', traceback.format_exc())            

    return status;    
   

if __name__ == '__main__':
    start_time = datetime.utcnow()
    processnotebooks('notebook')
    end_time = datetime.utcnow()
    logging.info('job - jupyter notebook report completed in: %s', end_time - start_time)
    sys.exit()
