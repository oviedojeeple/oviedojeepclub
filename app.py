from flask import Flask, request, jsonify, render_template, send_from_directory, redirect, url_for, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user  # Import current_user
from flask_restful import Resource, Api
from flask_cors import CORS
import msal
import os, time, requests

# Initialize Flask App
app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secure session key (random per restart)
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

login_manager = LoginManager()
login_manager.init_app(app)

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
    user_data = session.get("user")
    if user_data and user_data.get("user_id") == user_id:
        print(f'##### DEBUG ##### Session user data: {user_data}')
        return User(**user_data)
    return None

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
        # Create a dictionary for session storage
        user_data = {
            "user_id": user_info["oid"],
            "name": user_info["name"],
            "email": user_info["emails"][0]
        }
        session["user"] = user_data
        # Pass a new User instance to login_user if needed by Flask-Login
        login_user(User(**user_data), remember=True)
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

# Privacy Policy Route
@app.route('/privacy')
def privacy_policy():
    return render_template('privacy.html')

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
