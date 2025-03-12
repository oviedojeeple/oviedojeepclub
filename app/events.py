# app/events.py
import os
import json
from jsonschema import validate, ValidationError, SchemaError
from azure.storage.blob import BlobServiceClient

# Global constants and configuration for events
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME = "events"

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

def upload_event_data(event_data, blob_name):
    """
    Accepts a single event data dictionary, wraps it in a list, validates it,
    and uploads the JSON string to Azure Blob Storage.
    Returns a tuple: (success: bool, message: str)
    """
    # Wrap the event data in an array since our schema expects an array of events
    data_array = [event_data]
    is_valid, message = validate_json(data_array)
    if not is_valid:
        return False, message

    # Convert the JSON data into a string
    json_str = json.dumps(data_array, indent=2)
    try:
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=blob_name)
        blob_client.upload_blob(json_str, overwrite=True)
        return True, "Event data uploaded successfully!"
    except Exception as e:
        return False, f"Azure Blob Upload Error: {e}"
