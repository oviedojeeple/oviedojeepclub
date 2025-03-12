# app/routes.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_required, current_user, login_user, logout_user
from app.events import upload_event_data

main_bp = Blueprint('main', __name__)

@main_bp.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/x-icon')

@main_bp.before_request
def validate_user_session():
    print("##### DEBUG ##### In validate_user_session()")
    if current_user.is_authenticated:
        if not user_still_exists(current_user.email):
            logout_user()
            session.clear()
            flash("Your account is no longer valid. Please log in again.")
            return redirect(url_for("login"))
            
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

@main_bp.route('/')
def index():
    print("##### DEBUG ##### In index()")
    application_id = os.getenv('SQUARE_APPLICATION_ID')
    return render_template('index.html', application_id=application_id, user=current_user)

@main_bp.route("/accept_invitation", methods=["GET", "POST"])
def accept_invitation():
    print("##### DEBUG ##### In accept_invitation()")
    if request.method == "HEAD":
        return ""
        
    token = request.args.get("token") or request.form.get("token")
    print("##### DEBUG ##### In accept_invitation(): Received token:", token)
    invitation = get_invitation(token)
    print("##### DEBUG ##### In accept_invitation(): Retrieved invitation:", invitation)
    
    if not token or not invitation:
        flash("Invalid or expired invitation token.", "danger")
        return redirect(url_for("index"))
    
    if request.method == "POST":
        password = request.form.get("password")
        if not password:
            flash("Password is required.", "danger")
            return render_template("accept_invitation.html", token=token,
                                   family_email=invitation["family_email"],
                                   family_name=invitation["family_name"])
        
        email = invitation["family_email"]
        display_name = invitation["family_name"]
        membership_number = invitation["membership_number"]
        join_date = invitation["member_joined_date"]
        expiration_date = invitation["member_expiration_date"]
        
        try:
            created_user = create_b2c_user(email, display_name, password, membership_number, join_date, expiration_date)
            flash("Family member account created successfully. Please sign in.", "success")
            delete_invitation(token)
            return redirect(url_for("login"))
        except Exception as e:
            flash(f"Error creating family member account: {e}", "danger")
            return render_template("accept_invitation.html", token=token,
                                   family_email=invitation["family_email"],
                                   family_name=invitation["family_name"])
    
    return render_template("accept_invitation.html", token=token,
                           family_email=invitation["family_email"],
                           family_name=invitation["family_name"])

@main_bp.route('/auth/callback')
def auth_callback():
    print("##### DEBUG ##### In auth_callback()")
    flow = session.get("flow")
    if not flow:
        print("##### DEBUG ##### In auth_callback() Session expired or lost, please try logging in again.")
        return redirect(url_for("login"))
    
    result = _acquire_token_by_auth_code_flow(flow, request.args)
    if result:
        user_info = result
        print("##### DEBUG ##### In auth_callback(): Full token claims:", user_info)

        member_expiration_raw = user_info.get("extension_MemberExpirationDate")
        member_joined_raw = user_info.get("extension_MemberJoinedDate")
    
        member_expiration = "Not Available"
        member_expiration_iso = None
    
        if member_expiration_raw:
            try:
                timestamp_int = int(member_expiration_raw)
                if timestamp_int > 1e10:
                    timestamp_int = timestamp_int / 1000
                expiration_date_obj = datetime.fromtimestamp(timestamp_int).date()
                member_expiration = expiration_date_obj.strftime('%B %d, %Y')
                member_expiration_iso = expiration_date_obj.isoformat()
                print("##### DEBUG ##### In auth_callback(): Member expiration dates: ", member_expiration, member_expiration_iso)
            except Exception as e:
                print("##### DEBUG ##### In auth_callback() Converting timestamp failed:", e)
                member_expiration = "Invalid Date"
    
        job_title = user_info.get("jobTitle", "OJC Member")
        membership_number = user_info.get("extension_MembershipNumber")
    
        user_data = {
            "user_id": user_info["oid"],
            "name": user_info["name"],
            "email": user_info["emails"][0],
            "membership_number": membership_number,
            "job_title": job_title,
            "member_expiration_date": member_expiration,
            "member_expiration_iso": member_expiration_iso,
            "member_expiration_raw": member_expiration_raw,
            "member_joined_raw": member_joined_raw
        }
    
        session["user_data"] = user_data
    
        user_data_for_login = {k: v for k, v in user_data.items() 
                               if k in [
                                   "user_id", "name", "email", "job_title", "membership_number",
                                   "member_expiration_date", "member_expiration_iso", 
                                   "member_expiration_raw", "member_joined_raw"]}
    
        login_user(User(**user_data_for_login), remember=True)
        print("##### DEBUG ##### In auth_callback() Session after login: ", session)
        return redirect(url_for("index"))
    
    return "Login failed", 401

@main_bp.route('/blob-events')
@login_required
def blob_events():
    print("##### DEBUG ##### In blob_events()")
    connection_string = AZURE_STORAGE_CONNECTION_STRING
    try:
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_name = "events"
        blob_client = blob_service_client.get_blob_client(container=container_name, blob="events.json")
        events_blob = blob_client.download_blob().readall()
        events_data = json.loads(events_blob)
        
        # Only show future events by default
        now = datetime.utcnow()
        future_events = [
            event for event in events_data
            if parse_date(event.get('start_time')) > now
        ]
        
        sorted_events = sort_events_by_date_desc(future_events)
        return jsonify(sorted_events)
    except Exception as e:
        print("Error reading blob events:", e)
        return jsonify({"error": "Unable to read events from blob"}), 500

@main_bp.route("/create_event", methods=["GET", "POST"])
def create_event():
    print("##### DEBUG ##### In create_event()")
    if request.method == "POST":
        import time
        unique_event_id = "OJC" + str(int(time.time() * 1000))
        
        cover_image_file = request.files.get("cover_image")
        cover_image_url = None
        if cover_image_file:
            try:
                connection_string = AZURE_STORAGE_CONNECTION_STRING
                blob_service_client = BlobServiceClient.from_connection_string(connection_string)
                container_name = "event-images"
                try:
                    container_client = blob_service_client.get_container_client(container_name)
                    container_client.get_container_properties()
                except Exception:
                    container_client = blob_service_client.create_container(container_name)
                
                file_extension = cover_image_file.filename.rsplit(".", 1)[-1]
                blob_name = f"{unique_event_id}_{uuid.uuid4().hex}.{file_extension}"
                blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
                blob_client.upload_blob(cover_image_file, overwrite=True)
                cover_image_url = blob_client.url
            except Exception as e:
                print("Error uploading cover image:", e)
                flash("Error uploading cover image.", "danger")
                return redirect(url_for("create_event"))
        
        event = {
            "id": unique_event_id,
            "name": request.form.get("name", "").strip(),
            "description": request.form.get("description", "").strip(),
            "start_time": request.form.get("start_time", "").strip(),
            "end_time": request.form.get("end_time", "").strip() or None,
            "place": {
                "name": request.form.get("place_name", "").strip(),
                "location": {
                    "city": request.form.get("city", "").strip(),
                    "country": request.form.get("country", "").strip(),
                    "latitude": float(request.form.get("latitude", 0)),
                    "longitude": float(request.form.get("longitude", 0)),
                    "state": request.form.get("state", "").strip(),
                    "street": request.form.get("street", "").strip() or None,
                    "zip": request.form.get("zip", "").strip() or None,
                },
                "id": request.form.get("place_id", "").strip() or None,
            },
            "cover": {
                "offset_x": int(request.form.get("offset_x", 0)),
                "offset_y": int(request.form.get("offset_y", 0)),
                "source": cover_image_url or request.form.get("cover_source", "").strip(),
                "id": request.form.get("cover_id", "").strip() or None,
            },
        }
        
        events_list = get_events_from_blob(future_only=True)
        events_list.append(event)
        success, message = upload_events_to_blob(events_list)
        if success:
            flash(message, "success")
        else:
            flash(message, "danger")
        return redirect(url_for("index", section="events"))
    
    return render_template("create_event.html")

@main_bp.route('/delete_event/<event_id>', methods=['POST'])
@login_required
def delete_event(event_id):
    print("##### DEBUG ##### In delete_event()")
    if current_user.job_title != 'OJC Board Member':
        flash("You are not authorized to delete events.", "danger")
        return redirect(url_for("index"))
    
    events_list = get_events_from_blob(future_only=True)
    new_events_list = [event for event in events_list if event.get("id") != event_id]
    
    if len(new_events_list) == len(events_list):
        flash("Event not found.", "warning")
        return redirect(url_for("index", section="events"))
    
    success, message = upload_events_to_blob(new_events_list)
    if success:
        flash("Event deleted successfully.", "success")
    else:
        flash("Error deleting event: " + message, "danger")
    
    return redirect(url_for("index", section="events"))

@main_bp.route('/facebook/callback')
@login_required
def facebook_callback():
    print("##### DEBUG ##### In facebook_callback()")
    if request.args.get('state') != session.get('fb_state'):
        return "State mismatch", 400

    code = request.args.get('code')
    if not code:
        return "No code provided", 400

    token_url = "https://graph.facebook.com/v22.0/oauth/access_token"
    redirect_uri = os.getenv("FACEBOOK_REDIRECT_URI")
    params = {
        "client_id": os.getenv("FACEBOOK_APP_ID"),
        "redirect_uri": redirect_uri,
        "client_secret": os.getenv("FACEBOOK_APP_SECRET"),
        "code": code
    }
    token_response = requests.get(token_url, params=params)
    token_data = token_response.json()

    if "access_token" not in token_data:
        return f"Failed to get access token: {token_data.get('error')}", 400

    session["fb_access_token"] = token_data["access_token"]
    session.modified = True

    FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
    fb_events = get_facebook_events(FACEBOOK_PAGE_ID, session.get("fb_access_token"))
    if fb_events is None:
        return jsonify({"error": "Unable to fetch events from Facebook"}), 500

    sorted_facebook_events = sort_events_by_date_desc(fb_events)
    
    # Get existing local events (DO NOT OVERWRITE)
    existing_events = get_events_from_blob(future_only=True)
    local_events = [ev for ev in existing_events if ev.get("id", "").startswith("OJC")]

    # Combine local events and Facebook events without overwriting
    combined_events = local_events + sorted_facebook_events
    combined_events = sort_events_by_date_desc(combined_events)
    
    success, message = upload_events_to_blob(combined_events)
    if not success:
        return jsonify({"error": message}), 500

    flash("Facebook events synced successfully!", "success")
    return redirect(url_for("index", section="events"))

@main_bp.route('/family-members', methods=['GET'])
@login_required
def family_members():
    print("##### DEBUG ##### In family_members()")
    membership_number = current_user.membership_number
    graph_token = _acquire_graph_api_token()
    if not graph_token:
        return jsonify({"error": "Unable to acquire Graph API token"}), 500

    headers = {"Authorization": f"Bearer {graph_token}"}
    filter_clause = f"(extension_b32ce28f40e2412fb56abae06a1ac8ab_MembershipNumber eq '{membership_number}')"
    print("##### DEBUG ##### In family_members() filter_clause", filter_clause)
    params = {
        "$select": "id,displayName,mailNickName,userPrincipalName,extension_b32ce28f40e2412fb56abae06a1ac8ab_MembershipNumber",
        "$filter": filter_clause
    }
    print("##### DEBUG ##### In family_members() params", params)
    url = "https://graph.microsoft.com/v1.0/users"
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json().get("value", [])
        current_user_upn = f"{current_user.email.replace('@', '_at_')}@oviedojeepclub.onmicrosoft.com"
        data = [user for user in data if user.get("userPrincipalName") != current_user_upn]
        print("##### DEBUG ##### In family_members() family member user data: ", data)
        return jsonify(data)
    else:
        print("Graph API error:", response.text)
        return jsonify({"error": "Failed to fetch family members"}), response.status_code

@main_bp.route('/login')
def login():
    print("##### DEBUG ##### In login()")
    session.clear()
    session["flow"] = _build_auth_code_flow()
    return redirect(session["flow"]["auth_uri"])

@main_bp.route('/delete-data', methods=['GET', 'POST'])
def delete_data():
    if request.method == 'POST':
        email = request.form['email']
        print(f"Data deletion requested for: {email}")
        return render_template('delete_data.html', message="Your data deletion request has been received.", message_type="success")
    
    return render_template('delete_data.html')

@main_bp.route('/fb-events')
@login_required
def fb_events():
    print("##### DEBUG ##### In fb_events()")
    FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
    fb_token = session.get("fb_access_token")
    print("##### DEBUG ##### In fb_events() fb_access_token in session:", "fb_access_token" in session)
    events = get_facebook_events(FACEBOOK_PAGE_ID, fb_token)
    if events is None:
        return jsonify({"error": "Unable to fetch events"}), 500

    sorted_events = sort_events_by_date_desc(events)
    return jsonify(sorted_events)

@main_bp.route('/invite_family', methods=['GET', 'POST'])
@login_required
def invite_family():
    print("##### DEBUG ##### In invite_family()")
    if request.method == 'POST':
        family_email = request.form.get('family_email')
        family_name = request.form.get('family_name')
    if not family_email or not family_name:
        return jsonify({"error": "Missing family name or email"}), 400

    token = uuid.uuid4().hex
    print("##### DEBUG ##### In invite_family(): token", token)
    membership_number = current_user.membership_number
    member_joined_date = current_user.member_joined_raw
    member_expiration_date = current_user.member_expiration_raw
    invitation_data = {
        "family_email": family_email,
        "family_name": family_name,
        "membership_number": membership_number,
        "member_joined_date": member_joined_date,
        "member_expiration_date": member_expiration_date
    }
    print("##### DEBUG ##### In invite_family(): invitation_data", invitation_data)
    store_invitation(token, invitation_data)
    invitation_link = url_for("accept_invitation", token=token, _external=True)
    print("##### DEBUG ##### In invite_family(): invitation_link", invitation_link)
    send_family_invitation_email(family_email, family_name, invitation_link)
    
    return jsonify({"message": "Invitation sent successfully!"})

@main_bp.route('/items', methods=['GET'])
def get_items():
    print("##### DEBUG ##### In get_items()")
    result = client.catalog.list_catalog(types='ITEM')
    if result.is_success():
        items = result.body['objects']
        return jsonify(items)
    else:
        return jsonify({'error': 'Unable to fetch items'}), 500

@main_bp.route('/join')
def join():
    print("##### DEBUG ##### In join()")
    application_id = os.getenv('SQUARE_APPLICATION_ID')
    return render_template('index.html', application_id=application_id)

@main_bp.route('/list_old_events', methods=['GET'])
@login_required
def list_old_events():
    print("##### DEBUG ##### In list_old_events()")
    
    if current_user.job_title != 'OJC Board Member':
        flash("You are not authorized to view old events.", "danger")
        return redirect(url_for('index'))
    
    try:
        # Get only past events
        past_events = get_events_from_blob(future_only=False)
        sorted_events = sort_events_by_date_desc(past_events)
        return jsonify({"events": sorted_events}), 200
    except Exception as e:
        print("Error fetching old events:", e)
        flash("Unable to fetch old events.", "danger")
        return jsonify({"error": "Unable to fetch old events"}), 500

@main_bp.route("/logout")
@login_required
def logout():
    print("##### DEBUG ##### In logout()")
    logout_user()
    session.clear()
    return redirect(f"{AUTHORITY}/oauth2/v2.0/logout?post_logout_redirect_uri=https://test.oviedojeepclub.com")

@main_bp.route('/pay', methods=['GET', 'POST'])
def pay():
    print("##### DEBUG ##### In pay()")
    if request.method == 'POST':
        amount = 5000
        nonce = request.form.get('nonce')
        email = request.form.get('email')
        display_name = request.form.get('displayName')
        password = request.form.get('password')

        if user_still_exists(email):
            flash("A user with this email already exists. Please use Login.", "danger")
            application_id = os.getenv('SQUARE_APPLICATION_ID')
            return render_template('index.html', application_id=application_id, user=current_user, joinVisible=True)
        
        body = {
            "source_id": nonce,
            "amount_money": {
                "amount": amount,
                "currency": "USD"
            },
            "idempotency_key": os.urandom(12).hex()
        }
        result = client.payments.create_payment(body)
        print("##### DEBUG ##### In pay() result of payment: ", result)
        
        if result.is_success():
            receipt_url = result.body.get('payment', {}).get('receipt_url')
            session["receipt_url"] = receipt_url
            flash('Payment Successful! Creating your account...', 'success')
            membership_number, join_date, expiration_date = create_membership_details()
            
            try:
                created_user = create_b2c_user(email, display_name, password, membership_number, join_date, expiration_date)
                print("##### DEBUG ##### User created: ", created_user)
                send_new_membership_email(email, display_name, receipt_url)
                flash('Account created successfully. Please sign in.', 'success')
            except Exception as e:
                flash(f'Error creating account: {e}', 'danger')
                print("##### DEBUG ##### Error creating account:", e)
            
            application_id = os.getenv('SQUARE_APPLICATION_ID')
            return render_template('index.html', application_id=application_id, user=current_user, joinVisible=True)
        else:
            flash('Payment Failed. Please try again.', 'danger')
            application_id = os.getenv('SQUARE_APPLICATION_ID')
            return render_template('index.html', application_id=application_id, user=current_user, joinVisible=True)
    
    return redirect(url_for('index'))

@main_bp.route('/privacy')
def privacy_policy():
    return render_template('privacy.html')

@main_bp.route('/webhook/square', methods=['POST'])
def square_webhook():
    print("##### DEBUG ##### In square_webhook()")
    event = request.json
    if event['type'] == 'payment.updated':
        payment_status = event['data']['object']['payment']['status']
        if payment_status == 'COMPLETED':
            print("Payment Completed")
    return '', 200

@main_bp.route('/renew-membership', methods=['POST'])
def renew_membership():
    print("##### DEBUG ##### In renew_membership()")
    data = request.get_json()
    print("##### DEBUG ##### In renew_membership() Received JSON:", data)
    nonce = data.get("nonce")
    print("##### DEBUG ##### In renew_membership() Received nonce:", nonce)
    if not nonce:
        flash('Missing card information.', 'danger')
        return jsonify(success=False, message="Missing card information"), 400

    user = session.get('user')
    if not current_user.is_authenticated:
        flash('User not authenticated.', 'danger')
        return jsonify(success=False, message="User not authenticated"), 401

    amount = 3000
    body = {
        "source_id": nonce,
        "amount_money": {
            "amount": amount,
            "currency": "USD"
        },
        "idempotency_key": os.urandom(12).hex()
    }
    result = client.payments.create_payment(body)
    print("##### DEBUG ##### In renew_membership() result of payment: ", result)
    if result.is_success():
        receipt_url = result.body.get('payment', {}).get('receipt_url')
        session["receipt_url"] = receipt_url
        new_expiration_date = compute_expiration_date()
        azure_ad_b2c_api_url = f"https://graph.microsoft.com/v1.0/users/{current_user.id}"
        update_payload = {"extension_b32ce28f40e2412fb56abae06a1ac8ab_MemberExpirationDate": new_expiration_date}
        
        graph_token = _acquire_graph_api_token()
        if not graph_token:
            flash('Payment succeeded but failed to update membership. Share error with Administrator. Graph Token missing.', 'danger')
            return jsonify(success=False, message="Failed to acquire Graph API token"), 500
        
        graph_headers = {
            "Authorization": f"Bearer {graph_token}",
            "Content-Type": "application/json"
        }
        
        membership_number = current_user.membership_number
        filter_clause = f"(extension_b32ce28f40e2412fb56abae06a1ac8ab_MembershipNumber eq '{membership_number}')"
        params = {
            "$select": "id,displayName,extension_b32ce28f40e2412fb56abae06a1ac8ab_MembershipNumber",
            "$filter": filter_clause
        }
        url = "https://graph.microsoft.com/v1.0/users"
        response = requests.get(url, headers=graph_headers, params=params)
        if response.status_code == 200:
            users = response.json().get("value", [])
            print("##### DEBUG ##### In renew_membership() Found users for renewal:", users)
            for user in users:
                user_id = user["id"]
                patch_url = f"https://graph.microsoft.com/v1.0/users/{user_id}"
                patch_payload = {
                    "extension_b32ce28f40e2412fb56abae06a1ac8ab_MemberExpirationDate": new_expiration_date
                }
                patch_response = requests.patch(patch_url, headers=graph_headers, json=patch_payload)
                if patch_response.status_code not in [200, 204]:
                    print(f"Error updating user {user_id}: {patch_response.text}")
            try:
                ts = int(new_expiration_date)
                if ts > 1e10:
                    ts = ts / 1000
                expiration_date_obj = datetime.fromtimestamp(ts).date()
                member_expiration = expiration_date_obj.strftime('%B %d, %Y')
                member_expiration_iso = expiration_date_obj.isoformat()
            except Exception as e:
                print("Error converting new expiration date:", e)
                member_expiration = "Invalid Date"
                member_expiration_iso = "Invalid Date"
            session["user_data"]["member_expiration_date"] = member_expiration
            session["user_data"]["member_expiration_iso"] = member_expiration_iso

            flash('Payment Successful! Your renewal has been updated for all members.', 'success')
            return jsonify(success=True, message="Membership renewed successfully")
        else:
            send_membership_renewal_email(current_user.email, current_user.name)
            flash('Payment succeeded but failed to update membership. Share error with Administrator.', 'danger')
            return jsonify(success=False, message="Payment succeeded but failed to update membership"), 500
    else:
        flash('Payment failed. Share error with Administrator.', 'danger')
        return jsonify(success=False, message="Payment failed"), 400

@main_bp.route('/sync-public-events')
def sync_public_events():
    print("##### DEBUG ##### In sync_public_events()")
    state = os.urandom(16).hex()
    session['fb_state'] = state

    redirect_uri = os.getenv("FACEBOOK_REDIRECT_URI")
    params = {
        "client_id": os.getenv("FACEBOOK_APP_ID"),
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": "pages_read_engagement,pages_read_user_content",
        "response_type": "code"
    }
    query_string = "&".join(f"{key}={quote(str(value))}" for key, value in params.items())
    fb_auth_url = f"https://www.facebook.com/v22.0/dialog/oauth?{query_string}"
    return redirect(fb_auth_url)

@main_bp.template_filter('to_date')
def to_date_filter(value, format="%Y-%m-%d"):
    print("##### DEBUG ##### In to_date_filter()")
    try:
        return datetime.strptime(value, format).date()
    except Exception as e:
        print("Error in to_date filter:", e)
        return None
