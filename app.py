import os
from flask import Flask, render_template, send_from_directory, session
from flask_login import current_user
from flask_restful import Api
from flask_cors import CORS
from flask_apscheduler import APScheduler
from datetime import datetime

import config
from auth import auth_bp
from invitations import invitations_bp
from events import events_bp, check_event_reminders
from payments import payments_bp
from user_services import check_membership_expiration

def create_app():
    """
    Application factory for the Oviedo Jeep Club Flask app.
    """
    # Initialize Flask app
    app = Flask(__name__)
    # Load configuration
    app.config.from_object(config.Config)
    # Enable CORS
    CORS(app)
    # Setup Flask-RESTful API (if any resources added)
    Api(app)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(invitations_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(payments_bp)

    # Main routes
    @app.route('/')
    def index():
        return render_template(
            'index.html',
            application_id=app.config['SQUARE_APPLICATION_ID'],
            user=current_user
        )

    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(
            os.path.join(app.root_path, 'static'),
            'favicon.ico',
            mimetype='image/vnd.microsoft.icon'
        )

    @app.route('/privacy')
    def privacy_policy():
        return render_template('privacy.html')

    # Context processors
    @app.context_processor
    def inject_now():
        return {'now': lambda: datetime.utcnow()}

    @app.context_processor
    def inject_user_data():
        return {'user_data': session.get('user_data', {})}

    # Template filters
    @app.template_filter('timestamp_to_year')
    def timestamp_to_year(ts):
        try:
            ts_int = int(ts)
            if ts_int > 1e10:
                ts_int /= 1000
            return datetime.fromtimestamp(ts_int).year
        except Exception:
            return 'N/A'

    @app.template_filter('to_date')
    def to_date_filter(value, fmt='%Y-%m-%d'):
        try:
            from datetime import datetime as _dt
            return _dt.strptime(value, fmt).date()
        except Exception:
            return None

    # After request handler
    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response

    # Scheduler jobs
    scheduler = APScheduler()
    scheduler.init_app(app)
    scheduler.add_job(
        func=check_membership_expiration,
        trigger='cron',
        hour=6,
        minute=30,
        id='expiration_check'
    )
    scheduler.add_job(
        func=check_event_reminders,
        trigger='cron',
        hour=1,
        minute=37,
        id='event_reminder'
    )
    scheduler.start()

    return app

# Create application instance for WSGI
app = create_app()

if __name__ == '__main__':
    app.run(debug=app.config['DEBUG'], use_reloader=False)