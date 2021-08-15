import os
from smtplib import SMTP
from otodom.utils import get_credentials
from email.message import EmailMessage
import logging


def _log_to_server(_creds):
    try:
        server = SMTP(_creds['mail_server'])
        server.ehlo()
        server.starttls()
        server.login(_creds['username'], _creds['password'])
    except Exception as error:
        logging.info(error)
        raise RuntimeError("Falied to log in into the server - check 'send_info' function for server issues")
    return server


def send_info(subject: str, message_content: str) -> None:
    """Sending an info email to my mailbox 

    :param subject: Subject of the email
    :type subject: str
    :param message_content: Content of the email - might include HTML
    :type message_content: str
    """
    _creds = get_credentials()['gmail']
    server = _log_to_server(_creds)
    message = EmailMessage()
    message["From"] = _creds['username']
    message["To"] = _creds['username']
    message["Subject"] = f"FPL-{os.environ['COMPUTERNAME']}: {subject}"
    message.set_content(message_content)
    try:
        server.send_message(message)
    except Exception as error:
        logging.info(error)
        raise RuntimeError("Server login successful, but info email couldn't be sent - check 'send_info' function for server issues")
    server.quit()