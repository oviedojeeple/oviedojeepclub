from flask import Flask, request, jsonify, render_template, send_from_directory, redirect, url_for, session, flash, redirect
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_restful import Resource, Api
from flask_cors import CORS
from flask_apscheduler import APScheduler
from datetime import datetime
from azure.storage.blob import BlobServiceClient
from azure.data.tables import TableServiceClient, UpdateMode
from azure.communication.email import EmailClient
from square.client import Client
from urllib.parse import quote
from event_uploader import upload_event_data
import msal
import os, time, requests, json, uuid

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
print(f'##### DEBUG ##### SQUARE_ACCESS_TOKEN:: {SQUARE_ACCESS_TOKEN}')
SQUARE_APPLICATION_ID = os.getenv("SQUARE_APPLICATION_ID")
print(f'##### DEBUG ##### SQUARE_APPLICATION_ID:: {SQUARE_APPLICATION_ID}')
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
print(f'##### DEBUG ##### AZURE_STORAGE_CONNECTION_STRING:: {AZURE_STORAGE_CONNECTION_STRING}')
AZURE_COMM_CONNECTION_STRING = os.getenv("AZURE_COMM_CONNECTION_STRING")
print(f'##### DEBUG ##### AZURE_COMM_CONNECTION_STRING:: {AZURE_COMM_CONNECTION_STRING}')
AZURE_COMM_CONNECTION_STRING_SENDER = os.getenv("AZURE_COMM_CONNECTION_STRING_SENDER")
print(f'##### DEBUG ##### AZURE_COMM_CONNECTION_STRING_SENDER:: {AZURE_COMM_CONNECTION_STRING_SENDER}')

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
    
@app.context_processor
def inject_now():
    # Returns a callable function so that in the template you can do now().date()
    return {'now': lambda: datetime.utcnow()}

@app.context_processor
def inject_user_data():
    return {"user_data": session.get("user", {})}

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/x-icon')
@app.before_request
def validate_user_session():
    print("##### DEBUG ##### In validate_user_session()")
    if current_user.is_authenticated:
        # Use the user's email instead of the id for the existence check.
        if not user_still_exists(current_user.email):
            logout_user()
            session.clear()
            flash("Your account is no longer valid. Please log in again.")
            return redirect(url_for("login"))

@app.route('/')
def index():
    print("##### DEBUG ##### In index()")
    application_id = os.getenv('SQUARE_APPLICATION_ID')
    return render_template('index.html', application_id=application_id, user=current_user)

@app.route("/accept_invitation", methods=["GET", "POST"])
def accept_invitation():
    print("##### DEBUG ##### In accept_invitation()")
    # Ignore HEAD requests
    if request.method == "HEAD":
        return ""
        
    token = request.args.get("token") or request.form.get("token")
    print("##### DEBUG ##### In accept_invitation(): Received token:", token)
    invitation = get_invitation(token)
    print("##### DEBUG ##### In accept_invitation(): Retrieved invitation:", invitation)
    
    if not token or not invitation:
        flash("Invalid or expired invitation token.", "danger")
        return redirect(url_for("index"))
    
    if request.method == "POST":
        password = request.form.get("password")
        if not password:
            flash("Password is required.", "danger")
            return render_template("accept_invitation.html", token=token,
                                   family_email=invitation["family_email"],
                                   family_name=invitation["family_name"])
        
        email = invitation["family_email"]
        display_name = invitation["family_name"]
        membership_number = invitation["membership_number"]
        join_date = invitation["member_joined_date"]
        expiration_date = invitation["member_expiration_date"]
        
        try:
            created_user = create_b2c_user(email, display_name, password, membership_number, join_date, expiration_date)
            flash("Family member account created successfully. Please sign in.", "success")
            delete_invitation(token)
            return redirect(url_for("login"))
        except Exception as e:
            flash(f"Error creating family member account: {e}", "danger")
            return render_template("accept_invitation.html", token=token,
                                   family_email=invitation["family_email"],
                                   family_name=invitation["family_name"])
    
    return render_template("accept_invitation.html", token=token,
                           family_email=invitation["family_email"],
                           family_name=invitation["family_name"])

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
        member_joined_raw = user_info.get("extension_MemberJoinedDate")
    
        # Default values in case of conversion issues
        member_expiration = "Not Available"
        member_expiration_iso = None
    
        # Convert the integer timestamp to a date string and ISO format
        if member_expiration_raw:
            try:
                timestamp_int = int(member_expiration_raw)
                if timestamp_int > 1e10:  # Convert from milliseconds if necessary
                    timestamp_int = timestamp_int / 1000
                expiration_date_obj = datetime.fromtimestamp(timestamp_int).date()
                member_expiration = expiration_date_obj.strftime('%B %d, %Y')  # e.g., "March 31, 2025"
                member_expiration_iso = expiration_date_obj.isoformat()         # e.g., "2025-03-31"
                print("##### DEBUG ##### In auth_callback(): Member expiration dates: ", member_expiration, member_expiration_iso)
            except Exception as e:
                print("##### DEBUG ##### In auth_callback() Converting timestamp failed:", e)
                member_expiration = "Invalid Date"
    
        # Safely get the job title (or default)
        job_title = user_info.get("jobTitle", "OJC Member")

        membership_number = user_info.get("extension_MembershipNumber")
    
        # Create the user_data dictionary with all info
        user_data = {
            "user_id": user_info["oid"],
            "name": user_info["name"],
            "email": user_info["emails"][0],
            "membership_number": membership_number,
            "job_title": job_title,
            "member_expiration_date": member_expiration,
            "member_expiration_iso": member_expiration_iso,
            "member_expiration_raw": member_expiration_raw,
            "member_joined_raw": member_joined_raw
        }
    
        # Store the full user_data in session (for template use)
        session["user_data"] = user_data
    
        user_data_for_login = {k: v for k, v in user_data.items() 
                               if k in [
                                   "user_id", "name", "email", "job_title", "membership_number",
                                   "member_expiration_date", "member_expiration_iso", 
                                   "member_expiration_raw", "member_joined_raw"]}
    
        login_user(User(**user_data_for_login), remember=True)
        print("##### DEBUG ##### In auth_callback() Session after login: ", session)
        return redirect(url_for("index"))
    
    return "Login failed", 401

@app.route('/blob-events')
@login_required
def blob_events():
    print("##### DEBUG ##### In blob_events()")
    connection_string = AZURE_STORAGE_CONNECTION_STRING
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
        
from azure.storage.blob import BlobServiceClient
import uuid

@app.route("/create_event", methods=["GET", "POST"])
def create_event():
    print("##### DEBUG ##### In create_event()")
    if request.method == "POST":
        import time
        unique_event_id = "OJC" + str(int(time.time() * 1000))
        
        # Handle file upload for cover image if provided
        cover_image_file = request.files.get("cover_image")
        cover_image_url = None
        if cover_image_file:
            try:
                connection_string = AZURE_STORAGE_CONNECTION_STRING
                blob_service_client = BlobServiceClient.from_connection_string(connection_string)
                container_name = "event-images"  # Ensure this container exists or create it
                # Check if container exists; if not, create it.
                try:
                    container_client = blob_service_client.get_container_client(container_name)
                    container_client.get_container_properties()  # Will raise an exception if not exists
                except Exception:
                    container_client = blob_service_client.create_container(container_name)
                
                # Create a unique blob name using uuid
                file_extension = cover_image_file.filename.rsplit(".", 1)[-1]
                blob_name = f"{unique_event_id}_{uuid.uuid4().hex}.{file_extension}"
                blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
                blob_client.upload_blob(cover_image_file, overwrite=True)
                # Generate the URL for the uploaded image (assuming container is public)
                cover_image_url = blob_client.url
            except Exception as e:
                print("Error uploading cover image:", e)
                flash("Error uploading cover image.", "danger")
                return redirect(url_for("create_event"))
        
        # Build the event data; ignore the 'id' field from the form.
        event = {
            "id": unique_event_id,
            "name": request.form.get("name", "").strip(),
            "description": request.form.get("description", "").strip(),
            "start_time": request.form.get("start_time", "").strip(),
            "end_time": request.form.get("end_time", "").strip() or None,
            "place": {
                "name": request.form.get("place_name", "").strip(),
                "location": {
                    "city": request.form.get("city", "").strip(),
                    "country": request.form.get("country", "").strip(),
                    "latitude": float(request.form.get("latitude", 0)),
                    "longitude": float(request.form.get("longitude", 0)),
                    "state": request.form.get("state", "").strip(),
                    "street": request.form.get("street", "").strip() or None,
                    "zip": request.form.get("zip", "").strip() or None,
                },
                "id": request.form.get("place_id", "").strip() or None,
            },
            "cover": {
                "offset_x": int(request.form.get("offset_x", 0)),
                "offset_y": int(request.form.get("offset_y", 0)),
                # Use the uploaded image URL if available, otherwise use the URL from the form.
                "source": cover_image_url or request.form.get("cover_source", "").strip(),
                "id": request.form.get("cover_id", "").strip() or None,
            },
        }
        
        # Load existing events from the blob, append new event, then re-upload.
        events_list = get_events_from_blob()  # your helper function to retrieve events
        events_list.append(event)
        success, message = upload_events_to_blob(events_list)
        if success:
            flash(message, "success")
        else:
            flash(message, "danger")
        # Redirect back to index with section=events query parameter.
        return redirect(url_for("index", section="events"))
    
    return render_template("create_event.html")

@app.route('/delete_event/<event_id>', methods=['POST'])
@login_required
def delete_event(event_id):
    print("##### DEBUG ##### In delete_event()")
    # Only allow board members to delete events.
    if current_user.job_title != 'OJC Board Member':
        flash("You are not authorized to delete events.", "danger")
        return redirect(url_for("index"))
    
    # Load the existing events from the blob.
    events_list = get_events_from_blob()  # Your helper function
    
    # Filter out the event with the given ID.
    new_events_list = [event for event in events_list if event.get("id") != event_id]
    
    if len(new_events_list) == len(events_list):
        flash("Event not found.", "warning")
        return redirect(url_for("index", section="events"))
    
    # Upload the updated list back to the blob.
    success, message = upload_events_to_blob(new_events_list)
    if success:
        flash("Event deleted successfully.", "success")
    else:
        flash("Error deleting event: " + message, "danger")
    
    return redirect(url_for("index", section="events"))

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

    session["fb_access_token"] = token_data["access_token"]
    session.modified = True

    FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
    fb_events = get_facebook_events(FACEBOOK_PAGE_ID, session.get("fb_access_token"))
    if fb_events is None:
        return jsonify({"error": "Unable to fetch events from Facebook"}), 500

    # Sort the Facebook events if needed
    sorted_facebook_events = sort_events_by_date_desc(fb_events)

    # Load the current events from the blob
    existing_events = get_events_from_blob()
    # Filter to keep only custom events (those with IDs starting with "OJC")
    custom_events = [ev for ev in existing_events if ev.get("id", "").startswith("OJC")]
    # Combine custom events with the newly fetched Facebook events
    combined_events = custom_events + sorted_facebook_events
    # Optionally, sort the combined events list by start time descending
    combined_events = sort_events_by_date_desc(combined_events)
    
    # Upload the combined list back to the blob
    success, message = upload_events_to_blob(combined_events)
    if not success:
        return jsonify({"error": message}), 500

    # Redirect back to index with section=events query parameter.
    return redirect(url_for("index", section="events"))

@app.route('/family-members', methods=['GET'])
@login_required
def family_members():
    print("##### DEBUG ##### In family_members()")
    membership_number = current_user.membership_number
    graph_token = _acquire_graph_api_token()
    if not graph_token:
        return jsonify({"error": "Unable to acquire Graph API token"}), 500

    headers = {"Authorization": f"Bearer {graph_token}"}
    # Construct a filter query: find users with the same membership number,
    # excluding the primary member. Adjust the attribute name to your custom attribute.
    # Build filter using the full property name
    # Only filter on the membership number because the 'ne' operator is not supported.
    filter_clause = f"(extension_b32ce28f40e2412fb56abae06a1ac8ab_MembershipNumber eq '{membership_number}')"
    print("##### DEBUG ##### In family_members() filter_clause", filter_clause)
    params = {
        "$select": "id,displayName,mailNickName,userPrincipalName,extension_b32ce28f40e2412fb56abae06a1ac8ab_MembershipNumber",
        "$filter": filter_clause
    }
    print("##### DEBUG ##### In family_members() params", params)
    url = "https://graph.microsoft.com/v1.0/users"
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json().get("value", [])
        # Manually filter out the current user's record.
        current_user_upn = f"{current_user.email.replace('@', '_at_')}@oviedojeepclub.onmicrosoft.com"
        data = [user for user in data if user.get("userPrincipalName") != current_user_upn]
        print("##### DEBUG ##### In family_members() family member user data: ", data)
        return jsonify(data)
    else:
        print("Graph API error:", response.text)
        return jsonify({"error": "Failed to fetch family members"}), response.status_code
        
@app.route('/login')
def login():
    print("##### DEBUG ##### In login()")
    session.clear()  # Clear the session
    session["flow"] = _build_auth_code_flow()
    return redirect(session["flow"]["auth_uri"])

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

@app.route('/invite_family', methods=['GET', 'POST'])
@login_required
def invite_family():
    print("##### DEBUG ##### In invite_family()")
    if request.method == 'POST':
        family_email = request.form.get('family_email')
        family_name = request.form.get('family_name')
    if not family_email or not family_name:
        return jsonify({"error": "Missing family name or email"}), 400

    token = uuid.uuid4().hex
    print("##### DEBUG ##### In invite_family(): token", token)

    # Use the current user's membership details.
    membership_number = current_user.membership_number
    member_joined_date = current_user.member_joined_raw
    member_expiration_date = current_user.member_expiration_raw

    # Store invitation details in database
    invitation_data = {
        "family_email": family_email,
        "family_name": family_name,
        "membership_number": membership_number,
        "member_joined_date": member_joined_date,
        "member_expiration_date": member_expiration_date
    }

    print("##### DEBUG ##### In invite_family(): invitation_data", invitation_data)

    store_invitation(token, invitation_data)
    
    invitation_link = url_for("accept_invitation", token=token, _external=True)
    print("##### DEBUG ##### In invite_family(): invitation_link", invitation_link)
    send_family_invitation_email(family_email, family_name, invitation_link)
    
    return jsonify({"message": "Invitation sent successfully!"})

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
            # Generate membership details: membership number, join date, expiration date
            membership_number, join_date, expiration_date = create_membership_details()
            
            try:
                created_user = create_b2c_user(email, display_name, password, membership_number, join_date, expiration_date)
                print("##### DEBUG ##### User created: ", created_user)
                send_new_membership_email(email, display_name, receipt_url)
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

@app.route('/renew-membership', methods=['POST'])
def renew_membership():
    print("##### DEBUG ##### In renew_membership()")
    data = request.get_json()
    print("##### DEBUG ##### In renew_membership() Received JSON:", data)
    nonce = data.get("nonce")
    print("##### DEBUG ##### In renew_membership() Received nonce:", nonce)
    if not nonce:
        # Return a JSON error if no nonce is provided
        flash('Missing card information.', 'danger')
        return jsonify(success=False, message="Missing card information"), 400

    user = session.get('user')
    if not current_user.is_authenticated:
        # Instead of a redirect, return a JSON error
        flash('User not authenticated.', 'danger')
        return jsonify(success=False, message="User not authenticated"), 401

    # Process Square Payment
    amount = 3000  # Membership Fee (e.g., $30.00)
    body = {
        "source_id": nonce,
        "amount_money": {
            "amount": amount,
            "currency": "USD"
        },
        "idempotency_key": os.urandom(12).hex()
    }
    result = client.payments.create_payment(body)
    print("##### DEBUG ##### In renew_membership() result of payment: ", result)
    if result.is_success():
        # Payment processed successfully, update membership
        receipt_url = result.body.get('payment', {}).get('receipt_url')
        session["receipt_url"] = receipt_url  # Store for later display
        new_expiration_date = compute_expiration_date()  # Ensure this returns a timestamp string
        azure_ad_b2c_api_url = f"https://graph.microsoft.com/v1.0/users/{current_user.id}"
        update_payload = {"extension_b32ce28f40e2412fb56abae06a1ac8ab_MemberExpirationDate": new_expiration_date}
        
        # Acquire a Graph API token (using your helper function)
        graph_token = _acquire_graph_api_token()
        if not graph_token:
            flash('Payment succeeded but failed to update membership. Share error with Administrator. Graph Token missing.', 'danger')
            return jsonify(success=False, message="Failed to acquire Graph API token"), 500
        
        graph_headers = {
            "Authorization": f"Bearer {graph_token}",
            "Content-Type": "application/json"
        }
        
        # Query all users sharing the same Membership Number
        membership_number = current_user.membership_number
        filter_clause = f"(extension_b32ce28f40e2412fb56abae06a1ac8ab_MembershipNumber eq '{membership_number}')"
        params = {
            "$select": "id,displayName,extension_b32ce28f40e2412fb56abae06a1ac8ab_MembershipNumber",
            "$filter": filter_clause
        }
        url = "https://graph.microsoft.com/v1.0/users"
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            users = response.json().get("value", [])
            print("##### DEBUG ##### In renew_membership() Found users for renewal:", users)
            # Loop through each user and update the MemberExpirationDate
            for user in users:
                user_id = user["id"]
                patch_url = f"https://graph.microsoft.com/v1.0/users/{user_id}"
                patch_payload = {
                    "extension_b32ce28f40e2412fb56abae06a1ac8ab_MemberExpirationDate": new_expiration_date
                }
                patch_response = requests.patch(patch_url, headers=headers, json=patch_payload)
                if patch_response.status_code not in [200, 204]:
                    print(f"Error updating user {user_id}: {patch_response.text}")
                    # Optionally, log the error for further handling.
            # Update the session for the current user.
            try:
                # For display purposes, convert the timestamp to a human-readable date.
                ts = int(new_expiration_date)
                if ts > 1e10:  # if in milliseconds
                    ts = ts / 1000
                expiration_date_obj = datetime.fromtimestamp(ts).date()
                member_expiration = expiration_date_obj.strftime('%B %d, %Y')
                member_expiration_iso = expiration_date_obj.isoformat()
            except Exception as e:
                print("Error converting new expiration date:", e)
                member_expiration = "Invalid Date"
                member_expiration_iso = "Invalid Date"
            session["user_data"]["member_expiration_date"] = member_expiration
            session["user_data"]["member_expiration_iso"] = member_expiration_iso

            flash('Payment Successful! Your renewal has been updated for all members.', 'success')
            return jsonify(success=True, message="Membership renewed successfully")
        else:
            send_membership_renewal_email(current_user.email, current_user.name)
            flash('Payment succeeded but failed to update membership. Share error with Administrator.', 'danger')
            return jsonify(success=False, message="Payment succeeded but failed to update membership"), 500
    else:
        flash('Payment failed. Share error with Administrator.', 'danger')
        return jsonify(success=False, message="Payment failed"), 400
        
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

@app.template_filter('to_date')
def to_date_filter(value, format="%Y-%m-%d"):
    print("##### DEBUG ##### In to_date_filter()")
    try:
        return datetime.strptime(value, format).date()
    except Exception as e:
        print("Error in to_date filter:", e)
        return None

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
        
def check_membership_expiration():
    print("##### DEBUG ##### In check_membership_expiration()")
    today = datetime.today().date()
    # Replace get_all_users() with your actual function to retrieve user data
    users = get_all_users()  
    for user in users:
        expiration_str = user.get("member_expiration_iso")
        if expiration_str:
            expiration_date = datetime.strptime(expiration_str, "%Y-%m-%d").date()
            days_left = (expiration_date - today).days
            if days_left in [90, 60, 30, 15, 1]:
                send_disablement_reminder_email(user['email'], user['name'], days_left)

# Initialize and start the scheduler in your app initialization section
scheduler = APScheduler()
scheduler.add_job(func=check_membership_expiration, trigger="interval", days=1, id="expiration_check")
scheduler.start()

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
    # Generate a unique 13-digit timestamp and prefix it with "OJC"
    membership_number = "OJC" + str(int(time.time() * 1000))
    # Use the current timestamp for join date (in seconds)
    join_date = int(datetime.now().timestamp())
    # Compute the expiration date using your helper function
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
    """
    Retrieves all users from Microsoft Graph API with selected fields.
    Returns:
        A list of dictionaries, each representing a user.
    """
    token = _acquire_graph_api_token()
    if not token:
        print("Error: Could not acquire Graph API token.")
        return []
    
    headers = {"Authorization": f"Bearer {token}"}
    # Select the fields that are relevant for membership checks:
    # id, displayName, mail, and the custom membership expiration attribute.
    select_fields = "id,displayName,mail,extension_b32ce28f40e2412fb56abae06a1ac8ab_MemberExpirationDate"
    url = f"https://graph.microsoft.com/v1.0/users?$select={select_fields}"
    
    users = []
    while url:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            users.extend(data.get("value", []))
            # Check if there is a nextLink for pagination
            url = data.get("@odata.nextLink")
        else:
            print(f"Error fetching users: {response.status_code} {response.text}")
            break

    return users

def get_events_from_blob():
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
        return events
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

    container_name = "events"  # Ensure this container exists in your Azure storage account.
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
    # Checks if a user with the expected userPrincipalName exists.
    token = _acquire_graph_api_token()
    if not token:
        # For safety, if we cannot get a token, assume user does not exist.
        return False
    headers = {"Authorization": f"Bearer {token}"}
    # Compute expected UPN: replace "@" with "_at_" and append your domain.
    mail_nickname = email.replace("@", "_at_")
    expected_upn = f"{mail_nickname}@oviedojeepclub.onmicrosoft.com"
    
    # Construct a filter query for userPrincipalName.
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

# Function to check if the user can renew
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
        # Convert entity to a dictionary if needed
        return dict(entity)
    except Exception as e:
        print("Error retrieving invitation:", e)
        return None

def parse_date(date_str):
    print("##### DEBUG ##### In parse_date()")
    from datetime import datetime, timezone
    # List of potential formats
    formats = ['%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%dT%H:%M']
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            # If the datetime is aware, convert it to UTC and make it naive
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        except ValueError:
            continue
    raise ValueError("No valid date format found for: " + date_str)

def sort_events_by_date_desc(events):
    print("##### DEBUG ##### In sort_events_by_date_desc()")
    # Sort events so that future (newer) events come first (descending order)
    return sorted(
        events,
        key=lambda e: parse_date(e['start_time']),
        # disabling revers - reverse=True
    )

def send_disablement_reminder_email(recipient_email, recipient_name, days_left):
    print("##### DEBUG ##### In send_disablement_reminder_email()")
    email_client = EmailClient.from_connection_string(AZURE_COMM_CONNECTION_STRING)
    try:
        response = email_client.send(
            sender=AZURE_COMM_CONNECTION_STRING_SENDER,
            content={
                "subject": "Membership Expiration Reminder",
                "plainText": (
                    f"Hello {recipient_name},\n\n"
                    f"Your membership is set to expire in {days_left} day(s). "
                    "Please renew your membership to continue enjoying Oviedo Jeep Club benefits."
                ),
                "html": (
                    f"<html><body><h1>Membership Expiration Reminder</h1>"
                    f"<p>Hello {recipient_name},</p>"
                    f"<p>Your membership is set to expire in <strong>{days_left}</strong> day(s). "
                    "Please renew your membership to continue enjoying Oviedo Jeep Club benefits.</p>"
                    f"</body></html>"
                )
            },
            recipients={
                "to": [
                    {"address": recipient_email, "displayName": recipient_name}
                ]
            }
        )
        print("Disablement reminder email sent!", response)
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
        result = poller.result()  # Wait for the operation to complete.
        flash("Family member invite sent successfully.", "success")
        print("##### DEBUG ##### In send_family_invitation_email() Invitation email sent! Result:", result)
    except Exception as e:
        flash("Family member invite failed to be sent.", "danger")
        print("Error sending family invitation email:", e)

def send_membership_renewal_email(recipient_email, recipient_name):
    print("##### DEBUG ##### In send_membership_renewal_email()")
    email_client = EmailClient.from_connection_string(AZURE_COMM_CONNECTION_STRING)
    try:
        response = email_client.send(
            sender=AZURE_COMM_CONNECTION_STRING_SENDER,
            content={
                "subject": "Membership Renewal Confirmation",
                "plainText": "Your membership has been renewed successfully!",
                "html": (
                    "<html><body><h1>Membership Renewal Confirmation</h1>"
                    "<p>Your membership has been renewed successfully!</p>"
                    "</body></html>"
                )
            },
            recipients={
                "to": [
                    {"address": recipient_email, "displayName": recipient_name}
                ]
            }
        )
        print("Membership renewal email sent!", response)
    except Exception as e:
        print("Error sending renewal email:", e)

def send_new_membership_email(recipient_email, recipient_name, receipt_url):
    print("##### DEBUG ##### In send_new_membership_email()")
    email_client = EmailClient.from_connection_string(AZURE_COMM_CONNECTION_STRING)
    try:
        response = email_client.send(
            sender=AZURE_COMM_CONNECTION_STRING_SENDER,  # your verified sender
            content={
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
            recipients={
                "to": [
                    {"address": recipient_email, "displayName": recipient_name}
                ]
            }
        )
        print("New membership email sent!", response)
    except Exception as e:
        print("Error sending new membership email:", e)

def store_invitation(token, data, expire_seconds=3600):
    print("##### DEBUG ##### In store_invitation()")
    # Construct the entity. Using token as both PartitionKey and RowKey.
    entity = {
        "PartitionKey": token,
        "RowKey": token,
        **data,
        # Optionally, add a CreatedAt field for expiration logic
        "CreatedAt": datetime.utcnow().isoformat()
    }
    table_client.upsert_entity(entity=entity, mode=UpdateMode.REPLACE)

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
