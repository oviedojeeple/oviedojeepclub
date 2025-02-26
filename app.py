from flask import Flask, request, jsonify, render_template, send_from_directory, redirect, url_for, session, flash, redirect
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user  # Import current_user
from flask_restful import Resource, Api
from flask_cors import CORS
from datetime import datetime
from square.client import Client
import msal
import os, time, requests

# Initialize Flask App
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")  # Secure session key (random per restart)
CORS(app)
api = Api(app)

app.config['PROPAGATE_EXCEPTIONS'] = True
app.config['DEBUG'] = True

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
    def __init__(self, user_id, name, email):
        print(f'##### DEBUG ##### In User class with {self} and {user_id} and {name} and {email}')
        self.id = user_id
        self.name = name
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    print(f'##### DEBUG ##### In load_user with {user_id}')
    print("##### DEBUG ##### In load_user with Full session:", dict(session))
    user_data = session.get("user")
    if user_data and user_data.get("user_id") == user_id:
        print(f'##### DEBUG ##### Session user data: {user_data}')
        return User(**user_data)
    return None

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
    return render_template('index.html', user=current_user)  # Pass current_user to the template

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

        # Retrieve the raw custom attribute value
        member_expiration_raw = user_info.get("extension_b32ce28f40e2412fb56abae06a1ac8ab_MemberExpirationDate")
        
        # Convert the integer timestamp to a date string.
        # If the timestamp is in milliseconds, divide by 1000. Adjust as necessary.
        if member_expiration_raw:
            try:
                timestamp_int = int(member_expiration_raw)
                # Check if the timestamp seems to be in milliseconds
                if timestamp_int > 1e10:
                    timestamp_int = timestamp_int / 1000
                member_expiration = datetime.fromtimestamp(timestamp_int).strftime('%Y-%m-%d')
            except Exception as e:
                print("Error converting timestamp:", e)
                member_expiration = "Invalid Date"
        else:
            member_expiration = "Not Available"
        
        # Create the user_data dictionary including the formatted expiration date
        user_data = {
            "user_id": user_info["oid"],
            "name": user_info["name"],
            "email": user_info["emails"][0],
            "member_expiration_date": member_expiration
        }
        session["user"] = user_data
        
        # Pass a new User instance to login_user if needed by Flask-Login
        login_user(User(**user_data), remember=True)
        print("##### DEBUG ##### In auth_callback() Session after login: ", session)
        return redirect(url_for("index"))
    
    return "Login failed", 401

@app.route('/login')
def login():
    print("##### DEBUG ##### In login()")
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
        body = {
            "source_id": request.form['nonce'],
            "amount_money": {
                "amount": amount,
                "currency": "USD"
            },
            "idempotency_key": os.urandom(12).hex()
        }
        result = client.payments.create_payment(body)
        
        if result.is_success():
            flash('Payment Successful! Welcome to Oviedo Jeep Club.', 'success')
            return redirect(url_for('profile'))
        else:
            flash('Payment Failed. Please try again.', 'danger')
    
    # Pass Application ID to the template
    return render_template('pay.html', application_id=SQUARE_APPLICATION_ID)

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
