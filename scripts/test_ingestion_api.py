#!/usr/bin/env python3
"""
Test script for the Sovereign Ingestion API.
"""

import sys
from pathlib import Path
import json
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from oricli_core.client import OricliAlphaClient

def test_ingestion():
    print("\n--- Testing Sovereign Ingestion API ---")
    client = OricliAlphaClient(base_url="http://localhost:8080", api_key="test_key")
    
    # 1. Test Text Ingestion
    print("1. Testing raw text ingestion...")
    try:
        text_payload = "Oricli-Alpha was recently upgraded with a Sovereign Ingestion API. This allows her to learn from external PDFs and documents in real-time."
        res = client.knowledge.ingest(
            text=text_payload,
            metadata={"source": "test_script", "tags": ["upgrade", "ingestion"], "domain": "system_updates"}
        )
        print(f"   Success: {res.get('success')}, Chunks: {res.get('chunks_processed')}")
    except Exception as e:
        print(f"   Failed text ingestion: {e}")

    # 2. Test File Ingestion
    print("2. Testing file ingestion (dummy text file)...")
    dummy_file = Path("test_ingest.txt")
    dummy_file.write_text("This is a test document about Oricli's RAG capabilities. It contains important facts that the Hive should remember.")
    
    try:
        res = client.knowledge.ingest(
            file_path=str(dummy_file),
            metadata={"tags": ["rag", "test"], "domain": "documentation"}
        )
        print(f"   Success: {res.get('success')}, Chunks: {res.get('chunks_processed')}")
    except Exception as e:
        print(f"   Failed file ingestion: {e}")
    finally:
        if dummy_file.exists():
            dummy_file.unlink()

    # 3. Test RAG Retrieval
    print("3. Verifying retrieval via Chat Completion...")
    try:
        # Give it a second to sync
        time.sleep(2)
        response = client.chat.completions.create(
            model="oricli-swarm",
            messages=[{"role": "user", "content": "What was Oricli-Alpha recently upgraded with?"}],
            max_tokens=100
        )
        print("\n--- Hive Response ---")
        print(response.choices[0].message.content)
        print("---------------------")
    except Exception as e:
        print(f"   Retrieval test failed: {e}")

if __name__ == "__main__":
    test_ingestion()
