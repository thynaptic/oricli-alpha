from __future__ import annotations
"""
Web Ingestion Agent Module
Autonomous web crawler that ingests articles and blogs into the Hive.
Integrates with web_scraper for extraction and ingestion_agent for indexing.
"""

import time
import logging
import urllib.parse
from typing import Any, Dict, List, Set, Optional
from collections import deque

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.brain.registry import ModuleRegistry
from oricli_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)

class WebIngestionAgentModule(BaseBrainModule):
    """Orchestrates autonomous web crawling and ingestion."""

    def __init__(self):
        super().__init__()
        self._scraper = None
        self._ingestor = None
        self._initialized = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="web_ingestion_agent",
            version="1.0.0",
            description="Autonomous web crawler for ingesting online articles and blogs.",
            operations=[
                "crawl_and_ingest",
                "status"
            ],
            dependencies=["requests", "beautifulsoup4"],
            enabled=True,
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize and link dependencies."""
        try:
            self._scraper = ModuleRegistry.get_module("web_scraper")
            self._ingestor = ModuleRegistry.get_module("ingestion_agent")
            self._initialized = True
            return True
        except Exception as e:
            logger.warning(f"WebIngestionAgent dependencies partially loaded: {e}")
            return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute web ingestion operations."""
        if operation == "status":
            return {"success": True, "scraper_ready": self._scraper is not None}

        if operation == "crawl_and_ingest":
            return self._crawl_and_ingest(params)
        else:
            raise InvalidParameterError(parameter="operation", value=operation, reason="Unsupported operation")

    def _crawl_and_ingest(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Breadth-first crawl and ingest content."""
        seed_url = params.get("url")
        max_pages = int(params.get("max_pages", 5))
        max_depth = int(params.get("max_depth", 2))
        metadata = params.get("metadata", {})
        
        if not seed_url:
            return {"success": False, "error": "Seed URL is required"}

        if not self._scraper or not self._ingestor:
            return {"success": False, "error": "Required modules (web_scraper or ingestion_agent) not available"}

        domain = urllib.parse.urlparse(seed_url).netloc
        queue = deque([(seed_url, 0)]) # (url, depth)
        visited: Set[str] = {seed_url}
        ingested_urls: List[str] = []
        total_chunks = 0

        while queue and len(ingested_urls) < max_pages:
            url, depth = queue.popleft()
            
            # 1. Scrape content
            logger.info(f"Crawling: {url} (Depth: {depth})")
            scrape_res = self._scraper.execute("scrape_url", {"url": url})
            
            if scrape_res.get("success"):
                result = scrape_res.get("result", {})
                title = result.get("title", "Untitled")
                content = result.get("content", "")
                
                if content:
                    # 2. Ingest into Hive
                    ingest_meta = {**metadata, "url": url, "title": title, "source_type": "web"}
                    ingest_res = self._ingestor.execute("ingest_text", {
                        "text": content,
                        "metadata": ingest_meta
                    })
                    
                    if ingest_res.get("success"):
                        ingested_urls.append(url)
                        total_chunks += ingest_res.get("chunks_processed", 0)

                # 3. Extract links for further crawling
                if depth < max_depth:
                    links_res = self._scraper.execute("extract_links", {"url": url})
                    if links_res.get("success"):
                        for link_obj in links_res.get("result", {}).get("links", []):
                            link = link_obj.get("url")
                            if link and link not in visited:
                                # Stay within same domain to avoid runaway crawl
                                if urllib.parse.urlparse(link).netloc == domain:
                                    visited.add(link)
                                    queue.append((link, depth + 1))

            # Small delay to be polite
            time.sleep(1.0)

        return {
            "success": True,
            "seed_url": seed_url,
            "pages_ingested": len(ingested_urls),
            "total_chunks": total_chunks,
            "urls": ingested_urls
        }
