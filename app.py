# ========= Imports =========
from flask import Flask, request, jsonify, render_template, send_from_directory, redirect, url_for, session, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_restful import Resource, Api
from flask_cors import CORS
from flask_apscheduler import APScheduler
from datetime import datetime
from azure.storage.blob import BlobServiceClient, BlobLeaseClient
from azure.data.tables import TableServiceClient, UpdateMode
from azure.communication.email import EmailClient
from azure.core.exceptions import ResourceExistsError
from square.client import Client
from urllib.parse import quote
from event_uploader import upload_event_data
import msal
import os, time, requests, json, uuid

# ========= App Initialization and Configuration =========
app.secret_key = os.getenv("FLASK_SECRET_KEY")  # Secure session key (random per restart)
CORS(app)
api = Api(app)

app.config['PROPAGATE_EXCEPTIONS'] = True
app.config['DEBUG'] = True
app.config["SESSION_PERMANENT"] = True

# ========= Environment Config =========
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
print(f'##### DEBUG ##### CLIENT_ID:: {CLIENT_ID}')
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
TENANT_ID = os.getenv("AZURE_TENANT_ID")
print(f'##### DEBUG ##### TENANT_ID:: {TENANT_ID}')
REDIRECT_URI = os.getenv("AZURE_REDIRECT_URI")
print(f'##### DEBUG ##### REDIRECT_URI:: {REDIRECT_URI}')
AZURE_POLICY = os.getenv("AZURE_POLICY")
print(f'##### DEBUG ##### AZURE_POLICY:: {AZURE_POLICY}')
AZURE_AUTHORITY = os.getenv("AZURE_AUTHORITY")
print(f'##### DEBUG ##### AZURE_AUTHORITY:: {AZURE_AUTHORITY}')
AUTHORITY = f"{AZURE_AUTHORITY}/{AZURE_POLICY}"
print(f'##### DEBUG ##### AUTHORITY:: {AUTHORITY}')
LOGIN_URL = f"{AUTHORITY}/oauth2/v2.0/authorize"
print(f'##### DEBUG ##### LOGIN_URL:: {LOGIN_URL}')
TOKEN_URL = f"{AUTHORITY}/oauth2/v2.0/token"
print(f'##### DEBUG ##### TOKEN_URL:: {TOKEN_URL}')
SQUARE_ACCESS_TOKEN = os.getenv("SQUARE_ACCESS_TOKEN")
print(f'##### DEBUG ##### SQUARE_ACCESS_TOKEN:: {SQUARE_ACCESS_TOKEN}')
SQUARE_APPLICATION_ID = os.getenv("SQUARE_APPLICATION_ID")
print(f'##### DEBUG ##### SQUARE_APPLICATION_ID:: {SQUARE_APPLICATION_ID}')
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
print(f'##### DEBUG ##### AZURE_STORAGE_CONNECTION_STRING:: {AZURE_STORAGE_CONNECTION_STRING}')
AZURE_COMM_CONNECTION_STRING = os.getenv("AZURE_COMM_CONNECTION_STRING")
print(f'##### DEBUG ##### AZURE_COMM_CONNECTION_STRING:: {AZURE_COMM_CONNECTION_STRING}')
AZURE_COMM_CONNECTION_STRING_SENDER = os.getenv("AZURE_COMM_CONNECTION_STRING_SENDER")
print(f'##### DEBUG ##### AZURE_COMM_CONNECTION_STRING_SENDER:: {AZURE_COMM_CONNECTION_STRING_SENDER}')

# ========= Extensions Initialization =========
login_manager = LoginManager()
login_manager.init_app(app)

table_service_client = TableServiceClient.from_connection_string(conn_str=AZURE_STORAGE_CONNECTION_STRING)
table_name = "Invitations"
try:
    table_client = table_service_client.create_table_if_not_exists(table_name=table_name)
    print("Table client created or retrieved for table:", table_name)
except Exception as e:
    print("Error creating/getting table:", e)
    table_client = table_service_client.get_table_client(table_name=table_name)

client = Client(
    access_token=SQUARE_ACCESS_TOKEN,
    environment='sandbox'  # Change to 'production' when ready
)

LOCK_CONTAINER = "locks"
LOCK_BLOB_NAME = "expiration_lock.txt"

# ========= Helper Classes =========
class User(UserMixin):
    print(f'##### DEBUG ##### In User class with {UserMixin}')
    def __init__(self, user_id, name, email, membership_number, member_expiration_raw, member_joined_raw, job_title=None, member_expiration_date=None, member_expiration_iso=None):
        print(f'##### DEBUG ##### In User class with {self} and {user_id} and {name} and {email}')
        self.id = user_id
        self.name = name
        self.email = email
        self.membership_number = membership_number
        self.job_title = job_title
        self.member_expiration_date = member_expiration_date
        self.member_expiration_iso = member_expiration_iso
        self.member_expiration_raw = member_expiration_raw
        self.member_joined_raw = member_joined_raw

@login_manager.user_loader
def load_user(user_id):
    user_data = session.get("user_data", {})
    if user_data:
        # Build a User object using the full user_data
        return User(
            user_id=user_data["user_id"],
            name=user_data["name"],
            email=user_data["email"],
            membership_number=user_data.get("membership_number"),
            job_title=user_data.get("job_title"),
            member_expiration_date=user_data.get("member_expiration_date"),
            member_expiration_iso=user_data.get("member_expiration_iso"),
            member_expiration_raw=user_data.get("member_expiration_raw"),
            member_joined_raw=user_data.get("member_joined_raw")
        )
    return None

# ========= Helper Functions =========
def _build_auth_code_flow():
    print("##### DEBUG ##### In _build_auth_code_flow()")
    app = msal.ConfidentialClientApplication(
        CLIENT_ID,
        CLIENT_SECRET,
        authority=AUTHORITY
    )
    return app.initiate_auth_code_flow([], redirect_uri=REDIRECT_URI)

def _acquire_token_by_auth_code_flow(flow, args):
    print("##### DEBUG ##### In _acquire_token_by_auth_code_flow")
    app = msal.ConfidentialClientApplication(CLIENT_ID, CLIENT_SECRET, authority=AUTHORITY)
    result = app.acquire_token_by_auth_code_flow(flow, args)
    if "id_token" in result:
        user_info = result["id_token_claims"]  # Extract user details from ID token
        return user_info
    return None

def _get_user_info(access_token):
    print(f'##### DEBUG ##### In _get_user_info with {access_token}')
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers)
    print(f'##### DEBUG ##### In _get_user_info - response:: {response}')
    return response.json()

def _acquire_graph_api_token():
    print("##### DEBUG ##### In _acquire_graph_api_token()")
    authority_url = f"https://login.microsoftonline.com/{TENANT_ID}"
    app = msal.ConfidentialClientApplication(
        CLIENT_ID,
        client_credential=CLIENT_SECRET,
        authority=authority_url
    )
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" in result:
        return result["access_token"]
    else:
        print("Error acquiring Graph token:", result.get("error_description"))
        return None

def acquire_lock():
    print("##### DEBUG ##### In acquire_lock()")
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    # Ensure the locks container exists.
    container_client = blob_service_client.get_container_client(LOCK_CONTAINER)
    try:
        container_client.create_container()
    except ResourceExistsError:
        print("##### DEBUG ##### In acquire_lock() resource exists, passing...")
        pass
    except Exception as e:
        print("Unexpected error creating container:", e)
        raise
    blob_client = container_client.get_blob_client(LOCK_BLOB_NAME)
    # Create the blob if it doesn't exist.
    try:
        blob_client.upload_blob("lock", overwrite=False)
    except Exception:
        pass  # Already exists.
    try:
        lease = BlobLeaseClient(blob_client)
        lease.acquire(lease_duration=-1)
        print("##### DEBUG ##### In acquire_lock() Lock acquired.")
        return lease
    except Exception as e:
        print("Could not acquire lock:", e)
        return None

def compute_expiration_date():
    print("##### DEBUG ##### In compute_expiration_date()")
    now = datetime.now()
    current_year = now.year
    oct_31 = datetime(current_year, 10, 31)
    if now > oct_31:
        expiration = datetime(current_year + 2, 3, 31)
    else:
        expiration = datetime(current_year + 1, 3, 31)
    return int(expiration.timestamp())

def create_b2c_user(email, display_name, password, membership_number, join_date, expiration_date):
    print("##### DEBUG ##### In create_b2c_user() Attempting to create B2C user with:", email, display_name, membership_number, join_date, expiration_date)
    tenant_id = os.getenv("AZURE_TENANT_ID")
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    scope = ["https://graph.microsoft.com/.default"]
    
    app_msal = msal.ConfidentialClientApplication(client_id, authority=authority, client_credential=client_secret)
    result = app_msal.acquire_token_for_client(scopes=scope)
    if "access_token" not in result:
        raise Exception("Error acquiring Graph token: " + result.get("error_description", "Unknown error"))
    token = result["access_token"]
    
    mail_nickname = email.replace("@", "_at_")
    expected_upn = f"{mail_nickname}@oviedojeepclub.onmicrosoft.com"
    
    user_payload = {
        "accountEnabled": True,
        "displayName": display_name,
        "userPrincipalName": expected_upn,
        "mailNickname": mail_nickname,
        "passwordProfile": {
            "forceChangePasswordNextSignIn": False,
            "password": password
        },
        "identities": [
            {
                "signInType": "emailAddress",
                "issuer": "oviedojeepclub.onmicrosoft.com",
                "issuerAssignedId": email
            }
        ]
    }
    
    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json"
    }
    
    response = requests.post("https://graph.microsoft.com/v1.0/users", headers=headers, json=user_payload)
    print("Graph API create user response:", response.status_code, response.text)
    if response.status_code == 201:
        created_user = response.json()
        update_payload = {
            "otherMails": [email],
            "extension_b32ce28f40e2412fb56abae06a1ac8ab_MembershipNumber": membership_number,
            "extension_b32ce28f40e2412fb56abae06a1ac8ab_MemberJoinedDate": join_date,
            "extension_b32ce28f40e2412fb56abae06a1ac8ab_MemberExpirationDate": expiration_date
        }
        update_response = requests.patch(f"https://graph.microsoft.com/v1.0/users/{created_user['id']}",
                                         headers=headers, json=update_payload)
        if update_response.status_code not in [200, 204]:
            raise Exception("Error updating user custom attributes: " + update_response.text)
        return created_user
    else:
        raise Exception("Error creating user: " + response.text)

def create_membership_details():
    print("##### DEBUG ##### In create_membership_details()")
    import time
    from datetime import datetime
    membership_number = "OJC" + str(int(time.time() * 1000))
    join_date = int(datetime.now().timestamp())
    expiration_date = compute_expiration_date()
    return membership_number, join_date, expiration_date

def delete_invitation(token):
    print("##### DEBUG ##### In delete_invitation()")
    try:
        table_client.delete_entity(partition_key=token, row_key=token)
    except Exception as e:
        print("Error deleting invitation:", e)

def get_all_users():
    print("##### DEBUG ##### In get_all_users()")
    token = _acquire_graph_api_token()
    if not token:
        print("Error: Could not acquire Graph API token.")
        return []
    
    headers = {"Authorization": f"Bearer {token}"}
    select_fields = "id,displayName,mailNickname,extension_b32ce28f40e2412fb56abae06a1ac8ab_MemberExpirationDate"
    url = f"https://graph.microsoft.com/v1.0/users?$select={select_fields}"
    
    users = []
    while url:
        response = requests.get(url, headers=headers)
        print("##### DEBUG ##### In get_all_users() with response: ", response)
        if response.status_code == 200:
            data = response.json()
            users.extend(data.get("value", []))
            url = data.get("@odata.nextLink")
        else:
            print(f"Error fetching users: {response.status_code} {response.text}")
            break

    return users

def get_events_from_blob(future_only=True):
    print("##### DEBUG ##### In get_events_from_blob()")
    connection_string = AZURE_STORAGE_CONNECTION_STRING
    try:
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    except Exception as e:
        print("Error initializing BlobServiceClient:", e)
        return []
    
    container_name = "events"
    blob_client = blob_service_client.get_blob_client(container=container_name, blob="events.json")
    try:
        blob_data = blob_client.download_blob().readall().decode('utf-8')
        events = json.loads(blob_data)
        
        now = datetime.utcnow()

        if future_only:
            # Filter for only future events
            events = [
                event for event in events
                if parse_date(event.get('start_time')) > now
            ]
        else:
            # Filter for only past events
            events = [
                event for event in events
                if parse_date(event.get('start_time')) <= now
            ]

        return sort_events_by_date_desc(events)
    except Exception as e:
        print("Error reading events blob:", e)
        return []

def upload_events_to_blob(events):
    print("##### DEBUG ##### In upload_events_to_blob()")
    connection_string = AZURE_STORAGE_CONNECTION_STRING
    if not connection_string:
        print("##### DEBUG ##### In upload_events_to_blob() Azure Storage connection string is not set!")
        return False, "Azure Storage connection string is not set"
    try:
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    except Exception as e:
        print("Error initializing BlobServiceClient:", e)
        return False, str(e)

    container_name = "events"
    blob_client = blob_service_client.get_blob_client(container=container_name, blob="events.json")
    try:
        events_json = json.dumps(events)
        blob_client.upload_blob(events_json, overwrite=True)
        print("##### DEBUG ##### In upload_events_to_blob() Events successfully uploaded to Azure Blob Storage.")
        return True, "Events successfully uploaded to Azure Blob Storage."
    except Exception as e:
        print("Error uploading blob:", e)
        return False, str(e)

def user_still_exists(email):
    print(f'##### DEBUG ##### In user_still_exists with {email}')
    token = _acquire_graph_api_token()
    if not token:
        return False
    headers = {"Authorization": f"Bearer {token}"}
    mail_nickname = email.replace("@", "_at_")
    expected_upn = f"{mail_nickname}@oviedojeepclub.onmicrosoft.com"
    filter_query = f"userPrincipalName eq '{expected_upn}'"
    url = f"https://graph.microsoft.com/v1.0/users?$filter={quote(filter_query)}"
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data.get("value") and len(data["value"]) > 0:
            return True
    else:
        print("Error checking user existence:", response.status_code, response.text)
    return False

def is_renewal_eligible(user):
    print("##### DEBUG ##### In is_renewal_eligible()")
    today = datetime.date.today()
    if "membership_expiration" in user:
        expiration_date = datetime.datetime.strptime(user["membership_expiration"], "%Y-%m-%d").date()
        renewal_start = datetime.date(expiration_date.year, 1, 1)
        renewal_end = datetime.date(expiration_date.year, 3, 31)
        return renewal_start <= today <= renewal_end
    return False

def get_facebook_events(page_id, access_token):
    print("##### DEBUG ##### In get_facebook_events()")
    url = f"https://graph.facebook.com/v22.0/{page_id}/events"
    params = {
        "access_token": access_token,
        "since": int(time.time()),
        "fields": "id,name,description,start_time,end_time,place,cover"
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if "error" in data:
            print("Facebook API error:", data["error"])
            return None
        return data.get("data", [])
    except Exception as e:
        print("Error fetching Facebook events:", e)
        return None

def get_invitation(token):
    print("##### DEBUG ##### In get_invitation()")
    try:
        entity = table_client.get_entity(partition_key=token, row_key=token)
        return dict(entity)
    except Exception as e:
        print("Error retrieving invitation:", e)
        return None

def parse_date(date_str):
    print("##### DEBUG ##### In parse_date()")
    from datetime import datetime, timezone
    formats = ['%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%dT%H:%M']
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        except ValueError:
            continue
    raise ValueError("No valid date format found for: " + date_str)

def release_lock(lease):
    print("##### DEBUG ##### In release_lock()")
    try:
        lease.release()
        print("##### DEBUG ##### In release_lock() Lock released.")
    except Exception as e:
        print("Could not release lock:", e)

def sort_events_by_date_desc(events):
    print("##### DEBUG ##### In sort_events_by_date_desc()")
    return sorted(
        events,
        key=lambda e: parse_date(e['start_time']),
    )

def send_disablement_reminder_email(recipient_email, recipient_name, days_left):
    print("##### DEBUG ##### In send_disablement_reminder_email()")
    email_client = EmailClient.from_connection_string(AZURE_COMM_CONNECTION_STRING)
    try:
        # Define the login URL for renewal; update this to your actual URL if different.
        login_url = "https://test.oviedojeepclub.com/login"
        message = {
            "senderAddress": AZURE_COMM_CONNECTION_STRING_SENDER,
            "content": {
                "subject": "Membership Expiration Reminder",
                "plainText": (
                    f"Hello {recipient_name},\n\n"
                    f"Your membership is set to expire in {days_left} day(s).\n\n"
                    "To renew your membership, please log in to your account using the link below and click on the 'Renew Membership' button:\n"
                    f"{login_url}\n\n"
                    "Thank you for being a valued member of the Oviedo Jeep Club."
                ),
                "html": (
                    f"<html><body><h1>Membership Expiration Reminder</h1>"
                    f"<p>Hello {recipient_name},</p>"
                    f"<p>Your membership is set to expire in <strong>{days_left}</strong> day(s).</p>"
                    f"<p>To renew your membership, please <a href='{login_url}'>log in</a> to your account and click on the 'Renew Membership' button.</p>"
                    f"<p>Thank you for being a valued member of the Oviedo Jeep Club.</p>"
                    f"</body></html>"
                )
            },
            "recipients": {
                "to": [
                    {"address": recipient_email, "displayName": recipient_name}
                ]
            }
        }
        poller = email_client.begin_send(message)
        result = poller.result()
        print("##### DEBUG ##### In send_disablement_reminder_email() Email sent! Result:", result)
    except Exception as e:
        print("Error sending disablement reminder email:", e)

def send_family_invitation_email(recipient_email, recipient_name, invitation_link):
    print("##### DEBUG ##### In send_family_invitation_email()")
    email_client = EmailClient.from_connection_string(AZURE_COMM_CONNECTION_STRING)
    try:
        message = {
            "senderAddress": AZURE_COMM_CONNECTION_STRING_SENDER,
            "content": {
                "subject": "You're Invited to Join the Oviedo Jeep Club Family Membership",
                "plainText": (
                    f"Hello {recipient_name},\n\n"
                    f"You have been invited to join the Oviedo Jeep Club family membership. "
                    f"Please click the link below to accept your invitation:\n{invitation_link}"
                ),
                "html": (
                    f"<html><body><h1>Invitation to Join Oviedo Jeep Club</h1>"
                    f"<p>Hello {recipient_name},</p>"
                    f"<p>You have been invited to join the Oviedo Jeep Club family membership. "
                    f"Please click the link below to accept your invitation:</p>"
                    f"<a href='{invitation_link}'>Accept Invitation</a></body></html>"
                )
            },
            "recipients": {
                "to": [
                    {"address": recipient_email, "displayName": recipient_name}
                ]
            }
        }
        poller = email_client.begin_send(message)
        result = poller.result()
        flash("Family member invite sent successfully.", "success")
        print("##### DEBUG ##### In send_family_invitation_email() Invitation email sent! Result:", result)
    except Exception as e:
        flash("Family member invite failed to be sent.", "danger")
        print("Error sending family invitation email:", e)

def send_membership_renewal_email(recipient_email, recipient_name):
    print("##### DEBUG ##### In send_membership_renewal_email()")
    email_client = EmailClient.from_connection_string(AZURE_COMM_CONNECTION_STRING)
    try:
        message = {
            "senderAddress": AZURE_COMM_CONNECTION_STRING_SENDER,
            "content": {
                "subject": "Membership Renewal Confirmation",
                "plainText": "Your membership has been renewed successfully!",
                "html": (
                    "<html><body><h1>Membership Renewal Confirmation</h1>"
                    "<p>Your membership has been renewed successfully!</p>"
                    "</body></html>"
                )
            },
            "recipients": {
                "to": [
                    {"address": recipient_email, "displayName": recipient_name}
                ]
            }
        }
        poller = email_client.begin_send(message)
        result = poller.result()
        print("##### DEBUG ##### In send_membership_renewal_email() Email sent! Result:", result)
    except Exception as e:
        print("Error sending membership renewal email:", e)

def send_new_membership_email(recipient_email, recipient_name, receipt_url):
    print("##### DEBUG ##### In send_new_membership_email()")
    email_client = EmailClient.from_connection_string(AZURE_COMM_CONNECTION_STRING)
    try:
        message = {
            "senderAddress": AZURE_COMM_CONNECTION_STRING_SENDER,
            "content": {
                "subject": "Welcome to Oviedo Jeep Club!",
                "plainText": (
                    f"Hello {recipient_name},\n\n"
                    f"Your account has been created successfully.\n"
                    f"View your receipt here: {receipt_url}"
                ),
                "html": (
                    f"<html><body><h1>Welcome to Oviedo Jeep Club!</h1>"
                    f"<p>Hello {recipient_name},</p>"
                    f"<p>Your account has been created successfully.</p>"
                    f"<p>View your receipt <a href='{receipt_url}'>here</a>.</p>"
                    f"</body></html>"
                )
            },
            "recipients": {
                "to": [
                    {"address": recipient_email, "displayName": recipient_name}
                ]
            }
        }
        poller = email_client.begin_send(message)
        result = poller.result()
        print("##### DEBUG ##### In send_new_membership_email() Email sent! Result:", result)
    except Exception as e:
        print("Error sending new membership email:", e)

def store_invitation(token, data, expire_seconds=3600):
    print("##### DEBUG ##### In store_invitation()")
    entity = {
        "PartitionKey": token,
        "RowKey": token,
        **data,
        "CreatedAt": datetime.utcnow().isoformat()
    }
    table_client.upsert_entity(entity=entity, mode=UpdateMode.REPLACE)
    
# ========= Context Processors =========
@app.context_processor
def inject_now():
    return {'now': lambda: datetime.utcnow()}

@app.context_processor
def inject_user_data():
    return {"user_data": session.get("user", {})}

@app.template_filter('timestamp_to_year')
def timestamp_to_year(ts):
    try:
        ts = int(ts)
        # If timestamp is in milliseconds, convert to seconds.
        if ts > 1e10:
            ts = ts / 1000
        return datetime.fromtimestamp(ts).year
    except Exception as e:
        print("Error converting timestamp to year:", e)
        return "N/A"

def check_membership_expiration():
    print("##### DEBUG ##### In check_membership_expiration()")
    run_id = uuid.uuid4()
    start_time = datetime.utcnow().isoformat()
    pid = os.getpid()
    print(f"##### DEBUG ##### In check_membership_expiration() [{start_time}] [PID {pid}] expiration_check job STARTED. Run ID: {run_id}")
    lease = acquire_lock()
    if not lease:
        print("##### DEBUG ##### In check_membership_expiration() - Another instance is processing; skipping this run.")
        end_time = datetime.utcnow().isoformat()
        print(f"##### DEBUG ##### In check_membership_expiration() [{end_time}] [PID {pid}] expiration_check job DID NOT START. Run ID: {run_id}")
        return
    try:
        print("##### DEBUG ##### In check_membership_expiration() - begin processing...")
        today = datetime.today().date()
        users = get_all_users()
        processed_ids = set()  # To avoid duplicates within one run.
        for user in users:
            user_id = user.get("id")
            if user_id in processed_ids:
                continue
            processed_ids.add(user_id)
            print("Processing user:", user)
            expiration_timestamp = user.get("extension_b32ce28f40e2412fb56abae06a1ac8ab_MemberExpirationDate")
            if expiration_timestamp:
                if expiration_timestamp > 1e10:
                    expiration_timestamp = expiration_timestamp / 1000
                expiration_date = datetime.fromtimestamp(expiration_timestamp).date()
                days_left = (expiration_date - today).days
                if days_left in [90, 60, 30, 15, 1]:
                    email = user.get('mailNickname', '').replace('_at_', '@')
                    print("About to send email to:", email)
                    try:
                        send_disablement_reminder_email(email, user.get('displayName', 'Member'), days_left)
                        print("Email sent to:", email)
                    except Exception as e:
                        print("Error sending email to", email, ":", e)
        end_time = datetime.utcnow().isoformat()
        print(f"##### DEBUG ##### In check_membership_expiration() [{end_time}] [PID {pid}] expiration_check job FINISHED. Run ID: {run_id}")
    finally:
        release_lock(lease)

# ========= API Resource =========
class Main(Resource):
    def post(self):
        return jsonify({'message': 'Welcome to the Oviedo Jeep Club Flask REST App'})

api.add_resource(Main, '/')

# ========= After Request =========
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

# ========= Scheduler Initialization =========
scheduler = APScheduler()
scheduler.add_job(func=check_membership_expiration, trigger="cron", hour=17, minute=30, id="expiration_check")
scheduler.start()
jobs = scheduler.get_jobs()
print(f"##### DEBUG ##### Initialized scheduler - Scheduler jobs count: {len(jobs)}; jobs: {jobs}")
