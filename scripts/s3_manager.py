#!/usr/bin/env python3
"""
S3 Manager - Upload, download, and manage files in Beget S3
All files are stored under docagent/ prefix in bucket
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.s3_config import (
    upload_to_s3,
    download_from_s3,
    list_s3_files,
    delete_from_s3,
    get_s3_url,
    sync_folder_to_s3,
    get_s3_folder_size,
    S3_BUCKET,
    S3_PREFIX,
    S3_ENDPOINT
)
from dotenv import load_dotenv
import argparse

# Load environment variables
load_dotenv('/opt/docagent/.env')


def test_connection():
    """Test S3 connection"""
    print(f"🔗 Testing S3 connection...")
    print(f"   Endpoint: {S3_ENDPOINT}")
    print(f"   Bucket: {S3_BUCKET}")
    print(f"   Prefix: {S3_PREFIX}")
    
    try:
        files = list_s3_files()
        print(f"✅ Connection successful!")
        print(f"   Files in {S3_PREFIX}: {len(files)}")
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


def list_files(prefix: str = ""):
    """List files in S3"""
    print(f"📂 Listing files in {S3_PREFIX}{prefix}...")
    
    try:
        files = list_s3_files(prefix)
        
        if not files:
            print(f"   No files found")
            return
        
        print(f"   Found {len(files)} files:")
        for file in sorted(files):
            print(f"   - {file}")
    
    except Exception as e:
        print(f"❌ Error listing files: {e}")


def upload_file(local_path: str, s3_path: str = None):
    """Upload file to S3"""
    print(f"⬆️  Uploading {local_path}...")
    
    if not os.path.exists(local_path):
        print(f"❌ File not found: {local_path}")
        return
    
    try:
        uri = upload_to_s3(local_path, s3_path)
        url = get_s3_url(s3_path or Path(local_path).name)
        
        print(f"✅ Uploaded successfully!")
        print(f"   URI: {uri}")
        print(f"   URL: {url}")
    
    except Exception as e:
        print(f"❌ Upload failed: {e}")


def download_file(s3_path: str, local_path: str):
    """Download file from S3"""
    print(f"⬇️  Downloading {s3_path}...")
    
    try:
        result = download_from_s3(s3_path, local_path)
        print(f"✅ Downloaded to: {result}")
    
    except Exception as e:
        print(f"❌ Download failed: {e}")


def delete_file(s3_path: str):
    """Delete file from S3"""
    print(f"🗑️  Deleting {s3_path}...")
    
    try:
        delete_from_s3(s3_path)
        print(f"✅ Deleted successfully!")
    
    except Exception as e:
        print(f"❌ Delete failed: {e}")


def sync_folder(local_folder: str, s3_folder: str = ""):
    """Sync local folder to S3"""
    print(f"🔄 Syncing {local_folder} to s3://{S3_BUCKET}/{S3_PREFIX}{s3_folder}...")
    
    if not os.path.exists(local_folder):
        print(f"❌ Folder not found: {local_folder}")
        return
    
    try:
        uploaded = sync_folder_to_s3(local_folder, s3_folder)
        print(f"✅ Synced {len(uploaded)} files!")
        
        for uri in uploaded[:5]:  # Show first 5
            print(f"   - {uri}")
        
        if len(uploaded) > 5:
            print(f"   ... and {len(uploaded) - 5} more")
    
    except Exception as e:
        print(f"❌ Sync failed: {e}")


def folder_info(s3_folder: str = ""):
    """Show folder size and file count"""
    print(f"📊 Analyzing {S3_PREFIX}{s3_folder}...")
    
    try:
        stats = get_s3_folder_size(s3_folder)
        
        print(f"✅ Folder statistics:")
        print(f"   Files: {stats['files']}")
        print(f"   Size: {stats['size_mb']} MB ({stats['size_gb']} GB)")
    
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    parser = argparse.ArgumentParser(description='S3 Manager for docagent project')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Test connection
    subparsers.add_parser('test', help='Test S3 connection')
    
    # List files
    list_parser = subparsers.add_parser('list', help='List files')
    list_parser.add_argument('prefix', nargs='?', default='', help='S3 prefix (folder)')
    
    # Upload file
    upload_parser = subparsers.add_parser('upload', help='Upload file')
    upload_parser.add_argument('local_path', help='Local file path')
    upload_parser.add_argument('s3_path', nargs='?', help='S3 path (optional)')
    
    # Download file
    download_parser = subparsers.add_parser('download', help='Download file')
    download_parser.add_argument('s3_path', help='S3 path')
    download_parser.add_argument('local_path', help='Local destination path')
    
    # Delete file
    delete_parser = subparsers.add_parser('delete', help='Delete file')
    delete_parser.add_argument('s3_path', help='S3 path')
    
    # Sync folder
    sync_parser = subparsers.add_parser('sync', help='Sync folder to S3')
    sync_parser.add_argument('local_folder', help='Local folder path')
    sync_parser.add_argument('s3_folder', nargs='?', default='', help='S3 folder (optional)')
    
    # Folder info
    info_parser = subparsers.add_parser('info', help='Show folder statistics')
    info_parser.add_argument('s3_folder', nargs='?', default='', help='S3 folder (optional)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print(f"\n{'='*60}")
    print(f"S3 Manager - Beget Cloud Storage")
    print(f"{'='*60}\n")
    
    if args.command == 'test':
        test_connection()
    
    elif args.command == 'list':
        list_files(args.prefix)
    
    elif args.command == 'upload':
        upload_file(args.local_path, args.s3_path)
    
    elif args.command == 'download':
        download_file(args.s3_path, args.local_path)
    
    elif args.command == 'delete':
        delete_file(args.s3_path)
    
    elif args.command == 'sync':
        sync_folder(args.local_folder, args.s3_folder)
    
    elif args.command == 'info':
        folder_info(args.s3_folder)
    
    print(f"\n{'='*60}\n")


if __name__ == '__main__':
    main()
