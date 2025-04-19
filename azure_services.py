from azure.storage.blob import BlobServiceClient
from azure.data.tables import TableServiceClient
from azure.communication.email import EmailClient
from square.client import Client as SquareClient

from config import Config

# Initialize Azure Blob service client
blob_service_client = BlobServiceClient.from_connection_string(
    Config.AZURE_STORAGE_CONNECTION_STRING
)

# Initialize Azure Table service client and invitations table
table_service_client = TableServiceClient.from_connection_string(
    Config.AZURE_STORAGE_CONNECTION_STRING
)
invitations_table_client = table_service_client.create_table_if_not_exists(
    table_name="Invitations"
)

# Initialize Azure Communication Email client
email_client = EmailClient.from_connection_string(
    Config.AZURE_COMM_CONNECTION_STRING
)

# Initialize Square client (sandbox environment by default)
square_client = SquareClient(
    access_token=Config.SQUARE_ACCESS_TOKEN,
    environment="sandbox"
)