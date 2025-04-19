import os

def _env(key, required=True, default=None):
    """
    Helper to read environment variable or raise if missing.
    """
    val = os.getenv(key, default)
    if required and (val is None or val == ""):
        raise RuntimeError(f"Missing required environment variable: {key}")
    return val

class Config:
    # Flask settings
    SECRET_KEY = _env("FLASK_SECRET_KEY")
    DEBUG = os.getenv("FLASK_DEBUG", "False").lower() in ("1", "true", "yes")
    PROPAGATE_EXCEPTIONS = True
    SESSION_PERMANENT = True

    # Azure B2C / MSAL
    CLIENT_ID = _env("AZURE_CLIENT_ID")
    CLIENT_SECRET = _env("AZURE_CLIENT_SECRET")
    TENANT_ID = _env("AZURE_TENANT_ID")
    REDIRECT_URI = _env("AZURE_REDIRECT_URI")
    AZURE_POLICY = _env("AZURE_POLICY")
    # B2C authority (includes policy)
    AZURE_AUTHORITY = _env("AZURE_AUTHORITY")
    AUTHORITY = f"{AZURE_AUTHORITY}/{AZURE_POLICY}"
    LOGIN_URL = f"{AUTHORITY}/oauth2/v2.0/authorize"
    TOKEN_URL = f"{AUTHORITY}/oauth2/v2.0/token"
    # AAD authority for client credentials (e.g., Graph API)
    AAD_AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"

    # Square
    SQUARE_ACCESS_TOKEN = _env("SQUARE_ACCESS_TOKEN")
    SQUARE_APPLICATION_ID = _env("SQUARE_APPLICATION_ID")

    # Azure Storage / Tables / Blob
    AZURE_STORAGE_CONNECTION_STRING = _env("AZURE_STORAGE_CONNECTION_STRING")

    # Azure Communication Email
    AZURE_COMM_CONNECTION_STRING = _env("AZURE_COMM_CONNECTION_STRING")
    AZURE_COMM_CONNECTION_STRING_SENDER = _env("AZURE_COMM_CONNECTION_STRING_SENDER")

    # Facebook Graph API
    FACEBOOK_PAGE_ID = _env("FACEBOOK_PAGE_ID")
    FACEBOOK_REDIRECT_URI = _env("FACEBOOK_REDIRECT_URI")
    FACEBOOK_APP_ID = _env("FACEBOOK_APP_ID")
    FACEBOOK_APP_SECRET = _env("FACEBOOK_APP_SECRET")

    # JSON schema settings (if any future)
    # Add more config as needed