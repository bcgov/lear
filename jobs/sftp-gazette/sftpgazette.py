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

    subject = "SFTP Gazette Error Notification from LEAR for processing '" \
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


def processnotebooks(notebookdirectory):
    """Process data."""
    status = False
         
    logging.info('Start processing directory: %s', notebookdirectory)        
    data_dir = os.getenv('DATA_DIR', '/opt/app-root/data/') 
    dest_dir = os.getenv('SFTP_ARCHIVE_DIRECTORY', '/opt/app-root/archive/')            
    
    try: 
        pm.execute_notebook(os.path.join(notebookdirectory, "generate_files.ipynb") , data_dir +'temp.ipynb', parameters=None)   
        os.remove(data_dir+'temp.ipynb')   

        FtpProcessor.process_ftp(data_dir)                        
                    
        pm.execute_notebook(os.path.join(notebookdirectory, "update_database.ipynb") , data_dir +'temp.ipynb', parameters=None)   
        os.remove(data_dir+'temp.ipynb')      

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
