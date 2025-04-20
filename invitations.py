"""
Invitations blueprint: handles sending family membership invitations and accepting invitation tokens.
"""
import uuid
from datetime import datetime as _dt
from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from azure_services import invitations_table_client
from user_services import create_b2c_user, _acquire_graph_api_token
import requests
from urllib.parse import quote
from emails import send_family_invitation_email
import logging

logger = logging.getLogger(__name__)

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
    try:
        # Parse JSON or form payload
        data = request.get_json(silent=True) or request.form
        logger.info(f"invite_family called; payload: {data}")
        family_email = data.get('family_email')
        family_name = data.get('family_name')
        if not family_email or not family_name:
            logger.info("invite_family missing family_name or family_email")
            return jsonify({'error': 'Missing family name or email'}), 400
        # Generate the invitation token and entity
        token = uuid.uuid4().hex
        logger.info(f"Generated invitation token {token} for family_email={family_email}")
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
        # Store invitation
        invitations_table_client.upsert_entity(entity=entity)
        logger.info(f"Invitation entity upserted with token {token} for {family_email}")
        # Build acceptance link
        link = url_for('invitations.accept_invitation', token=token, _external=True)
        # Send invitation email asynchronously
        import threading

        def _send():
            logger.info(f"_send: sending family invitation email to {family_email} with link {link}")
            try:
                send_family_invitation_email(family_email, family_name, link)
                logger.info(f"Family invitation email sent successfully to {family_email}")
            except Exception:
                logger.exception(f"Error sending family invitation to {family_email}")

        logger.info(f"Starting email sending thread for family_email={family_email}")
        threading.Thread(target=_send, daemon=True).start()
        return jsonify({'message': 'Invitation sent successfully!'}), 200
    except Exception as e:
        logger.exception("invite_family failed with exception")
        return jsonify({'error': str(e)}), 500

@invitations_bp.route('/delete-data', methods=['GET', 'POST'])
def delete_data():
    if request.method == 'POST':
        email = request.form.get('email')
        flash('Your data deletion request has been received.', 'success')
        return render_template('delete_data.html', message='Your data deletion request has been received.', message_type='success')
    return render_template('delete_data.html')
 
@invitations_bp.route('/family-members')
@login_required
def family_members():
    """
    Return family members (B2C users) associated with the current user's membership number.
    """
    # Acquire Graph API token
    token = _acquire_graph_api_token()
    if not token:
        return jsonify({'error': 'Unable to acquire Graph API token'}), 500
    # Build Graph API request to filter users by MembershipNumber extension attribute
    membership_number = current_user.membership_number
    filter_str = f"extension_b32ce28f40e2412fb56abae06a1ac8ab_MembershipNumber eq '{membership_number}'"
    # URL-encode the filter string
    encoded_filter = quote(filter_str)
    # Include userPrincipalName in select to filter out the current user
    select_fields = 'displayName,mailNickname,userPrincipalName'
    url = (
        f"https://graph.microsoft.com/v1.0/users"
        f"?$filter={encoded_filter}"
        f"&$select={select_fields}"
    )
    resp = requests.get(url, headers={'Authorization': f'Bearer {token}'})
    if resp.status_code != 200:
        return jsonify({'error': resp.text}), resp.status_code
    members = resp.json().get('value', [])
    # Filter out the signed-in user (membership number matches but not a family member)
    current_user_upn = (
        f"{current_user.email.replace('@', '_at_')}@oviedojeepclub.onmicrosoft.com"
    )
    filtered = [m for m in members if m.get('userPrincipalName') != current_user_upn]
    # Return remaining family members
    return jsonify(filtered)