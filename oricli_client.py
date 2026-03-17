import requests
import json
import os
import time
import base64
from typing import Dict, Any, List, Optional, Union

class OricliClient:
    """Lean Python client for Oricli-Alpha Pure-Go Backbone v2.0"""
    
    def __init__(self, base_url: str = "http://localhost:8089", api_key: str = "test_key", tenant_id: str = "local"):
        self.base_url = base_url
        self.api_key = api_key
        self.tenant_id = tenant_id
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "X-Tenant-ID": tenant_id,
            "Content-Type": "application/json"
        }

    def health(self) -> Dict[str, Any]:
        return requests.get(f"{self.base_url}/v1/health", headers=self.headers).json()

    def chat(self, prompt: str, model: str = "oricli-cognitive") -> str:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}]
        }
        resp = requests.post(f"{self.base_url}/v1/chat/completions", headers=self.headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def ingest_text(self, text: str, source: str = "direct", metadata: Optional[Dict] = None) -> Dict[str, Any]:
        payload = {
            "operation": "ingest_text",
            "params": {
                "text": text,
                "source": source,
                "metadata": metadata or {}
            }
        }
        return requests.post(f"{self.base_url}/v1/swarm/run", headers=self.headers, json=payload).json()

    def ingest_file(self, file_path: str) -> Dict[str, Any]:
        url = f"{self.base_url}/v1/ingest"
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f)}
            # Multipart requires different headers
            headers = self.headers.copy()
            del headers["Content-Type"] 
            return requests.post(url, headers=headers, files=files).json()

    def crawl(self, target_url: str, max_pages: int = 5) -> Dict[str, Any]:
        payload = {"url": target_url, "max_pages": max_pages}
        return requests.post(f"{self.base_url}/v1/ingest/web", headers=self.headers, json=payload).json()

    def solve_arc(self, task: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "operation": "solve_arc",
            "params": {"task": task}
        }
        return requests.post(f"{self.base_url}/v1/swarm/run", headers=self.headers, json=payload).json()

    def memory_search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        payload = {
            "operation": "vector_search",
            "params": {"query": query, "limit": limit}
        }
        return requests.post(f"{self.base_url}/v1/swarm/run", headers=self.headers, json=payload).json()

