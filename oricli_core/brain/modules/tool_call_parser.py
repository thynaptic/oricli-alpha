from __future__ import annotations
"""
Tool Call Parser - Parser for extracting tool calls from model responses
Mirrors Swift ToolCallParser.swift functionality
"""

import json
import re
from typing import List, Optional
try:
    from oricli_core.brain.modules.tool_calling_models import ToolCall, ToolCallFunction
except ImportError:
    from tool_calling_models import ToolCall, ToolCallFunction


class ToolCallParser:
    """Parser for extracting tool calls from model responses"""
    
    _instance: Optional["ToolCallParser"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
    
    # MARK: - Parsing
    
    def parse_tool_calls(self, response: str) -> List[ToolCall]:
        """Parse tool calls from a response string"""
        # Try to extract JSON from response
        json_data = self._extract_json(response)
        if json_data:
            return self._parse_tool_calls_from_json(json_data)
        
        # Try to find tool_calls in text format
        return self._parse_tool_calls_from_text(response)
    
    def extract_tool_calls_from_json(self, json_data: bytes) -> List[ToolCall]:
        """Extract tool calls from JSON data"""
        return self._parse_tool_calls_from_json(json_data.decode("utf-8"))
    
    # MARK: - JSON Parsing
    
    def _parse_tool_calls_from_json(self, json_string: str) -> List[ToolCall]:
        """Parse tool calls from JSON string"""
        try:
            data = json.loads(json_string)
            
            # Handle different JSON structures
            tool_calls_data = None
            if isinstance(data, dict):
                tool_calls_data = data.get("tool_calls") or data.get("toolCalls")
            elif isinstance(data, list):
                tool_calls_data = data
            
            if not tool_calls_data:
                return []
            
            parsed_calls: List[ToolCall] = []
            
            for call_data in tool_calls_data:
                if isinstance(call_data, dict):
                    function_data = call_data.get("function") or call_data.get("function")
                    if not function_data:
                        continue
                    
                    name = function_data.get("name")
                    arguments_str = function_data.get("arguments")
                    
                    if not name:
                        continue
                    
                    # Parse arguments (may be string or dict)
                    if isinstance(arguments_str, str):
                        try:
                            arguments = json.loads(arguments_str)
                        except json.JSONDecodeError:
                            arguments = {}
                    elif isinstance(arguments_str, dict):
                        arguments = arguments_str
                    else:
                        arguments = {}
                    
                    tool_call = ToolCall(
                        index=call_data.get("index"),
                        function=ToolCallFunction(name=name, arguments=arguments)
                    )
                    parsed_calls.append(tool_call)
            
            return parsed_calls
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            return []
    
    # MARK: - Text Parsing
    
    def _parse_tool_calls_from_text(self, text: str) -> List[ToolCall]:
        """Parse tool calls from text using regex patterns"""
        tool_calls: List[ToolCall] = []
        
        # Pattern: tool_call: function_name(arg1="value1", arg2="value2")
        pattern = r'tool_call:\s*(\w+)\s*\(([^)]+)\)'
        
        matches = re.finditer(pattern, text)
        
        for match in matches:
            if match.lastindex >= 2:
                function_name = match.group(1)
                arguments_string = match.group(2)
                
                # Parse arguments (simple key="value" format)
                arguments: dict = {}
                arg_pattern = r'(\w+)\s*=\s*"([^"]+)"'
                arg_matches = re.finditer(arg_pattern, arguments_string)
                
                for arg_match in arg_matches:
                    if arg_match.lastindex >= 2:
                        key = arg_match.group(1)
                        value = arg_match.group(2)
                        arguments[key] = value
                
                tool_call = ToolCall(
                    index=None,
                    function=ToolCallFunction(name=function_name, arguments=arguments)
                )
                tool_calls.append(tool_call)
        
        return tool_calls
    
    # MARK: - JSON Extraction
    
    def _extract_json(self, text: str) -> Optional[str]:
        """Extract JSON from text (may be in markdown code blocks)"""
        # Try to find JSON in markdown code blocks
        json_pattern = r'```json\s*(\{.*?\})\s*```'
        match = re.search(json_pattern, text, re.DOTALL)
        if match:
            return match.group(1)
        
        # Try to find JSON object directly
        start_idx = text.find("{")
        if start_idx != -1:
            end_idx = text.rfind("}")
            if end_idx != -1 and end_idx > start_idx:
                return text[start_idx:end_idx + 1]
        
        return None


# Global singleton instance
tool_call_parser = ToolCallParser()

