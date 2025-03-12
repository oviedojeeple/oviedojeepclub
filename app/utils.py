# app/utils.py
import os
import msal
import time
from datetime import datetime

def build_auth_code_flow():
    """Builds the MSAL auth code flow."""
    authority = f"{os.getenv('AZURE_AUTHORITY')}/{os.getenv('AZURE_POLICY')}"
    app = msal.ConfidentialClientApplication(
        os.getenv("AZURE_CLIENT_ID"),
        client_credential=os.getenv("AZURE_CLIENT_SECRET"),
        authority=authority
    )
    return app.initiate_auth_code_flow([], redirect_uri=os.getenv("AZURE_REDIRECT_URI"))

def compute_expiration_date():
    """Compute membership expiration date based on the current date."""
    now = datetime.now()
    current_year = now.year
    oct_31 = datetime(current_year, 10, 31)
    if now > oct_31:
        expiration = datetime(current_year + 2, 3, 31)
    else:
        expiration = datetime(current_year + 1, 3, 31)
    return int(expiration.timestamp())

# Add additional helper functions as needed…
