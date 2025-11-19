#!/usr/bin/env python3
"""
Docling Document Processor
Converts PDF/DOCX/HTML to Markdown and uploads to S3
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from docling.document_converter import DocumentConverter
from config.s3_config import upload_to_s3, get_s3_client

class DoclingProcessor:
    def __init__(self, app_name: str):
        self.app_name = app_name
        self.converter = DocumentConverter()
    
    def process_file(self, file_path: str) -> dict:
        """
        Process single file with Docling
        
        Args:
            file_path: Path to file (PDF, DOCX, HTML, etc.)
        
        Returns:
            dict: {
                'markdown': str,
                's3_raw': str,
                's3_processed': str,
                'metadata': dict
            }
        """
        file_name = Path(file_path).name
        file_stem = Path(file_path).stem
        
        print(f"\n📄 Processing: {file_name}")
        
        # 1. Convert with Docling
        print("  🔄 Converting to Markdown...")
        result = self.converter.convert(file_path)
        markdown = result.document.export_to_markdown()
        
        # 2. Upload raw file to S3
        print("  ☁️  Uploading raw to S3...")
        s3_raw = f"raw/{self.app_name}/{file_name}"
        try:
            upload_to_s3(file_path, s3_raw)
            print(f"     ✅ {s3_raw}")
        except Exception as e:
            print(f"     ⚠️  Failed: {e}")
            s3_raw = None
        
        # 3. Save markdown locally
        md_path = f"/tmp/{file_stem}.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(markdown)
        
        # 4. Upload markdown to S3
        print("  ☁️  Uploading processed to S3...")
        s3_processed = f"processed/{self.app_name}/{file_stem}.md"
        try:
            upload_to_s3(md_path, s3_processed)
            print(f"     ✅ {s3_processed}")
        except Exception as e:
            print(f"     ⚠️  Failed: {e}")
            s3_processed = None
        
        # 5. Create metadata
        metadata = {
            "file_name": file_name,
            "app_name": self.app_name,
            "s3_raw": s3_raw,
            "s3_processed": s3_processed,
            "pages": len(result.pages) if hasattr(result, 'pages') else 0,
            "word_count": len(markdown.split()),
            "char_count": len(markdown),
            "processed_at": datetime.now().isoformat(),
            "file_size": os.path.getsize(file_path),
            "file_type": Path(file_path).suffix
        }
        
        # 6. Upload metadata to S3
        print("  ☁️  Uploading metadata to S3...")
        metadata_path = f"/tmp/{file_stem}.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        s3_metadata = f"metadata/{self.app_name}/{file_stem}.json"
        try:
            upload_to_s3(metadata_path, s3_metadata)
            print(f"     ✅ {s3_metadata}")
        except Exception as e:
            print(f"     ⚠️  Failed: {e}")
        
        # Cleanup temp files
        try:
            os.remove(md_path)
            os.remove(metadata_path)
        except:
            pass
        
        print(f"  ✅ Done! Processed {metadata['word_count']} words")
        
        return {
            'markdown': markdown,
            's3_raw': s3_raw,
            's3_processed': s3_processed,
            'metadata': metadata
        }
    
    def process_directory(self, directory: str) -> list:
        """Process all supported files in directory"""
        results = []
        supported_extensions = ['.pdf', '.docx', '.doc', '.html', '.htm', '.pptx']
        
        print(f"\n🔍 Scanning directory: {directory}")
        
        for file_path in Path(directory).rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                try:
                    result = self.process_file(str(file_path))
                    results.append(result)
                except Exception as e:
                    print(f"  ❌ Error processing {file_path}: {e}")
        
        print(f"\n✅ Processed {len(results)} files")
        return results

def main():
    """CLI interface"""
    if len(sys.argv) < 3:
        print("""
Usage: python docling_processor.py <file_or_dir> <app_name>

Examples:
  python docling_processor.py document.pdf duckdb
  python docling_processor.py /docs/folder/ openspg
  
Supported formats: PDF, DOCX, HTML, PPTX
        """)
        sys.exit(1)
    
    path = sys.argv[1]
    app_name = sys.argv[2]
    
    # Check S3 credentials
    if not os.getenv("S3_ACCESS_KEY") or not os.getenv("S3_SECRET_KEY"):
        print("⚠️  Warning: S3 credentials not set!")
        print("   Set S3_ACCESS_KEY and S3_SECRET_KEY environment variables")
        print("   Files will be converted but not uploaded to S3")
    
    processor = DoclingProcessor(app_name)
    
    if os.path.isfile(path):
        result = processor.process_file(path)
        print(f"\n📊 Result:")
        print(f"   Words: {result['metadata']['word_count']}")
        print(f"   S3: {result['s3_processed']}")
    elif os.path.isdir(path):
        results = processor.process_directory(path)
        total_words = sum(r['metadata']['word_count'] for r in results)
        print(f"\n📊 Summary:")
        print(f"   Files: {len(results)}")
        print(f"   Total words: {total_words}")
    else:
        print(f"❌ Error: {path} not found")
        sys.exit(1)

if __name__ == "__main__":
    main()
