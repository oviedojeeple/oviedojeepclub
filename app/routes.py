# app/routes.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_required, current_user, login_user, logout_user

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    # Minimal version of your index route
    return render_template('index.html')

# You can move additional routes here:
@main_bp.route('/login')
def login():
    session.clear()
    # Build and store your auth flow
    from app.utils import build_auth_code_flow
    session["flow"] = build_auth_code_flow()
    return redirect(session["flow"]["auth_uri"])

# Add your other routes (e.g., /auth/callback, /logout, etc.) below...
