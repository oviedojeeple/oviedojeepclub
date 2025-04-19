"""
Authentication blueprint: routes for user login, logout, and session management using Azure AD B2C.
"""
from flask import Blueprint, request, session, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user
from urllib.parse import quote
import msal, requests, os
from datetime import datetime
from config import Config

# Blueprint for authentication routes and user session management
auth_bp = Blueprint('auth', __name__)
# Flask-Login manager instance
login_manager = LoginManager()

class User(UserMixin):
    def __init__(self, user_id, name, email, membership_number=None,
                 job_title=None, member_expiration_date=None,
                 member_expiration_iso=None, member_expiration_raw=None,
                 member_joined_raw=None):
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
    # Load user_data from session and rebuild User
    user_data = session.get("user_data", {})
    if user_data and user_data.get("user_id") == user_id:
        return User(
            user_id=user_data.get("user_id"),
            name=user_data.get("name"),
            email=user_data.get("email"),
            membership_number=user_data.get("membership_number"),
            job_title=user_data.get("job_title"),
            member_expiration_date=user_data.get("member_expiration_date"),
            member_expiration_iso=user_data.get("member_expiration_iso"),
            member_expiration_raw=user_data.get("member_expiration_raw"),
            member_joined_raw=user_data.get("member_joined_raw")
        )
    return None

def _build_auth_code_flow():
    app_msal = msal.ConfidentialClientApplication(
        Config.CLIENT_ID,
        client_credential=Config.CLIENT_SECRET,
        authority=Config.AUTHORITY
    )
    return app_msal.initiate_auth_code_flow([], redirect_uri=Config.REDIRECT_URI)

def _acquire_token_by_auth_code_flow(flow, args):
    app_msal = msal.ConfidentialClientApplication(
        Config.CLIENT_ID,
        client_credential=Config.CLIENT_SECRET,
        authority=Config.AUTHORITY
    )
    result = app_msal.acquire_token_by_auth_code_flow(flow, args)
    if "id_token" in result:
        return result.get("id_token_claims")
    return None

def _acquire_graph_api_token():
    authority_url = Config.AZURE_AUTHORITY
    app_msal = msal.ConfidentialClientApplication(
        Config.CLIENT_ID,
        client_credential=Config.CLIENT_SECRET,
        authority=authority_url
    )
    result = app_msal.acquire_token_for_client(
        scopes=["https://graph.microsoft.com/.default"]
    )
    return result.get("access_token")

def user_still_exists(email):
    token = _acquire_graph_api_token()
    if not token:
        return False
    headers = {"Authorization": f"Bearer {token}"}
    mail_nickname = email.replace("@", "_at_")
    expected_upn = f"{mail_nickname}@oviedojeepclub.onmicrosoft.com"
    filter_query = f"userPrincipalName eq '{expected_upn}'"
    url = f"https://graph.microsoft.com/v1.0/users?$filter={quote(filter_query)}"
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        return bool(data.get("value"))
    return False

@auth_bp.before_app_request
def validate_user_session():
    if current_user.is_authenticated:
        if not user_still_exists(current_user.email):
            logout_user()
            session.clear()
            flash("Your account is no longer valid. Please log in again.")
            return redirect(url_for('auth.login'))

@auth_bp.route('/login')
def login():
    session.clear()
    session["flow"] = _build_auth_code_flow()
    return redirect(session["flow"]["auth_uri"])

@auth_bp.route('/auth/callback')
def auth_callback():
    flow = session.get("flow")
    if not flow:
        return redirect(url_for('auth.login'))
    result = _acquire_token_by_auth_code_flow(flow, request.args)
    if not result:
        return "Login failed", 401
    user_info = result
    # Extract membership expiration info
    member_expiration_raw = user_info.get("extension_MemberExpirationDate")
    member_joined_raw = user_info.get("extension_MemberJoinedDate")
    member_expiration = None
    member_expiration_iso = None
    if member_expiration_raw:
        try:
            ts = int(member_expiration_raw)
            if ts > 1e10:
                ts /= 1000
            dt = datetime.fromtimestamp(ts).date()
            member_expiration = dt.strftime('%B %d, %Y')
            member_expiration_iso = dt.isoformat()
        except Exception:
            member_expiration = None
            member_expiration_iso = None
    job_title = user_info.get("jobTitle")
    membership_number = user_info.get("extension_MembershipNumber")
    user_data = {
        "user_id": user_info.get("oid"),
        "name": user_info.get("name"),
        "email": user_info.get("emails", [None])[0],
        "membership_number": membership_number,
        "job_title": job_title,
        "member_expiration_date": member_expiration,
        "member_expiration_iso": member_expiration_iso,
        "member_expiration_raw": member_expiration_raw,
        "member_joined_raw": member_joined_raw
    }
    session["user_data"] = user_data
    user_for_login = {
        k: user_data[k] for k in [
            "user_id", "name", "email", "job_title",
            "membership_number", "member_expiration_date",
            "member_expiration_iso", "member_expiration_raw",
            "member_joined_raw"
        ] if k in user_data
    }
    login_user(User(**user_for_login), remember=True)
    return redirect(url_for('index'))

@auth_bp.route('/logout')
def logout():
    logout_user()
    session.clear()
    return redirect(f"{Config.AUTHORITY}/oauth2/v2.0/logout?post_logout_redirect_uri={Config.REDIRECT_URI}")