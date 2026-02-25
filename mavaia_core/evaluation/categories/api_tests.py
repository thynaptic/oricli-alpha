from __future__ import annotations
"""
API Test Executor

Tests all HTTP API endpoints including OpenAI-compatible endpoints
and Mavaia-specific endpoints.
"""

import time
from typing import Any, Dict, List, Optional
from pathlib import Path

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from mavaia_core.evaluation.test_data_manager import TestCase
from mavaia_core.evaluation.test_results import TestResult, TestStatus


class APITestRunner:
    """Runs tests for API endpoints"""
    
    def __init__(self, base_url: str = "http://localhost:8000", api_key: Optional[str] = None):
        """
        Initialize API test executor
        
        Args:
            base_url: Base URL for API server
            api_key: Optional API key for authentication
        """
        if not HTTPX_AVAILABLE:
            raise ImportError(
                "httpx is required for API tests. Install with: pip install httpx"
            )
        
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client = httpx.Client(timeout=30.0)
    
    def __del__(self):
        """Cleanup client"""
        if hasattr(self, "client"):
            self.client.close()
    
    def run_test_case(
        self,
        test_case: TestCase,
        timeout: Optional[float] = None
    ) -> TestResult:
        """
        Run a single API test case
        
        Args:
            test_case: Test case to run
            timeout: Optional timeout override
            
        Returns:
            TestResult instance
        """
        test_timeout = timeout or test_case.timeout
        start_time = time.time()
        
        result = TestResult(
            test_id=test_case.id,
            module=test_case.module,  # May be endpoint name
            category=test_case.category,
            operation=test_case.operation,  # May be HTTP method
        )
        
        try:
            # Skip if marked as skip
            if test_case.skip:
                result.status = TestStatus.SKIPPED
                result.execution_time = time.time() - start_time
                return result
            
            # Extract endpoint and method from test case
            endpoint = test_case.params.get("endpoint", "/")
            method = test_case.params.get("method", "GET").upper()
            headers = test_case.params.get("headers", {})
            body = test_case.params.get("body")
            query_params = test_case.params.get("query_params", {})
            
            # Add API key to headers if provided
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            # Build URL
            url = f"{self.base_url}{endpoint}"
            
            # Make request
            response = self.client.request(
                method=method,
                url=url,
                headers=headers,
                json=body if body else None,
                params=query_params,
                timeout=test_timeout
            )
            
            # Validate response
            validation_errors = self._validate_response(
                test_case,
                response
            )
            
            if validation_errors:
                result.status = TestStatus.FAILED
                result.error_message = "; ".join(validation_errors)
                result.error_type = "ValidationError"
            else:
                result.status = TestStatus.PASSED
                result.result_data = {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                }
            
            result.execution_time = time.time() - start_time
            
        except httpx.TimeoutException:
            result.status = TestStatus.TIMEOUT
            result.error_message = f"Request timeout after {test_timeout}s"
            result.error_type = "TimeoutError"
            result.execution_time = time.time() - start_time
            
        except httpx.HTTPStatusError as e:
            result.status = TestStatus.FAILED
            result.error_message = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            result.error_type = "HTTPStatusError"
            result.execution_time = time.time() - start_time
            
        except Exception as e:
            result.status = TestStatus.ERROR
            result.error_message = str(e)
            result.error_type = type(e).__name__
            result.execution_time = time.time() - start_time
        
        return result
    
    def _validate_response(
        self,
        test_case: TestCase,
        response: httpx.Response
    ) -> List[str]:
        """
        Validate API response
        
        Args:
            test_case: Test case with expected values
            response: HTTP response
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        expected = test_case.expected
        
        if not expected:
            return errors
        
        # Check status code
        if "status_code" in expected:
            expected_status = expected["status_code"]
            if response.status_code != expected_status:
                errors.append(
                    f"Expected status {expected_status}, got {response.status_code}"
                )
        
        # Check response body
        if "body" in expected:
            try:
                response_data = response.json()
                expected_body = expected["body"]
                
                # Check if response contains expected fields
                if isinstance(expected_body, dict):
                    for key, value in expected_body.items():
                        if key not in response_data:
                            errors.append(f"Missing field in response: {key}")
                        elif response_data[key] != value:
                            errors.append(
                                f"Field '{key}' expected '{value}', got '{response_data[key]}'"
                            )
            except Exception:
                # Not JSON, check text
                if "body" in expected and response.text != expected["body"]:
                    errors.append("Response body does not match expected")
        
        # Check response headers
        if "headers" in expected:
            expected_headers = expected["headers"]
            for header, value in expected_headers.items():
                if header.lower() not in [h.lower() for h in response.headers.keys()]:
                    errors.append(f"Missing header: {header}")
                elif response.headers[header.lower()] != value:
                    errors.append(
                        f"Header '{header}' expected '{value}', "
                        f"got '{response.headers[header.lower()]}'"
                    )
        
        return errors
    
    def run_test_suite(
        self,
        test_cases: List[TestCase],
        timeout: Optional[float] = None
    ) -> List[TestResult]:
        """
        Run a suite of API test cases
        
        Args:
            test_cases: List of test cases to run
            timeout: Optional timeout override for all tests
            
        Returns:
            List of test results
        """
        results = []
        
        for test_case in test_cases:
            result = self.run_test_case(test_case, timeout)
            results.append(result)
        
        return results

