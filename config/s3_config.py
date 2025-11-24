"""
S3 Configuration for Beget Cloud Storage
All project files are stored under docagent/ prefix
"""

import boto3
from botocore.client import Config
import os
from pathlib import Path

# Beget S3 Configuration
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "https://s3.ru1.storage.beget.cloud")
S3_BUCKET = os.getenv("S3_BUCKET", "db6a1f644d97-la-ducem1")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "JQDHVXZY7XFWUHF8LV0S")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "pjVG1Zt5G6y8N8eYAmPnKcnnPpfxB3KVCcFrEyfk")
S3_REGION = os.getenv("S3_REGION", "ru1")
S3_PREFIX = os.getenv("S3_PREFIX", "docagent/")  # Project folder in bucket

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

def upload_to_s3(file_path: str, s3_path: str = None, use_prefix: bool = True) -> str:
    """
    Upload file to S3
    
    Args:
        file_path: Local file path
        s3_path: S3 object key (path in bucket). If None, uses filename
        use_prefix: Whether to prepend S3_PREFIX (docagent/)
    
    Returns:
        S3 URI: s3://bucket/docagent/path
    """
    s3 = get_s3_client()
    
    if s3_path is None:
        s3_path = Path(file_path).name
    
    if use_prefix:
        s3_path = f"{S3_PREFIX}{s3_path}"
    
    s3.upload_file(file_path, S3_BUCKET, s3_path)
    return f"s3://{S3_BUCKET}/{s3_path}"

def download_from_s3(s3_path: str, local_path: str, use_prefix: bool = True) -> str:
    """
    Download file from S3
    
    Args:
        s3_path: S3 object key (without docagent/ prefix by default)
        local_path: Local destination path
        use_prefix: Whether to prepend S3_PREFIX (docagent/)
    
    Returns:
        Local file path
    """
    s3 = get_s3_read_client()
    
    if use_prefix and not s3_path.startswith(S3_PREFIX):
        s3_path = f"{S3_PREFIX}{s3_path}"
    
    s3.download_file(S3_BUCKET, s3_path, local_path)
    return local_path

def list_s3_files(prefix: str = "", use_prefix: bool = True) -> list:
    """
    List files in S3 with prefix
    
    Args:
        prefix: Additional prefix after docagent/ (e.g., "input/", "models/")
        use_prefix: Whether to prepend S3_PREFIX (docagent/)
    
    Returns:
        List of S3 object keys (without docagent/ prefix)
    """
    s3 = get_s3_read_client()
    
    if use_prefix:
        full_prefix = f"{S3_PREFIX}{prefix}"
    else:
        full_prefix = prefix
    
    response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=full_prefix)
    objects = [obj['Key'] for obj in response.get('Contents', [])]
    
    # Remove S3_PREFIX from results for cleaner paths
    if use_prefix:
        objects = [key.replace(S3_PREFIX, '', 1) for key in objects]
    
    return objects

def delete_from_s3(s3_path: str, use_prefix: bool = True):
    """
    Delete file from S3
    
    Args:
        s3_path: S3 object key
        use_prefix: Whether to prepend S3_PREFIX (docagent/)
    """
    s3 = get_s3_client()
    
    if use_prefix and not s3_path.startswith(S3_PREFIX):
        s3_path = f"{S3_PREFIX}{s3_path}"
    
    s3.delete_object(Bucket=S3_BUCKET, Key=s3_path)

def get_s3_url(s3_path: str, use_prefix: bool = True) -> str:
    """
    Get public URL for S3 object
    
    Args:
        s3_path: S3 object key
        use_prefix: Whether to prepend S3_PREFIX (docagent/)
    
    Returns:
        Full S3 URL
    """
    if use_prefix and not s3_path.startswith(S3_PREFIX):
        s3_path = f"{S3_PREFIX}{s3_path}"
    
    return f"{S3_ENDPOINT}/{S3_BUCKET}/{s3_path}"

def sync_folder_to_s3(local_folder: str, s3_folder: str = "", use_prefix: bool = True) -> list:
    """
    Sync entire local folder to S3
    
    Args:
        local_folder: Local folder path
        s3_folder: S3 folder path (relative to docagent/)
        use_prefix: Whether to prepend S3_PREFIX (docagent/)
    
    Returns:
        List of uploaded file URIs
    """
    s3 = get_s3_client()
    local_path = Path(local_folder)
    uploaded = []
    
    if not local_path.exists():
        raise FileNotFoundError(f"Local folder not found: {local_folder}")
    
    for file_path in local_path.rglob('*'):
        if file_path.is_file():
            # Calculate relative path
            relative_path = file_path.relative_to(local_path)
            s3_key = f"{s3_folder}/{relative_path}".replace('\\', '/')
            
            if use_prefix:
                s3_key = f"{S3_PREFIX}{s3_key}"
            
            # Upload file
            s3.upload_file(str(file_path), S3_BUCKET, s3_key)
            uploaded.append(f"s3://{S3_BUCKET}/{s3_key}")
    
    return uploaded

def get_s3_folder_size(s3_folder: str = "", use_prefix: bool = True) -> dict:
    """
    Calculate size and count of files in S3 folder
    
    Args:
        s3_folder: S3 folder path
        use_prefix: Whether to prepend S3_PREFIX (docagent/)
    
    Returns:
        Dict with 'files' count and 'size' in bytes
    """
    s3 = get_s3_read_client()
    
    if use_prefix:
        full_prefix = f"{S3_PREFIX}{s3_folder}"
    else:
        full_prefix = s3_folder
    
    response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=full_prefix)
    
    total_size = 0
    file_count = 0
    
    for obj in response.get('Contents', []):
        total_size += obj['Size']
        file_count += 1
    
    return {
        'files': file_count,
        'size': total_size,
        'size_mb': round(total_size / (1024 * 1024), 2),
        'size_gb': round(total_size / (1024 * 1024 * 1024), 2)
    }
