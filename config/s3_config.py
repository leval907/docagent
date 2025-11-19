"""
S3 Configuration for Beget Cloud Storage
"""

import boto3
from botocore.client import Config
import os

# Beget S3 Configuration
S3_ENDPOINT = "https://s3.ru1.storage.beget.cloud"
S3_BUCKET = "db6a1f644d97-la-ducem1"
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "JQDHVXZY7XFWUHF8LV0S")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "pjVG1Zt5G6y8N8eYAmPnKcnnPpfxB3KVCcFrEyfk")
S3_REGION = "ru1"

def get_s3_client():
    """Get configured S3 client for Beget (write operations use signature v2)"""
    return boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name=S3_REGION,
        verify=False,
        config=Config(
            signature_version='s3',  # v2 for Beget compatibility
            s3={'addressing_style': 'path'}
        )
    )

def get_s3_read_client():
    """Get S3 client for read operations (list/get) - uses signature v4"""
    return boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name=S3_REGION,
        verify=False,
        config=Config(
            signature_version='s3v4',  # v4 for read operations
            s3={'addressing_style': 'path'}
        )
    )

def upload_to_s3(file_path: str, s3_path: str) -> str:
    """
    Upload file to S3
    
    Args:
        file_path: Local file path
        s3_path: S3 object key (path in bucket)
    
    Returns:
        S3 URI: s3://bucket/path
    """
    s3 = get_s3_client()
    s3.upload_file(file_path, S3_BUCKET, s3_path)
    return f"s3://{S3_BUCKET}/{s3_path}"

def download_from_s3(s3_path: str, local_path: str) -> str:
    """
    Download file from S3
    
    Args:
        s3_path: S3 object key
        local_path: Local destination path
    
    Returns:
        Local file path
    """
    s3 = get_s3_read_client()  # Use read client for downloads
    s3.download_file(S3_BUCKET, s3_path, local_path)
    return local_path

def list_s3_files(prefix: str) -> list:
    """
    List files in S3 with prefix
    
    Args:
        prefix: S3 prefix (folder path)
    
    Returns:
        List of S3 object keys
    """
    s3 = get_s3_read_client()  # Use read client for listing
    response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)
    return [obj['Key'] for obj in response.get('Contents', [])]

def delete_from_s3(s3_path: str):
    """Delete file from S3"""
    s3 = get_s3_client()
    s3.delete_object(Bucket=S3_BUCKET, Key=s3_path)

def get_s3_url(s3_path: str) -> str:
    """Get public URL for S3 object"""
    return f"{S3_ENDPOINT}/{S3_BUCKET}/{s3_path}"
