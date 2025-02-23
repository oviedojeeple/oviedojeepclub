from flask import Flask, request, jsonify, render_template, send_from_directory, redirect, url_for, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
from flask_restful import Resource, Api
from flask_cors import CORS
import msal
import os, time, requests, logging, sys

# Initialize Flask App
app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secure session key (random per restart)
CORS(app)
api = Api(app)

# Set up logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Log to stdout for Azure App Service Log Stream
    ]
)

logger = logging.getLogger(__name__)
logger.debug("Flask app has started.")

# Azure Entra ID Config (Using Environment Variables)
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
TENANT_ID = os.getenv("AZURE_TENANT_ID")
REDIRECT_URI = os.getenv("AZURE_REDIRECT_URI", "https://test.oviedojeepclub.com/auth/callback")
AZURE_POLICY = os.getenv("AZURE_POLICY")
SCOPES = ["User.Read"]
AUTHORITY = f"https://oviedojeepclub.b2clogin.com/{AZURE_POLICY}"
LOGIN_URL = f"{AUTHORITY}/oauth2/v2.0/authorize"
TOKEN_URL = f"{AUTHORITY}/oauth2/v2.0/token"

login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin):
    logger.info(f'In User class with {UserMixin}')
    def __init__(self, user_id, name, email):
        logger.info(f'In User class with {self} and {user_id} and {name} and {email}')
        self.id = user_id
        self.name = name
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    logger.info(f'In load_user with {user_id}')
    return session.get("user")

@app.route('/')
def index():
    logger.info("In index()")
    return render_template('index.html')

@app.route('/login')
def login():
    logger.info("In login()")
    session["flow"] = _build_auth_code_flow()
    return redirect(session["flow"]["auth_uri"])

@app.route('/auth/callback')
def auth_callback():
    logger.info("In auth_callback()")
    if request.args.get("error"):
        return f"Error: {request.args['error']} - {request.args.get('error_description')}"

    result = _acquire_token_by_auth_code_flow(session.get("flow"), request.args)
    if "access_token" in result:
        user_info = _get_user_info(result["access_token"])
        session["user"] = User(user_info["id"], user_info["displayName"], user_info["mail"])
        login_user(session["user"])
        return redirect(url_for("dashboard"))

    return "Login failed", 401

@app.route("/dashboard")
@login_required
def dashboard():
    logger.info("In dashboard()")
    user = session.get("user")
    return f"Hello, {user.name}! <a href='/logout'>Logout</a>"

@app.route("/logout")
@login_required
def logout():
    logger.info("In logout()")
    logout_user()
    session.clear()
    return redirect(f"{AUTHORITY}/oauth2/v2.0/logout?post_logout_redirect_uri=https://test.oviedojeepclub.com")

def _build_auth_code_flow():
    logger.info("In _build_auth_code_flow()")
    app = msal.ConfidentialClientApplication(CLIENT_ID, CLIENT_SECRET, authority=AUTHORITY)
    return app.initiate_auth_code_flow(SCOPES, REDIRECT_URI)

def _acquire_token_by_auth_code_flow(flow, args):
    logger.info(f'In _acquire_token_by_auth_code_flow with {flow} and {args}')
    app = msal.ConfidentialClientApplication(CLIENT_ID, CLIENT_SECRET, authority=AUTHORITY)
    return app.acquire_token_by_auth_code_flow(flow, args)

def _get_user_info(access_token):
    logger.info(f'In _get_user_info with {access_token}')
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers)
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
