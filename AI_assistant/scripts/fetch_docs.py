#!/usr/bin/env python3
import os
import sys
import requests
from pathlib import Path

# Fix Unicode encoding for Windows
if sys.platform == "win32":
    # Set console to UTF-8 mode
    os.system("chcp 65001 > nul 2>&1")
    # Reconfigure stdout to use UTF-8
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')

# 🎯 NEW: Clean content folder structure
DOCS_DIR = "content"
BUCKET_URL = "https://sw-dl-bucket.s3.us-east-2.amazonaws.com/docs"

# Your exact files from S3
DOCS_FILES = [
    "About.md",
    "cookie_policy.md",
    "jazzcompletecopy.md",
    "marketing_policy.md",
    "privacy_policy.md",
    "rechannelcopy.md",
    "refund_policy.md",
    "reMIDI_4_installation_instructions.md",
    "reMIDI_4_user_manual.md",
    "remidi4copy.md",
    "sampleloops1copy.md",
    "sampleloops2copy.md",
    "songwish_landing_page.md",
    "support.md",
    "terms_and_conditions.md"
]

def safe_print(message):
    """Print with fallback for Unicode characters"""
    try:
        print(message)
    except UnicodeEncodeError:
        # Replace Unicode characters with ASCII equivalents
        safe_message = (message
                       .replace("📄", "[FILE]")
                       .replace("✅", "[OK]")
                       .replace("⚠️", "[WARN]")
                       .replace("❌", "[ERROR]")
                       .replace("→", "->"))
        print(safe_message)

def fetch_docs():
    safe_print(f"Fetching docs from {BUCKET_URL} -> {DOCS_DIR}")
   
    # Create content directory
    Path(DOCS_DIR).mkdir(parents=True, exist_ok=True)
   
    download_count = 0
    session = requests.Session()
    session.timeout = 30
   
    for filename in DOCS_FILES:
        url = f"{BUCKET_URL}/{filename}"
        target_path = Path(DOCS_DIR) / filename
       
        try:
            safe_print(f"📄 Downloading: {filename}")
            response = session.get(url)
            response.raise_for_status()
           
            # Skip empty files (like support.md with 0 chars)
            if len(response.text.strip()) == 0:
                safe_print(f"   ⚠️  Skipping empty file")
                continue
               
            target_path.write_text(response.text, encoding='utf-8')
            download_count += 1
            safe_print(f"   ✅ Success ({len(response.text)} chars)")
           
        except requests.RequestException as e:
            safe_print(f"   ⚠️  Failed: {e}")
            continue
   
    safe_print(f"✅ Downloaded {download_count}/{len(DOCS_FILES)} files successfully")
   
    if download_count > 0:
        safe_print("📄 Content files:")
        for file in sorted(Path(DOCS_DIR).glob("*.md")):
            size = file.stat().st_size
            safe_print(f"   {file.name} ({size:,} bytes)")
        return True
    else:
        safe_print("❌ No files were downloaded!")
        return False

if __name__ == "__main__":
    success = fetch_docs()
    exit(0 if success else 1)