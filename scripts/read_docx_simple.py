import zipfile
import re
import sys
import os

def read_docx(file_path):
    try:
        with zipfile.ZipFile(file_path) as zf:
            xml_content = zf.read('word/document.xml').decode('utf-8')
            # Simple regex to strip XML tags
            text = re.sub('<[^<]+?>', '', xml_content)
            print(text)
    except Exception as e:
        print(f"Error reading docx: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python read_docx.py <file_path>")
        sys.exit(1)
    read_docx(sys.argv[1])
