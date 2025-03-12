# app/scheduler.py
from flask_apscheduler import APScheduler
from app.utils import compute_expiration_date  # or any function you need
import uuid
from datetime import datetime
import os

def check_membership_expiration():
    # Your scheduled task implementation
    run_id = uuid.uuid4()
    start_time = datetime.utcnow().isoformat()
    pid = os.getpid()
    print(f"Expiration check started at {start_time}, PID {pid}, Run ID: {run_id}")
    # Add logic to check membership expiration, send emails, etc.
    # ...

def init_scheduler(app):
    scheduler = APScheduler()
    scheduler.init_app(app)
    scheduler.add_job(func=check_membership_expiration, trigger="cron", hour=17, minute=30, id="expiration_check")
    scheduler.start()
