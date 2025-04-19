import json
import time
import requests
from datetime import datetime, timezone

from azure_services import blob_service_client
from config import Config

def parse_date(date_str):
    """
    Parse ISO date strings to naive UTC datetime.
    """
    formats = ['%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%dT%H:%M']
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt.tzinfo:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        except ValueError:
            continue
    raise ValueError(f"Invalid date format: {date_str}")

def sort_events_by_date_desc(events):
    """
    Return events sorted by start_time descending.
    """
    return sorted(
        events,
        key=lambda e: parse_date(e['start_time']),
        reverse=True
    )

def get_events_from_blob(future_only=True):
    """
    Download and filter events from Azure Blob.
    """
    client = blob_service_client.get_blob_client(container="events", blob="events.json")
    data = client.download_blob().readall().decode('utf-8')
    events = json.loads(data)
    now = datetime.utcnow()
    if future_only:
        events = [e for e in events if parse_date(e['start_time']) > now]
    else:
        events = [e for e in events if parse_date(e['start_time']) <= now]
    return sort_events_by_date_desc(events)

def upload_events_to_blob(events):
    """
    Upload a list of events to Azure Blob.
    """
    client = blob_service_client.get_blob_client(container="events", blob="events.json")
    content = json.dumps(events)
    client.upload_blob(content, overwrite=True)
    return True, "Events successfully uploaded to Azure Blob Storage."

def get_facebook_events(access_token):
    """
    Fetch public events from Facebook Graph API.
    """
    url = f"https://graph.facebook.com/v22.0/{Config.FACEBOOK_PAGE_ID}/events"
    params = {
        "access_token": access_token,
        "since": int(time.time()),
        "fields": "id,name,description,start_time,end_time,place,cover"
    }
    resp = requests.get(url, params=params)
    data = resp.json()
    if resp.status_code != 200 or 'error' in data:
        raise RuntimeError(f"Facebook API error: {data.get('error')}")
    return data.get('data', [])