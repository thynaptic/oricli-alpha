import time
import uuid
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from oricli_core.client import OricliAlphaClient

def test_rag_ingestion():
    client = OricliAlphaClient(base_url="http://localhost:8081", api_key="test_key")
    
    unique_id = str(uuid.uuid4())[:8]
    secret_knowledge = f"The secret password for project phoenix is 'FLAMINGO-{unique_id}'."
    source_name = f"test_secret_{unique_id}.txt"
    
    print(f"[*] Ingesting secret knowledge: {secret_knowledge}")
    
    # 1. Ingest text
    ingest_res = client.knowledge.ingest(
        text=secret_knowledge,
        metadata={"source": source_name, "tags": ["test", "secret"]}
    )
    
    if not ingest_res.get("success"):
        print(f"[!] Ingestion failed: {ingest_res}")
        return
    
    print(f"[+] Ingestion successful. Processed {ingest_res.get('chunks_processed')} chunks.")
    
    # Wait for indexing
    print("[*] Waiting for indexing...")
    time.sleep(5)
    
    # 2. Query Hive
    query = "What is the secret password for project phoenix?"
    print(f"[*] Querying Hive: {query}")
    
    response = client.chat.completions.create(
        model="oricli-swarm",
        messages=[{"role": "user", "content": query}]
    )
    
    content = response.choices[0].message.content
    print(f"\n[HIVE RESPONSE]:\n{content}\n")
    
    if f"FLAMINGO-{unique_id}" in content:
        print("[SUCCESS] RAG pipeline verified! Ingested knowledge was retrieved.")
    else:
        print("[FAILURE] RAG pipeline failed. Knowledge not found in response.")

if __name__ == "__main__":
    test_rag_ingestion()
