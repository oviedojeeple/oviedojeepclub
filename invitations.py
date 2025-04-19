"""
Invitations blueprint: handles sending family membership invitations and accepting invitation tokens.
"""
import uuid
from datetime import datetime as _dt
from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from azure_services import invitations_table_client
from user_services import create_b2c_user
from emails import send_family_invitation_email

invitations_bp = Blueprint('invitations', __name__)

@invitations_bp.route('/accept_invitation', methods=['GET', 'POST'])
def accept_invitation():
    token = request.args.get('token') or request.form.get('token')
    invite = None
    if token:
        try:
            invite = dict(invitations_table_client.get_entity(token, token))
        except Exception:
            invite = None
    if not invite:
        flash('Invalid or expired invitation token.', 'danger')
        return redirect(url_for('index'))
    if request.method == 'POST':
        password = request.form.get('password')
        if not password:
            flash('Password is required.', 'danger')
            return render_template('accept_invitation.html', token=token, **invite)
        try:
            create_b2c_user(
                invite['family_email'], invite['family_name'], password,
                invite['membership_number'], invite['member_joined_date'], invite['member_expiration_date']
            )
            invitations_table_client.delete_entity(token, token)
            flash('Family member account created. Please sign in.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            flash(str(e), 'danger')
            return render_template('accept_invitation.html', token=token, **invite)
    return render_template('accept_invitation.html', token=token, **invite)

@invitations_bp.route('/invite_family', methods=['POST'])
@login_required
def invite_family():
    data = request.get_json() or request.form
    family_email = data.get('family_email')
    family_name = data.get('family_name')
    if not family_email or not family_name:
        return jsonify({'error': 'Missing family name or email'}), 400
    token = uuid.uuid4().hex
    entity = {
        'PartitionKey': token,
        'RowKey': token,
        'family_email': family_email,
        'family_name': family_name,
        'membership_number': current_user.membership_number,
        'member_joined_date': current_user.member_joined_raw,
        'member_expiration_date': current_user.member_expiration_raw,
        'CreatedAt': _dt.utcnow().isoformat()
    }
    invitations_table_client.upsert_entity(entity=entity)
    link = url_for('invitations.accept_invitation', token=token, _external=True)
    send_family_invitation_email(family_email, family_name, link)
    return jsonify({'message': 'Invitation sent successfully!'}), 200

@invitations_bp.route('/delete-data', methods=['GET', 'POST'])
def delete_data():
    if request.method == 'POST':
        email = request.form.get('email')
        flash('Your data deletion request has been received.', 'success')
        return render_template('delete_data.html', message='Your data deletion request has been received.', message_type='success')
    return render_template('delete_data.html')