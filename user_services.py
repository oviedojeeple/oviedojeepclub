"""
User services module: provides operations around Azure B2C user data, including:
  - Fetching all users with membership expiration via Microsoft Graph
  - Computing standard membership expiration dates
  - Generating membership details (number, join date, expiration)
  - Creating B2C users and updating their extension attributes
  - Scheduled job to check and email users about upcoming expiration
"""
import time
import msal
import requests
from datetime import datetime
from config import Config

def _acquire_graph_api_token():
    authority_url = f"https://login.microsoftonline.com/{Config.TENANT_ID}"
    app = msal.ConfidentialClientApplication(
        Config.CLIENT_ID,
        client_credential=Config.CLIENT_SECRET,
        authority=authority_url
    )
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    return result.get("access_token")

def get_all_users():
    """
    Fetch all users from Microsoft Graph with membership expiration.
    """
    token = _acquire_graph_api_token()
    if not token:
        return []
    headers = {"Authorization": f"Bearer {token}"}
    select_fields = (
        "id,displayName,mailNickname,"
        "extension_b32ce28f40e2412fb56abae06a1ac8ab_MemberExpirationDate"
    )
    url = f"https://graph.microsoft.com/v1.0/users?$select={select_fields}"
    users = []
    while url:
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            break
        data = resp.json()
        users.extend(data.get("value", []))
        url = data.get("@odata.nextLink")
    return users

def compute_expiration_date():
    """
    Compute expiration timestamp (Mar 31 next year or year after).
    """
    now = datetime.now()
    year = now.year
    oct_31 = datetime(year, 10, 31)
    if now > oct_31:
        exp = datetime(year + 2, 3, 31)
    else:
        exp = datetime(year + 1, 3, 31)
    return int(exp.timestamp())

def create_membership_details():
    """
    Generate unique membership number, join date, and expiration.
    """
    membership_number = "OJC" + str(int(time.time() * 1000))
    join_date = int(datetime.now().timestamp())
    expiration_date = compute_expiration_date()
    return membership_number, join_date, expiration_date

def create_b2c_user(email, display_name, password,
                    membership_number, join_date, expiration_date):
    """
    Create a user in Azure B2C via Microsoft Graph.
    """
    token = _acquire_graph_api_token()
    if not token:
        raise RuntimeError("Unable to acquire Graph API token")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    mail_nickname = email.replace("@", "_at_")
    upn = f"{mail_nickname}@oviedojeepclub.onmicrosoft.com"
    user_payload = {
        "accountEnabled": True,
        "displayName": display_name,
        "userPrincipalName": upn,
        "mailNickname": mail_nickname,
        "passwordProfile": {"forceChangePasswordNextSignIn": False, "password": password},
        "identities": [{
            "signInType": "emailAddress",
            "issuer": "oviedojeepclub.onmicrosoft.com",
            "issuerAssignedId": email
        }]
    }
    resp = requests.post("https://graph.microsoft.com/v1.0/users", headers=headers, json=user_payload)
    if resp.status_code != 201:
        raise RuntimeError(f"Error creating user: {resp.text}")
    created = resp.json()
    update_payload = {
        "otherMails": [email],
        "extension_b32ce28f40e2412fb56abae06a1ac8ab_MembershipNumber": membership_number,
        "extension_b32ce28f40e2412fb56abae06a1ac8ab_MemberJoinedDate": join_date,
        "extension_b32ce28f40e2412fb56abae06a1ac8ab_MemberExpirationDate": expiration_date
    }
    upd = requests.patch(
        f"https://graph.microsoft.com/v1.0/users/{created['id']}",
        headers=headers,
        json=update_payload
    )
    if upd.status_code not in (200, 204):
        raise RuntimeError(f"Error updating custom attributes: {upd.text}")
    return created
  
def check_membership_expiration():
    """
    Scheduled job: send membership expiration reminder emails.
    Fetches all users, computes days until expiration, and emails them when
    their membership expires in 15, 8, or 1 days.
    """
    from datetime import datetime as _dt
    from emails import send_disablement_reminder_email
    # Get all users with expiration data
    users = get_all_users()
    today = _dt.utcnow().date()
    for user in users:
        # Extract raw expiration timestamp
        exp_raw = user.get('extension_b32ce28f40e2412fb56abae06a1ac8ab_MemberExpirationDate')
        if not exp_raw:
            continue
        # Normalize to seconds
        ts = exp_raw / 1000 if exp_raw > 1e10 else exp_raw
        try:
            exp_date = _dt.fromtimestamp(ts).date()
        except Exception:
            continue
        days_left = (exp_date - today).days
        if days_left in (15, 8, 1):
            # Prepare recipient info
            recipient = user.get('mailNickname', '').replace('_at_', '@')
            name = user.get('displayName', 'Member')
            send_disablement_reminder_email(recipient, name, days_left)