from flask import Flask, request, jsonify, render_template, send_from_directory, redirect, url_for, session, flash, redirect
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_restful import Resource, Api
from flask_cors import CORS
from datetime import datetime
from azure.storage.blob import BlobServiceClient
from square.client import Client
from urllib.parse import quote
import msal
import os, time, requests, json

# Initialize Flask App
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")  # Secure session key (random per restart)
CORS(app)
api = Api(app)

app.config['PROPAGATE_EXCEPTIONS'] = True
app.config['DEBUG'] = True
app.config["SESSION_PERMANENT"] = True

# Azure Entra ID Config (Using Environment Variables)
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
print(f'##### DEBUG ##### TOKEN_URL:: {SQUARE_ACCESS_TOKEN}')
SQUARE_APPLICATION_ID = os.getenv("SQUARE_APPLICATION_ID")
print(f'##### DEBUG ##### TOKEN_URL:: {SQUARE_APPLICATION_ID}')

login_manager = LoginManager()
login_manager.init_app(app)

client = Client(
    access_token=SQUARE_ACCESS_TOKEN,
    environment='sandbox'  # Change to 'production' when ready
)

class User(UserMixin):
    print(f'##### DEBUG ##### In User class with {UserMixin}')
    def __init__(self, user_id, name, email, job_title=None, member_expiration_date=None):
        print(f'##### DEBUG ##### In User class with {self} and {user_id} and {name} and {email}')
        self.id = user_id
        self.name = name
        self.email = email
        self.job_title = job_title
        self.member_expiration_date = member_expiration_date

@login_manager.user_loader
def load_user(user_id):
    print(f'##### DEBUG ##### In load_user with {user_id}')
    print("##### DEBUG ##### In load_user with Full session:", dict(session))
    user_data = session.get("user")
    if user_data and user_data.get("user_id") == user_id:
        print(f'##### DEBUG ##### Session user data: {user_data}')
        return User(**user_data)
    return None

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/x-icon')
@app.before_request
def validate_user_session():
    print("##### DEBUG ##### In validate_user_session()")
    if current_user.is_authenticated:
        if not user_still_exists(current_user.id):
            logout_user()
            session.clear()
            flash("Your account is no longer valid. Please log in again.")
            return redirect(url_for("login"))

@app.route('/')
def index():
    print("##### DEBUG ##### In index()")
    application_id = os.getenv('SQUARE_APPLICATION_ID')
    return render_template('index.html', application_id=application_id, user=current_user)

@app.route('/auth/callback')
def auth_callback():
    print("##### DEBUG ##### In auth_callback()")
    flow = session.get("flow")
    if not flow:
        print("##### DEBUG ##### In auth_callback() Session expired or lost, please try logging in again.")
        return redirect(url_for("login"))
    
    result = _acquire_token_by_auth_code_flow(flow, request.args)
    if result:
        user_info = result
        print("##### DEBUG ##### In auth_callback(): Full token claims:", user_info)

        # Retrieve the raw custom attribute value
        member_expiration_raw = user_info.get("extension_MemberExpirationDate")
        
        # Convert the integer timestamp to a date string.
        if member_expiration_raw:
            try:
                timestamp_int = int(member_expiration_raw)
                if timestamp_int > 1e10:
                    timestamp_int = timestamp_int / 1000
                member_expiration = datetime.fromtimestamp(timestamp_int).strftime('%B, %-d %Y')
            except Exception as e:
                print("Error converting timestamp:", e)
                member_expiration = "Invalid Date"
        else:
            member_expiration = "Not Available"
        
        # Safely get the job title (or default if not present)
        job_title = user_info.get("jobTitle", "OJC Member")
        
        # Create the user_data dictionary
        user_data = {
            "user_id": user_info["oid"],
            "name": user_info["name"],
            "email": user_info["emails"][0],
            "job_title": job_title,
            "member_expiration_date": member_expiration
        }
        session["user"] = user_data
        
        # Pass a new User instance to login_user if needed by Flask-Login
        login_user(User(**user_data), remember=True)
        print("##### DEBUG ##### In auth_callback() Session after login: ", session)
        return redirect(url_for("index"))
    
    return "Login failed", 401

@app.route('/blob-events')
@login_required
def blob_events():
    print("##### DEBUG ##### In blob_events()")
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    try:
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_name = "events"  # Make sure this container exists.
        blob_client = blob_service_client.get_blob_client(container=container_name, blob="events.json")
        events_blob = blob_client.download_blob().readall()
        events_data = json.loads(events_blob)
        sorted_events = sort_events_by_date_desc(events_data)
        return jsonify(sorted_events)
    except Exception as e:
        print("Error reading blob events:", e)
        return jsonify({"error": "Unable to read events from blob"}), 500

@app.route('/facebook/callback')
@login_required
def facebook_callback():
    print("##### DEBUG ##### In facebook_callback()")
    # Verify state parameter for security
    if request.args.get('state') != session.get('fb_state'):
        return "State mismatch", 400

    code = request.args.get('code')
    if not code:
        return "No code provided", 400

    token_url = "https://graph.facebook.com/v22.0/oauth/access_token"
    redirect_uri = os.getenv("FACEBOOK_REDIRECT_URI")
    params = {
        "client_id": os.getenv("FACEBOOK_APP_ID"),
        "redirect_uri": redirect_uri,
        "client_secret": os.getenv("FACEBOOK_APP_SECRET"),
        "code": code
    }
    token_response = requests.get(token_url, params=params)
    token_data = token_response.json()

    if "access_token" not in token_data:
        return f"Failed to get access token: {token_data.get('error')}", 400

    # Save the access token in session
    session["fb_access_token"] = token_data["access_token"]
    session.modified = True

    # Now fetch events using the token from session
    FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
    events = get_facebook_events(FACEBOOK_PAGE_ID, session.get("fb_access_token"))
    if events is None:
        return jsonify({"error": "Unable to fetch events from Facebook"}), 500
    sorted_events = sort_events_by_date_desc(events)
    upload_events_to_blob(sorted_events)
    
    # Redirect back to index with section=events query parameter.
    return redirect(url_for("index", section="events"))
    
@app.route('/login')
def login():
    print("##### DEBUG ##### In login()")
    session.clear()  # Clear the session
    session["flow"] = _build_auth_code_flow()
    return redirect(session["flow"]["auth_uri"])

@app.route("/dashboard")
@login_required
def dashboard():
    print("##### DEBUG ##### In dashboard()")
    user = session.get("user")
    print(f'##### DEBUG ##### In dashboard() - user:: {user}')
    return f"Hello, {user.name}! <a href='/logout'>Logout</a>"

# Data Deletion Route
@app.route('/delete-data', methods=['GET', 'POST'])
def delete_data():
    if request.method == 'POST':
        email = request.form['email']
        
        # Implement the data deletion logic here
        # Example: Remove the user from Azure Entra ID, or mark the account as deleted
        
        # For demonstration, we'll just print the email
        print(f"Data deletion requested for: {email}")
        
        # Send success message to the template
        return render_template('delete_data.html', message="Your data deletion request has been received.", message_type="success")
    
    return render_template('delete_data.html')

@app.route('/fb-events')
@login_required
def fb_events():
    print("##### DEBUG ##### In fb_events()")
    FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")

    fb_token = session.get("fb_access_token")
    print("##### DEBUG ##### In fb_events() fb_access_token in session:", "fb_access_token" in session)
    events = get_facebook_events(FACEBOOK_PAGE_ID, fb_token)
    if events is None:
        return jsonify({"error": "Unable to fetch events"}), 500

    sorted_events = sort_events_by_date_desc(events)
    return jsonify(sorted_events)

@app.route('/items', methods=['GET'])
def get_items():
    print("##### DEBUG ##### In get_items()")
    result = client.catalog.list_catalog(types='ITEM')
    if result.is_success():
        items = result.body['objects']
        return jsonify(items)
    else:
        return jsonify({'error': 'Unable to fetch items'}), 500

@app.route('/join')
def join():
    print("##### DEBUG ##### In join()")
    application_id = os.getenv('SQUARE_APPLICATION_ID')
    return render_template('index.html', application_id=application_id)

@app.route("/logout")
@login_required
def logout():
    print("##### DEBUG ##### In logout()")
    logout_user()
    session.clear()
    return redirect(f"{AUTHORITY}/oauth2/v2.0/logout?post_logout_redirect_uri=https://test.oviedojeepclub.com")

@app.route('/pay', methods=['GET', 'POST'])
def pay():
    print("##### DEBUG ##### In pay()")
    if request.method == 'POST':
        amount = 5000  # Membership Fee (e.g., $50.00)
        nonce = request.form.get('nonce')
        email = request.form.get('email')
        display_name = request.form.get('displayName')
        password = request.form.get('password')

        # Check if the user already exists
        if user_still_exists(email):
            flash("A user with this email already exists. Please use Login.", "danger")
            # Optionally, you could pass joinVisible=True to keep the join form visible.
            application_id = os.getenv('SQUARE_APPLICATION_ID')
            return render_template('index.html', application_id=application_id, user=current_user, joinVisible=True)
        
        # Process Square Payment
        body = {
            "source_id": nonce,
            "amount_money": {
                "amount": amount,
                "currency": "USD"
            },
            "idempotency_key": os.urandom(12).hex()
        }
        result = client.payments.create_payment(body)
        print("##### DEBUG ##### In pay() result of payment: ", result)
        
        if result.is_success():
            # Extract the receipt URL from the payment response
            receipt_url = result.body.get('payment', {}).get('receipt_url')
            session["receipt_url"] = receipt_url  # Store for later display
            
            flash('Payment Successful! Creating your account...', 'success')
            join_date = int(datetime.now().timestamp())
            expiration_date = compute_expiration_date()  # Your helper function
            
            try:
                created_user = create_b2c_user(email, display_name, password, join_date, expiration_date)
                print("##### DEBUG ##### User created: ", created_user)
                flash('Account created successfully. Please sign in.', 'success')
            except Exception as e:
                flash(f'Error creating account: {e}', 'danger')
                print("##### DEBUG ##### Error creating account:", e)
            
            # Instead of redirecting, re-render the index with join section visible.
            application_id = os.getenv('SQUARE_APPLICATION_ID')
            return render_template('index.html', application_id=application_id, user=current_user, joinVisible=True)
        else:
            flash('Payment Failed. Please try again.', 'danger')
            application_id = os.getenv('SQUARE_APPLICATION_ID')
            return render_template('index.html', application_id=application_id, user=current_user, joinVisible=True)
    
    # For GET requests, simply redirect to the index page.
    return redirect(url_for('index'))
    
# Privacy Policy Route
@app.route('/privacy')
def privacy_policy():
    return render_template('privacy.html')

@app.route('/webhook/square', methods=['POST'])
def square_webhook():
    print("##### DEBUG ##### In square_webhook()")
    event = request.json
    if event['type'] == 'payment.updated':
        payment_status = event['data']['object']['payment']['status']
        if payment_status == 'COMPLETED':
            # Mark user as paid or activate membership
            print("Payment Completed")
    return '', 200

@app.route('/sync-public-events')
def sync_public_events():
    print("##### DEBUG ##### In sync_public_events()")
    # Generate a random state value for CSRF protection and store it in the session
    state = os.urandom(16).hex()
    session['fb_state'] = state

    # Build the Facebook OAuth URL with required parameters
    redirect_uri = os.getenv("FACEBOOK_REDIRECT_URI")  # e.g., "https://test.oviedojeepclub.com/facebook/callback"
    params = {
        "client_id": os.getenv("FACEBOOK_APP_ID"),
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": "pages_read_engagement,pages_read_user_content",
        "response_type": "code"
    }
    query_string = "&".join(f"{key}={quote(str(value))}" for key, value in params.items())
    fb_auth_url = f"https://www.facebook.com/v22.0/dialog/oauth?{query_string}"
    return redirect(fb_auth_url)
    
def _build_auth_code_flow():
    print("##### DEBUG ##### In _build_auth_code_flow()")
    app = msal.ConfidentialClientApplication(
        CLIENT_ID,
        CLIENT_SECRET,
        authority=AUTHORITY
    )
    return app.initiate_auth_code_flow([], redirect_uri=REDIRECT_URI)

def _acquire_token_by_auth_code_flow(flow, args):
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
    # Use the tenant-specific authority for Graph API (not your B2C authority)
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
        
def compute_expiration_date():
    print("##### DEBUG ##### In compute_expiration_date()")
    now = datetime.now()  # Correct: using datetime.now(), not datetime.datetime.now()
    current_year = now.year
    oct_31 = datetime(current_year, 10, 31)
    if now > oct_31:
        # After October 31, expiration is March 31st of the year after next
        expiration = datetime(current_year + 2, 3, 31)
    else:
        # On or before October 31, expiration is March 31st of next year
        expiration = datetime(current_year + 1, 3, 31)
    return int(expiration.timestamp())

def create_b2c_user(email, display_name, password, join_date, expiration_date):
    print("##### DEBUG ##### In create_b2c_user() Attempting to create B2C user with:", email, display_name, join_date, expiration_date)
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
    
    # Normalize email for userPrincipalName
    mail_nickname = email.replace("@", "_at_")
    expected_upn = f"{mail_nickname}@oviedojeepclub.onmicrosoft.com"
    
    user_payload = {
        "accountEnabled": True,
        "displayName": display_name,
        "userPrincipalName": expected_upn,
        "mailNickname": mail_nickname,
        "passwordProfile": {
            "forceChangePasswordNextSignIn": False,  # since user set their own password, they may not need a forced change
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
        # Optionally update custom extension attributes:
        update_payload = {
            "otherMails": [email],
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

def upload_events_to_blob(events):
    print("##### DEBUG ##### In upload_events_to_blob()")
    # Initialize the BlobServiceClient using your connection string.
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not connection_string:
        print("##### DEBUG ##### In upload_events_to_blob() Azure Storage connection string is not set!")
        return
    try:
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    except Exception as e:
        print("Error initializing BlobServiceClient:", e)
        return

    container_name = "events"  # Ensure this container exists in your Azure storage account.
    blob_client = blob_service_client.get_blob_client(container=container_name, blob="events.json")
    events_json = json.dumps(events)
    blob_client.upload_blob(events_json, overwrite=True)
    print("##### DEBUG ##### In upload_events_to_blob() Events successfully uploaded to Azure Blob Storage.")

def user_still_exists(user_id):
    print(f'##### DEBUG ##### In user_still_exists with {user_id}')
    # Acquire an access token for the Microsoft Graph API
    token = _acquire_graph_api_token()
    if not token:
        # If you can't get a token, treat the user as non-existent to be safe.
        return False

    headers = {"Authorization": f"Bearer {token}"}
    graph_url = f"https://graph.microsoft.com/v1.0/users/{user_id}"
    response = requests.get(graph_url, headers=headers)
    
    if response.status_code == 200:
        return True  # User exists
    elif response.status_code == 404:
        return False  # User not found (deleted or does not exist)
    else:
        # Handle other status codes or log for further analysis
        print("Unexpected response from Graph API:", response.status_code, response.text)
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

def sort_events_by_date_desc(events):
    print("##### DEBUG ##### In sort_events_by_date_desc()")
    from datetime import datetime
    # Sort events so that future (newer) events come first (descending order)
    return sorted(
        events,
        key=lambda e: datetime.strptime(e['start_time'], '%Y-%m-%dT%H:%M:%S%z'),
    )
    
class Main(Resource):
    def post(self):
        return jsonify({'message': 'Welcome to the Oviedo Jeep Club Flask REST App'})

api.add_resource(Main, '/')

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

if __name__ == '__main__':
    app.run(debug=True)
