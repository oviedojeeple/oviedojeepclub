# config.py
import os

class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "you-should-change-this")
    DEBUG = True
    SESSION_PERMANENT = True
    PROPAGATE_EXCEPTIONS = True

    # Environment and API config
    CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
    CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
    TENANT_ID = os.getenv("AZURE_TENANT_ID")
    REDIRECT_URI = os.getenv("AZURE_REDIRECT_URI")
    AZURE_POLICY = os.getenv("AZURE_POLICY")
    AZURE_AUTHORITY = os.getenv("AZURE_AUTHORITY")
    # Construct authority-related URLs
    AUTHORITY = f"{AZURE_AUTHORITY}/{AZURE_POLICY}"
    LOGIN_URL = f"{AUTHORITY}/oauth2/v2.0/authorize"
    TOKEN_URL = f"{AUTHORITY}/oauth2/v2.0/token"
    SQUARE_ACCESS_TOKEN = os.getenv("SQUARE_ACCESS_TOKEN")
    SQUARE_APPLICATION_ID = os.getenv("SQUARE_APPLICATION_ID")
    AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    AZURE_COMM_CONNECTION_STRING = os.getenv("AZURE_COMM_CONNECTION_STRING")
    AZURE_COMM_CONNECTION_STRING_SENDER = os.getenv("AZURE_COMM_CONNECTION_STRING_SENDER")
