from __future__ import annotations
"""
URL/API Data Source

Streams questions from HTTP/HTTPS endpoints and REST APIs.
"""

import json
import os
from typing import Any, Dict, Iterator, Optional

from oricli_core.evaluation.curriculum.data_sources.base import BaseDataSource

# Lazy import
REQUESTS_AVAILABLE = None
requests = None


def _lazy_import_requests():
    """Lazy import requests"""
    global REQUESTS_AVAILABLE, requests
    if REQUESTS_AVAILABLE is None:
        try:
            import requests as req
            requests = req
            REQUESTS_AVAILABLE = True
        except ImportError:
            REQUESTS_AVAILABLE = False
    return REQUESTS_AVAILABLE


class URLSource(BaseDataSource):
    """URL/API-based data source"""
    
    def __init__(
        self,
        url: str,
        name: Optional[str] = None,
        auth: Optional[Dict[str, Any]] = None,
        field_mapping: Optional[Dict[str, str]] = None,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize URL source
        
        Args:
            url: Base URL or API endpoint
            name: Source name (defaults to URL)
            auth: Authentication configuration
            field_mapping: Field mapping dictionary
            method: HTTP method (GET, POST, etc.)
            headers: Custom headers
        """
        self.url = url
        self.name = name or url
        self.auth = auth or {}
        self.field_mapping = field_mapping or {}
        self.method = method.upper()
        self.headers = headers or {}
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        headers = {}
        auth_type = self.auth.get("type", "").lower()
        
        if auth_type == "bearer":
            token_env = self.auth.get("token_env")
            if token_env:
                token = os.getenv(token_env)
                if token:
                    headers["Authorization"] = f"Bearer {token}"
        elif auth_type == "api_key":
            key_name = self.auth.get("key_name", "X-API-Key")
            key_env = self.auth.get("key_env")
            if key_env:
                key = os.getenv(key_env)
                if key:
                    headers[key_name] = key
        
        return headers
    
    def get_source_name(self) -> str:
        """Return source identifier"""
        return f"url:{self.name}"
    
    def supports_filtering(self) -> bool:
        """URL sources may support filtering via query params"""
        return True
    
    def stream_questions(
        self,
        level: str,
        subject: str,
        skill_type: Optional[str] = None,
        difficulty_style: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Iterator[Dict[str, Any]]:
        """
        Stream questions from URL/API
        
        Args:
            level: Education level
            subject: Subject domain
            skill_type: Skill type filter (optional)
            difficulty_style: Difficulty style filter (optional)
            limit: Maximum number of questions (optional)
        
        Yields:
            Question dictionaries
        """
        if not _lazy_import_requests():
            raise ImportError(
                "requests library not available. Install with: pip install requests"
            )
        
        # Build request parameters
        params = {
            "level": level,
            "subject": subject,
        }
        if skill_type:
            params["skill_type"] = skill_type
        if difficulty_style:
            params["difficulty_style"] = difficulty_style
        if limit:
            params["limit"] = limit
        
        # Get auth headers
        headers = {**self.headers, **self._get_auth_headers()}
        
        try:
            # Make request
            if self.method == "GET":
                response = requests.get(self.url, params=params, headers=headers, timeout=30)
            elif self.method == "POST":
                response = requests.post(self.url, json=params, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {self.method}")
            
            response.raise_for_status()
            
            # Parse response
            data = response.json()
            
            # Handle different response formats
            if isinstance(data, list):
                questions = data
            elif isinstance(data, dict):
                # Try common keys
                questions = data.get("questions", data.get("data", data.get("items", [])))
            else:
                questions = []
            
            # Transform and yield questions
            count = 0
            for item in questions:
                question = self._transform_api_item(item, level, subject)
                if question:
                    yield question
                    count += 1
                    if limit and count >= limit:
                        break
        except Exception:
            # Silently skip on errors
            return
    
    def _transform_api_item(
        self,
        item: Dict[str, Any],
        level: str,
        subject: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Transform API item to curriculum format
        
        Args:
            item: Raw item from API
            level: Education level
            subject: Subject domain
        
        Returns:
            Transformed question or None if invalid
        """
        try:
            # Apply field mapping
            question_text = item.get(
                self.field_mapping.get("question", "question"),
                item.get("text", item.get("prompt", ""))
            )
            answer = item.get(
                self.field_mapping.get("answer", "answer"),
                item.get("solution", item.get("response", ""))
            )
            
            if not question_text:
                return None
            
            # Build curriculum format question
            question = {
                "id": item.get("id", f"url_{hash(str(item))}"),
                "question": question_text,
                "answer": str(answer),
                "level": item.get(self.field_mapping.get("level", "level"), level),
                "subject": item.get(self.field_mapping.get("subject", "subject"), subject),
                "skill_type": item.get("skill_type", "foundational"),
                "difficulty_style": item.get("difficulty_style", "standard"),
                "question_type": item.get("question_type", "free_response"),
                "metadata": {
                    "estimated_time": item.get("estimated_time", 30.0),
                    "estimated_tokens": item.get("estimated_tokens", 200),
                    "expected_reasoning_steps": item.get("expected_reasoning_steps", 3),
                },
            }
            
            # Add options if available
            if "options" in item:
                question["options"] = item["options"]
                question["question_type"] = "multiple_choice"
            
            return question
        except Exception:
            return None

