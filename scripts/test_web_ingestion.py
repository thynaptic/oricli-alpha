#!/usr/bin/env python3
"""
Test script for the Sovereign Web Ingestion API.
"""

import sys
from pathlib import Path
import json
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from oricli_core.client import OricliAlphaClient

def test_web_ingestion():
    print("\n--- Testing Sovereign Web Ingestion API ---")
    client = OricliAlphaClient(base_url="http://localhost:8080", api_key="test_key")
    
    # Test URL (using a simple, stable technical site or local mock if needed)
    # For testing, we'll use a known public documentation page
    target_url = "https://docs.python.org/3/library/intro.html"
    
    print(f"1. Triggering crawl and ingestion for: {target_url}...")
    try:
        res = client.knowledge.ingest_web(
            url=target_url,
            max_pages=2,
            max_depth=1,
            metadata={"tags": ["python", "docs"], "domain": "programming"}
        )
        print(f"   Success: {res.get('success')}")
        print(f"   Pages Ingested: {res.get('pages_ingested')}")
        print(f"   Total Chunks: {res.get('total_chunks')}")
        print(f"   URLs: {res.get('urls')}")
    except Exception as e:
        print(f"   Failed web ingestion: {e}")

    # 2. Test RAG Retrieval
    print("\n2. Verifying retrieval via Chat Completion...")
    try:
        # Give it a second to sync
        time.sleep(2)
        response = client.chat.completions.create(
            model="oricli-swarm",
            messages=[{"role": "user", "content": "What does the Python standard library provide according to the documentation?"}],
            max_tokens=100
        )
        print("\n--- Hive Response ---")
        print(response.choices[0].message.content)
        print("---------------------")
    except Exception as e:
        print(f"   Retrieval test failed: {e}")

if __name__ == "__main__":
    test_web_ingestion()
