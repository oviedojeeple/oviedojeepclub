import os
import json
from jsonschema import validate, ValidationError, SchemaError
from azure.storage.blob import BlobServiceClient

# Azure Storage configuration: Make sure the environment variable is set.
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME = "events"

# JSON Schema Definition for events
EVENT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Oviedo Jeep Club Event",
    "description": "Schema for Oviedo Jeep Club event listings",
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "name": {"type": "string"},
            "description": {"type": "string"},
            "start_time": {"type": "string", "format": "date-time"},
            "end_time": {"type": ["string", "null"], "format": "date-time"},
            "place": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "location": {
                        "type": "object",
                        "properties": {
                            "city": {"type": "string"},
                            "country": {"type": "string"},
                            "latitude": {"type": "number"},
                            "longitude": {"type": "number"},
                            "state": {"type": "string"},
                            "street": {"type": ["string", "null"]},
                            "zip": {"type": ["string", "null"]}
                        },
                        "required": ["city", "country", "latitude", "longitude", "state"]
                    },
                    "id": {"type": ["string", "null"]}
                },
                "required": ["name", "location"]
            },
            "cover": {
                "type": "object",
                "properties": {
                    "offset_x": {"type": "integer", "minimum": 0, "maximum": 100},
                    "offset_y": {"type": "integer", "minimum": 0, "maximum": 100},
                    "source": {"type": "string", "format": "uri"},
                    "id": {"type": ["string", "null"]}
                },
                "required": ["source"]
            }
        },
        "required": ["id", "name", "description", "start_time", "place", "cover"]
    }
}

def validate_json(data):
    """
    Validates the given JSON data against the EVENT_SCHEMA.
    Returns a tuple: (is_valid: bool, message: str)
    """
    try:
        validate(instance=data, schema=EVENT_SCHEMA)
        return True, ""
    except ValidationError as e:
        return False, f"JSON Validation Error: {e.message}"
    except SchemaError as e:
        return False, f"Schema Error: {e.message}"

def upload_to_azure_blob(file_path, blob_name):
    """
    Uploads a file to Azure Blob Storage.
    Returns a tuple: (success: bool, message: str)
    """
    try:
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=blob_name)
        with open(file_path, "rb") as file_data:
            blob_client.upload_blob(file_data, overwrite=True)
        return True, ""
    except Exception as e:
        return False, f"Azure Blob Upload Error: {e}"

def process_event_file(file_path):
    """
    Processes an event JSON file:
    - Loads and validates JSON data.
    - Uploads the file to Azure Blob Storage if valid.
    Returns a tuple: (success: bool, message: str)
    """
    try:
        with open(file_path, "r", encoding="utf-8") as json_file:
            data = json.load(json_file)
    except json.JSONDecodeError as e:
        return False, f"Error decoding JSON: {e}"

    is_valid, message = validate_json(data)
    if not is_valid:
        return False, message

    success, upload_message = upload_to_azure_blob(file_path, os.path.basename(file_path))
    if success:
        return True, "File uploaded and validated successfully!"
    else:
        return False, upload_message
