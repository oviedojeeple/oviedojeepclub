from flask import Flask, request, jsonify, render_template, send_from_directory, send_file
from flask_restful import Resource, Api
from flask_cors import CORS
from functools import wraps
from msal import ConfidentialClientApplication
from io import BytesIO
import os, json, time, requests, asyncio
import logging

# Initialize Flask App
app = Flask(__name__)
CORS(app)
api = Api(app)

# Configuration
CACHE_TIMEOUT = int(os.getenv("CACHE_TIMEOUT", 300))

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.debug("Flask app has started.")

# In-memory cache
cache = {}

def get_cached_item(cache_key):
    item = cache.get(cache_key)
    if item and time.time() - item[1] < CACHE_TIMEOUT:
        return item[0]
    return None

def set_cached_item(cache_key, item):
    cache[cache_key] = (item, time.time())

def error_response(message, status_code=400):
    return jsonify({"error": message}), status_code

@app.route('/')
def index():
    logger.info("Request for index page received")
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

class Main(Resource):
    def post(self):
        return jsonify({'message': 'Welcome to the Oviedo Jeep Club Flask REST App'})


# adding the defined resources along with their corresponding urls
api.add_resource(Main, '/')

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

if __name__ == '__main__':
    app.run(debug=True)
