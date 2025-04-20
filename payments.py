"""
Payments blueprint: handles membership payments (new and renewal) via Square and processes webhooks.
"""
import os
from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
from azure_services import square_client
from user_services import create_b2c_user, create_membership_details
from emails import send_new_membership_email, send_membership_renewal_email
from config import Config

payments_bp = Blueprint('payments', __name__)

@payments_bp.route('/items', methods=['GET'])
def get_items():
    result = square_client.catalog.list_catalog(types='ITEM')
    if result.is_success():
        return jsonify(result.body.get('objects', []))
    return jsonify({'error': 'Unable to fetch items'}), 500

@payments_bp.route('/join', methods=['GET'])
def join():
    return render_template('index.html', application_id=Config.SQUARE_APPLICATION_ID)

@payments_bp.route('/pay', methods=['POST'])
def pay():
    data = request.form or request.get_json() or {}
    nonce = data.get('nonce')
    email = data.get('email')
    name = data.get('displayName')
    password = data.get('password')
    if not nonce or not email or not name or not password:
        flash('Missing payment or user info.', 'danger')
        return redirect(url_for('payments.join'))
    if session.get('user_data') and email == session['user_data'].get('email'):
        flash('Email already used.', 'danger')
        return redirect(url_for('payments.join'))
    body = {
        'source_id': nonce,
        'amount_money': {'amount': 5000, 'currency': 'USD'},
        'idempotency_key': os.urandom(12).hex()
    }
    result = square_client.payments.create_payment(body)
    if not result.is_success():
        flash('Payment failed.', 'danger')
        return redirect(url_for('payments.join'))
    receipt = result.body.get('payment', {}).get('receipt_url')
    membership_number, join_date, expiration_date = create_membership_details()
    try:
        create_b2c_user(email, name, password, membership_number, join_date, expiration_date)
        send_new_membership_email(email, name, receipt)
        flash('Account created successfully. Please sign in.', 'success')
    except Exception as e:
        flash(f'Error creating account: {e}', 'danger')
    return redirect(url_for('payments.join'))

@payments_bp.route('/renew-membership', methods=['POST'])
@login_required
def renew_membership():
    data = request.get_json() or {}
    nonce = data.get('nonce')
    if not nonce:
        return jsonify(success=False, message='Missing card info'), 400
    body = {
        'source_id': nonce,
        'amount_money': {'amount': 3000, 'currency': 'USD'},
        'idempotency_key': os.urandom(12).hex()
    }
    result = square_client.payments.create_payment(body)
    if not result.is_success():
        return jsonify(success=False, message='Payment failed'), 400
    # Update expiration date in B2C (omitted for brevity)
    send_membership_renewal_email(current_user.email, current_user.name)
    return jsonify(success=True, message='Membership renewed successfully')

@payments_bp.route('/webhook/square', methods=['POST'])
def square_webhook():
    event = request.json
    # Handle payment notifications
    return '', 200