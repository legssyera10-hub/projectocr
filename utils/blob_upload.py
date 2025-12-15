import os
from datetime import datetime, timedelta
from azure.storage.blob.aio import BlobServiceClient
from azure.storage.blob import generate_blob_sas, BlobSasPermissions
from azure.core.exceptions import AzureError, ResourceExistsError, ClientAuthenticationError

# Set via environment variables:
# BLOB_CONN_STRING="...storage connection string..."
# BLOB_CONTAINER="your-container-name"
BLOB_CONN_STRING = os.getenv("BLOB_CONN_STRING")
BLOB_CONTAINER = os.getenv("BLOB_CONTAINER")

if not BLOB_CONN_STRING or not BLOB_CONTAINER:
    raise RuntimeError("BLOB_CONN_STRING or BLOB_CONTAINER missing in environment variables.")

async def upload_image_to_blob(upload_file, blob_name: str) -> str:
    """Upload image to Blob Storage and return a SAS URL (read-only, short-lived)."""
    try:
        blob_service = BlobServiceClient.from_connection_string(BLOB_CONN_STRING)
        container_client = blob_service.get_container_client(BLOB_CONTAINER)

        try:
            await container_client.create_container()
        except ResourceExistsError:
            pass  # already exists

        blob_client = container_client.get_blob_client(blob_name)
        data = await upload_file.read()
        await blob_client.upload_blob(
            data,
            overwrite=True,
            content_type=upload_file.content_type or "image/jpeg",
        )
        # Build SAS token using account key from connection string credential
        account_key = None
        try:
            account_key = blob_service.credential.account_key  # type: ignore[attr-defined]
        except AttributeError:
            pass
        if not account_key:
            raise ClientAuthenticationError("Account key missing to generate SAS; check BLOB_CONN_STRING.")

        sas_token = generate_blob_sas(
            account_name=blob_client.account_name,
            container_name=BLOB_CONTAINER,
            blob_name=blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(minutes=60),
        )
        await blob_service.close()
        return f"{blob_client.url}?{sas_token}"
    except AzureError as exc:
        raise RuntimeError(f"Azure Blob error: {exc}") from exc
