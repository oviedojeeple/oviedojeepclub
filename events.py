"""
Events blueprint: manages event creation, deletion, Facebook syncing, and scheduled reminder emails.
"""
import uuid
import json
import requests
from datetime import datetime
from flask import Blueprint, jsonify, request, flash, redirect, url_for, session
from flask_login import login_required, current_user
from config import Config
from azure_services import blob_service_client
from event_utils import (
    parse_date, sort_events_by_date_desc,
    get_events_from_blob, upload_events_to_blob,
    get_facebook_events
)
from emails import send_event_reminder_email

events_bp = Blueprint('events', __name__)

@events_bp.route('/blob-events')
@login_required
def blob_events():
    # Return future events from blob
    try:
        events = get_events_from_blob(future_only=True)
        return jsonify(events)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@events_bp.route('/create_event', methods=['GET', 'POST'])
@login_required
def create_event():
    if request.method == 'POST':
        unique_id = 'OJC' + str(int(uuid.uuid4().int >> 64))
        data = request.form.to_dict(flat=True)
        # Map form to event object
        event = {
            'id': unique_id,
            'name': data.get('name', '').strip(),
            'description': data.get('description', '').strip(),
            'start_time': data.get('start_time', '').strip(),
            'end_time': data.get('end_time') or None,
            'place': {
                'name': data.get('place_name', '').strip(),
                'location': {
                    'city': data.get('city', '').strip(),
                    'country': data.get('country', '').strip(),
                    'latitude': float(data.get('latitude', 0)),
                    'longitude': float(data.get('longitude', 0)),
                    'state': data.get('state', '').strip(),
                    'street': data.get('street') or None,
                    'zip': data.get('zip') or None,
                },
                'id': data.get('place_id') or None,
            },
            'cover': {
                'offset_x': int(data.get('offset_x', 0)),
                'offset_y': int(data.get('offset_y', 0)),
                'source': None,
                'id': data.get('cover_id') or None,
            }
        }
        # Handle cover image upload
        cover_file = request.files.get('cover_image')
        if cover_file:
            blob_client = blob_service_client.get_blob_client(
                container='event-images', blob=cover_file.filename
            )
            blob_client.upload_blob(cover_file, overwrite=True)
            event['cover']['source'] = blob_client.url
        else:
            event['cover']['source'] = data.get('cover_source', '').strip()
        # Append and upload
        events = get_events_from_blob(future_only=True)
        events.append(event)
        success, msg = upload_events_to_blob(events)
        flash(msg, 'success' if success else 'danger')
        return redirect(url_for('index', section='events'))
    return redirect(url_for('index'))

@events_bp.route('/delete_event/<event_id>', methods=['POST'])
@login_required
def delete_event(event_id):
    if current_user.job_title != 'OJC Board Member':
        flash('Not authorized to delete events.', 'danger')
        return redirect(url_for('index'))
    events = get_events_from_blob(future_only=True)
    filtered = [e for e in events if e.get('id') != event_id]
    success, msg = upload_events_to_blob(filtered)
    flash(msg, 'success' if success else 'danger')
    return redirect(url_for('index', section='events'))

@events_bp.route('/fb-events')
@login_required
def fb_events():
    token = session.get('fb_access_token')
    try:
        fb_events = get_facebook_events(token)
        return jsonify(sort_events_by_date_desc(fb_events))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@events_bp.route('/sync-public-events')
def sync_public_events():
    # Initiate Facebook OAuth
    state = uuid.uuid4().hex
    session['fb_state'] = state
    params = {
        'client_id': Config.FACEBOOK_APP_ID,
        'redirect_uri': Config.FACEBOOK_REDIRECT_URI,
        'state': state,
        'scope': 'pages_read_engagement,pages_read_user_content',
        'response_type': 'code'
    }
    from urllib.parse import urlencode
    url = f"https://www.facebook.com/v22.0/dialog/oauth?{urlencode(params)}"
    return redirect(url)

@events_bp.route('/facebook/callback')
def facebook_callback():
    if request.args.get('state') != session.get('fb_state'):
        return 'State mismatch', 400
    code = request.args.get('code')
    if not code:
        return 'No code', 400
    token_url = 'https://graph.facebook.com/v22.0/oauth/access_token'
    params = {
        'client_id': Config.FACEBOOK_APP_ID,
        'redirect_uri': Config.FACEBOOK_REDIRECT_URI,
        'client_secret': Config.FACEBOOK_APP_SECRET,
        'code': code
    }
    resp = requests.get(token_url, params=params)
    data = resp.json()
    access_token = data.get('access_token')
    if not access_token:
        return 'Error fetching token', 400
    session['fb_access_token'] = access_token
    # Sync events
    fb_events = get_facebook_events(access_token)
    local = [e for e in get_events_from_blob(future_only=True) if e.get('id', '').startswith('OJC')]
    combined = local + fb_events
    success, msg = upload_events_to_blob(sort_events_by_date_desc(combined))
    flash('Facebook events synced' if success else msg, 'success' if success else 'danger')
    return redirect(url_for('index', section='events'))

def check_event_reminders():
    """
    Scheduled job: send event reminder emails.
    """
    from user_services import get_all_users
    # Acquire events and users
    events = get_events_from_blob(future_only=True)
    users = get_all_users()
    today = datetime.utcnow().date()
    for event in events:
        try:
            event_date = parse_date(event['start_time']).date()
        except Exception:
            continue
        days_left = (event_date - today).days
        if days_left in [15, 8, 1]:
            for user in users:
                expiration_ts = user.get('extension_b32ce28f40e2412fb56abae06a1ac8ab_MemberExpirationDate')
                if expiration_ts and (expiration_ts / 1000 if expiration_ts > 1e10 else expiration_ts):
                    from datetime import datetime as _dt
                    exp_date = _dt.fromtimestamp(
                        expiration_ts / 1000 if expiration_ts > 1e10 else expiration_ts
                    ).date()
                    if event_date < exp_date:
                        recipient = user.get('mailNickname', '').replace('_at_', '@')
                        name = user.get('displayName', 'Member')
                        send_event_reminder_email(recipient, name, event, days_left)