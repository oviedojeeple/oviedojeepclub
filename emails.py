import os
import base64
from datetime import datetime
from flask import render_template, url_for
from azure_services import email_client
from config import Config
import logging

logger = logging.getLogger(__name__)

# Cache logo image base64
_logo_b64 = None
_logo_path = os.path.join(os.path.dirname(__file__), 'static', 'images', 'ojc.png')

def _get_logo_b64():
    global _logo_b64
    if _logo_b64 is None:
        with open(_logo_path, 'rb') as f:
            _logo_b64 = base64.b64encode(f.read()).decode('utf-8')
    return _logo_b64

def _send_email(subject, html_content, recipient_email, recipient_name):
    logger.debug(f"_send_email called with subject='{subject}', recipient_email='{recipient_email}', recipient_name='{recipient_name}'")
    message = {
        "senderAddress": Config.AZURE_COMM_CONNECTION_STRING_SENDER,
        "content": {"subject": subject, "html": html_content},
        "recipients": {"to": [{"address": recipient_email, "displayName": recipient_name}]},
        "attachments": [{
            "name": "ojc.png",
            "contentType": "image/png",
            "contentInBase64": _get_logo_b64(),
            "contentId": "ojc_logo"
        }]
    }
    logger.debug("Invoking email_client.begin_send...")
    try:
        poller = email_client.begin_send(message)
        logger.debug("Email client begin_send returned poller, awaiting result...")
        result = poller.result()
        logger.debug(f"Email sent to {recipient_email}, result: {result}")
        return result
    except Exception:
        logger.exception(f"Error occurred while sending email to {recipient_email}")
        raise

def send_disablement_reminder_email(recipient_email, recipient_name, days_left):
    login_url = url_for('auth.login', _external=True)
    html_content = render_template(
        'emails/disablement_reminder.html',
        recipient_name=recipient_name,
        login_url=login_url,
        days_left=days_left,
        current_year=datetime.now().year
    )
    subject = f"Membership Expiration Reminder - {days_left} Days Left"
    return _send_email(subject, html_content, recipient_email, recipient_name)

def send_event_reminder_email(recipient_email, recipient_name, event, days_left):
    html_content = render_template(
        'emails/event_reminder.html',
        recipient_name=recipient_name,
        event_name=event.get('name'),
        event_start_time=event.get('start_time'),
        days_left=days_left,
        current_year=datetime.now().year
    )
    subject = f"Event Reminder: {event.get('name')} starts in {days_left} day{'s' if days_left>1 else ''}"
    return _send_email(subject, html_content, recipient_email, recipient_name)

def send_family_invitation_email(recipient_email, recipient_name, invitation_link):
    logger.debug(f"send_family_invitation_email called with recipient_email={recipient_email}, recipient_name={recipient_name}, invitation_link={invitation_link}")
    html_content = render_template(
        'emails/family_invitation.html',
        recipient_name=recipient_name,
        invitation_link=invitation_link,
        current_year=datetime.now().year
    )
    subject = "You're Invited to Join the Oviedo Jeep Club Family Membership"
    return _send_email(subject, html_content, recipient_email, recipient_name)

def send_membership_renewal_email(recipient_email, recipient_name):
    html_content = render_template(
        'emails/membership_renewal.html',
        recipient_name=recipient_name,
        current_year=datetime.now().year
    )
    subject = "Membership Renewal Confirmation"
    return _send_email(subject, html_content, recipient_email, recipient_name)

def send_new_membership_email(recipient_email, recipient_name, receipt_url):
    html_content = render_template(
        'emails/new_membership.html',
        recipient_name=recipient_name,
        receipt_url=receipt_url,
        current_year=datetime.now().year
    )
    subject = "Welcome to The Oviedo Jeep Club!"
    return _send_email(subject, html_content, recipient_email, recipient_name)
  
def send_email_change_notification_email(recipient_email, recipient_name, old_email, new_email):
    """Send a notification to the old email that the user has changed their address."""
    logger.debug(f"send_email_change_notification_email called for {recipient_email}, old_email={old_email}, new_email={new_email}")
    html_content = render_template(
        'emails/email_change_notification.html',
        recipient_name=recipient_name,
        old_email=old_email,
        new_email=new_email,
        current_year=datetime.now().year
    )
    subject = "Your Oviedo Jeep Club email address has changed"
    return _send_email(subject, html_content, recipient_email, recipient_name)