"""
Memory Tool Module

Implements Claude Memory Tool functionality for persistent memory storage across conversations.
Supports all 6 memory operations: view, create, str_replace, insert, delete, rename.
All operations are restricted to the /memories directory for security.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import re

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import ModuleOperationError, InvalidParameterError

# Lazy imports to avoid timeout during module discovery
DatabaseStorage = None
StorageConfig = None

def _lazy_import_storage():
    """Lazy import storage components only when needed"""
    global DatabaseStorage, StorageConfig
    if DatabaseStorage is None:
        try:
            from mavaia_core.brain.state_storage.db_storage import DatabaseStorage as DS
            from mavaia_core.brain.state_storage.base_storage import StorageConfig as SC
            DatabaseStorage = DS
            StorageConfig = SC
        except ImportError:
            pass


class MemoryToolModule(BaseBrainModule):
    """
    Memory Tool Module for Claude Memory Tool operations.
    
    Provides persistent memory storage across conversations using database storage.
    All file operations are restricted to the /memories directory.
    """
    
    MEMORY_DIRECTORY = "/memories"
    STATE_TYPE = "memory_file"
    
    def __init__(self):
        """Initialize memory tool module."""
        super().__init__()
        self._storage: Optional[DatabaseStorage] = None
    
    @property
    def metadata(self) -> ModuleMetadata:
        """Return module metadata."""
        return ModuleMetadata(
            name="memory_tool",
            version="1.0.0",
            description="Claude Memory Tool - persistent memory storage across conversations",
            operations=[
                "view",
                "create",
                "str_replace",
                "insert",
                "delete",
                "rename",
            ],
            dependencies=[],
            enabled=True,
            model_required=False,
        )
    
    def initialize(self) -> bool:
        """Initialize the module and storage backend."""
        # Don't initialize storage here - it's heavy, will initialize lazily
        return True
    
    def _ensure_storage(self):
        """Lazy initialize storage only when needed"""
        _lazy_import_storage()
        if DatabaseStorage is None or StorageConfig is None:
            raise RuntimeError("DatabaseStorage not available")
        if self._storage is None:
            try:
                config = StorageConfig(
                    storage_type="database",
                    storage_path=None,  # Use default path
                )
                self._storage = DatabaseStorage(config)
                self._storage.initialize()
            except Exception as e:
                print(f"[MemoryTool] Failed to initialize storage: {e}")
                raise
    
    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a memory tool operation."""
        self._ensure_storage()
        
        try:
            if operation == "view":
                return self._view(params)
            elif operation == "create":
                return self._create(params)
            elif operation == "str_replace":
                return self._str_replace(params)
            elif operation == "insert":
                return self._insert(params)
            elif operation == "delete":
                return self._delete(params)
            elif operation == "rename":
                return self._rename(params)
            else:
                raise ValueError(f"Unknown operation: {operation}")
        except (InvalidParameterError, ValueError) as e:
            raise ModuleOperationError(
                self.metadata.name,
                operation,
                str(e),
            )
        except Exception as e:
            raise ModuleOperationError(
                self.metadata.name,
                operation,
                f"Unexpected error: {str(e)}",
            )
    
    def _validate_memory_path(self, path: str) -> str:
        """
        Validate and normalize a memory path.
        
        Args:
            path: Path to validate
            
        Returns:
            Normalized path
            
        Raises:
            ValueError: If path is invalid or outside /memories directory
        """
        if not path:
            raise ValueError("Path cannot be empty")
        
        # Normalize path separators
        normalized = path.replace("\\", "/")
        
        # Ensure path starts with /memories
        if not normalized.startswith(self.MEMORY_DIRECTORY):
            raise ValueError(
                f"Path must start with {self.MEMORY_DIRECTORY}. Got: {path}"
            )
        
        # Prevent directory traversal
        if ".." in normalized:
            raise ValueError("Directory traversal (..) not allowed")
        
        # Prevent absolute paths outside /memories
        parts = normalized.split("/")
        if parts[0] == "" and len(parts) > 1 and parts[1] != "memories":
            raise ValueError(f"Path must be within {self.MEMORY_DIRECTORY}")
        
        # Normalize to remove double slashes and trailing slashes (except for root)
        normalized = "/".join(part for part in parts if part)
        if normalized == "memories":
            normalized = "/memories"
        else:
            normalized = "/" + normalized
        
        return normalized
    
    def _get_file_data(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Get file data from storage.
        
        Args:
            file_path: Normalized file path
            
        Returns:
            File data dictionary or None if not found
        """
        return self._storage.load(self.STATE_TYPE, file_path)
    
    def _save_file_data(self, file_path: str, content: str) -> bool:
        """
        Save file data to storage.
        
        Args:
            file_path: Normalized file path
            content: File content
            
        Returns:
            True if saved successfully
        """
        lines = content.split("\n")
        file_data = {
            "content": content,
            "lines": lines,
        }
        return self._storage.save(self.STATE_TYPE, file_path, file_data)
    
    def _is_directory(self, path: str) -> bool:
        """
        Check if a path represents a directory.
        
        Args:
            path: Normalized path
            
        Returns:
            True if path is a directory
        """
        # Check if path ends with / or if there are files with this path as prefix
        if path.endswith("/") or path == self.MEMORY_DIRECTORY:
            return True
        
        # Check if there are any files with this path as a prefix
        all_states = self._storage.list_states(self.STATE_TYPE)
        for state in all_states:
            state_id = state["state_id"]
            if state_id.startswith(path + "/"):
                return True
        
        return False
    
    def _list_directory(self, dir_path: str) -> List[str]:
        """
        List contents of a directory.
        
        Args:
            dir_path: Normalized directory path
            
        Returns:
            List of file/directory names in the directory
        """
        if not dir_path.endswith("/"):
            dir_path = dir_path + "/"
        
        all_states = self._storage.list_states(self.STATE_TYPE)
        items = set()
        
        for state in all_states:
            state_id = state["state_id"]
            if state_id.startswith(dir_path):
                # Get the relative path from dir_path
                relative = state_id[len(dir_path):]
                if relative:
                    # Get the first component (file or subdirectory name)
                    first_component = relative.split("/")[0]
                    items.add(first_component)
        
        return sorted(list(items))
    
    def _view(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        View operation: List directory contents or read specific file lines.
        
        Args:
            path: Path to view (directory or file)
            start_line: Optional start line number (1-indexed)
            end_line: Optional end line number (1-indexed)
            
        Returns:
            Dictionary with directory listing or file content
        """
        path = params.get("path")
        if not path:
            raise InvalidParameterError("path", None, "path parameter is required")
        
        path = self._validate_memory_path(path)
        
        # Check if it's a directory
        if self._is_directory(path):
            items = self._list_directory(path)
            return {
                "success": True,
                "type": "directory",
                "path": path,
                "items": items,
            }
        
        # It's a file - get file data
        file_data = self._get_file_data(path)
        if file_data is None:
            return {
                "success": False,
                "error": f"File not found: {path}",
            }
        
        lines = file_data.get("lines", [])
        content = file_data.get("content", "")
        
        # Check if specific lines are requested
        start_line = params.get("start_line")
        end_line = params.get("end_line")
        
        if start_line is not None or end_line is not None:
            # Validate line numbers
            if start_line is not None and (start_line < 1 or start_line > len(lines)):
                raise InvalidParameterError(
                    "start_line",
                    start_line,
                    f"start_line must be between 1 and {len(lines)}"
                )
            if end_line is not None and (end_line < 1 or end_line > len(lines)):
                raise InvalidParameterError(
                    "end_line",
                    end_line,
                    f"end_line must be between 1 and {len(lines)}"
                )
            if start_line is not None and end_line is not None and start_line > end_line:
                raise InvalidParameterError(
                    "start_line, end_line",
                    f"{start_line}, {end_line}",
                    "start_line must be <= end_line"
                )
            
            # Extract requested lines (1-indexed)
            start_idx = (start_line or 1) - 1
            end_idx = end_line or len(lines)
            selected_lines = lines[start_idx:end_idx]
            selected_content = "\n".join(selected_lines)
            
            return {
                "success": True,
                "type": "file",
                "path": path,
                "content": selected_content,
                "lines": selected_lines,
                "start_line": start_line or 1,
                "end_line": end_line or len(lines),
                "total_lines": len(lines),
            }
        
        # Return full file
        return {
            "success": True,
            "type": "file",
            "path": path,
            "content": content,
            "lines": lines,
            "total_lines": len(lines),
        }
    
    def _create(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create operation: Create or overwrite a memory file.
        
        Args:
            path: File path to create
            content: File content
            
        Returns:
            Success status
        """
        path = params.get("path")
        content = params.get("content", "")
        
        if not path:
            raise InvalidParameterError("path", None, "path parameter is required")
        
        path = self._validate_memory_path(path)
        
        # Ensure path doesn't end with / (it's a file, not directory)
        if path.endswith("/"):
            raise InvalidParameterError(
                "path",
                path,
                "File path cannot end with /"
            )
        
        # Save file
        if self._save_file_data(path, content):
            return {
                "success": True,
                "path": path,
                "message": f"File created: {path}",
            }
        else:
            return {
                "success": False,
                "error": f"Failed to create file: {path}",
            }
    
    def _str_replace(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        String replace operation: Replace text within a file.
        
        Args:
            path: File path
            old_str: Text to replace
            new_str: Replacement text
            
        Returns:
            Success status
        """
        path = params.get("path")
        old_str = params.get("old_str")
        new_str = params.get("new_str", "")
        
        if not path:
            raise InvalidParameterError("path", None, "path parameter is required")
        if old_str is None:
            raise InvalidParameterError("old_str", None, "old_str parameter is required")
        
        path = self._validate_memory_path(path)
        
        # Get existing file
        file_data = self._get_file_data(path)
        if file_data is None:
            return {
                "success": False,
                "error": f"File not found: {path}",
            }
        
        content = file_data.get("content", "")
        
        # Perform replacement
        if old_str not in content:
            return {
                "success": False,
                "error": f"Text not found in file: {path}",
            }
        
        new_content = content.replace(old_str, new_str, 1)  # Replace first occurrence
        
        # Save updated file
        if self._save_file_data(path, new_content):
            return {
                "success": True,
                "path": path,
                "message": f"Text replaced in file: {path}",
            }
        else:
            return {
                "success": False,
                "error": f"Failed to update file: {path}",
            }
    
    def _insert(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Insert operation: Insert text at a specific line number.
        
        Args:
            path: File path
            line: Line number to insert at (1-indexed)
            content: Text to insert
            
        Returns:
            Success status
        """
        path = params.get("path")
        line = params.get("line")
        content = params.get("content", "")
        
        if not path:
            raise InvalidParameterError("path", None, "path parameter is required")
        if line is None:
            raise InvalidParameterError("line", None, "line parameter is required")
        
        path = self._validate_memory_path(path)
        
        # Validate line number
        if line < 1:
            raise InvalidParameterError(
                "line",
                line,
                "line must be >= 1"
            )
        
        # Get existing file
        file_data = self._get_file_data(path)
        if file_data is None:
            return {
                "success": False,
                "error": f"File not found: {path}",
            }
        
        lines = file_data.get("lines", [])
        
        # Validate line number is within bounds (allow inserting at end)
        if line > len(lines) + 1:
            raise InvalidParameterError(
                "line",
                line,
                f"line must be <= {len(lines) + 1} (file has {len(lines)} lines)"
            )
        
        # Insert content (split into lines if needed)
        content_lines = content.split("\n")
        
        # Insert at specified line (1-indexed -> 0-indexed)
        insert_idx = line - 1
        new_lines = lines[:insert_idx] + content_lines + lines[insert_idx:]
        new_content = "\n".join(new_lines)
        
        # Save updated file
        if self._save_file_data(path, new_content):
            return {
                "success": True,
                "path": path,
                "line": line,
                "message": f"Text inserted at line {line} in file: {path}",
            }
        else:
            return {
                "success": False,
                "error": f"Failed to update file: {path}",
            }
    
    def _delete(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Delete operation: Delete a memory file or directory.
        
        Args:
            path: Path to delete (file or directory)
            
        Returns:
            Success status
        """
        path = params.get("path")
        if not path:
            raise InvalidParameterError("path", None, "path parameter is required")
        
        path = self._validate_memory_path(path)
        
        # Check if it's a directory
        if self._is_directory(path):
            # Delete all files with this path as prefix
            all_states = self._storage.list_states(self.STATE_TYPE)
            deleted_count = 0
            
            dir_prefix = path if path.endswith("/") else path + "/"
            
            for state in all_states:
                state_id = state["state_id"]
                if state_id == path or state_id.startswith(dir_prefix):
                    if self._storage.delete(self.STATE_TYPE, state_id):
                        deleted_count += 1
            
            return {
                "success": True,
                "path": path,
                "type": "directory",
                "deleted_count": deleted_count,
                "message": f"Directory deleted: {path}",
            }
        
        # It's a file
        if self._storage.delete(self.STATE_TYPE, path):
            return {
                "success": True,
                "path": path,
                "type": "file",
                "message": f"File deleted: {path}",
            }
        else:
            return {
                "success": False,
                "error": f"File not found: {path}",
            }
    
    def _rename(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rename operation: Rename or move a memory file or directory.
        
        Args:
            path: Current path
            new_path: New path
            
        Returns:
            Success status
        """
        path = params.get("path")
        new_path = params.get("new_path")
        
        if not path:
            raise InvalidParameterError("path", None, "path parameter is required")
        if not new_path:
            raise InvalidParameterError("new_path", None, "new_path parameter is required")
        
        path = self._validate_memory_path(path)
        new_path = self._validate_memory_path(new_path)
        
        # Check if source exists
        if self._is_directory(path):
            # Rename directory - move all files with this path as prefix
            all_states = self._storage.list_states(self.STATE_TYPE)
            moved_count = 0
            
            dir_prefix = path if path.endswith("/") else path + "/"
            new_dir_prefix = new_path if new_path.endswith("/") else new_path + "/"
            
            for state in all_states:
                state_id = state["state_id"]
                if state_id == path or state_id.startswith(dir_prefix):
                    # Calculate new path
                    if state_id == path:
                        new_state_id = new_path
                    else:
                        relative = state_id[len(dir_prefix):]
                        new_state_id = new_dir_prefix + relative
                    
                    # Load old data
                    file_data = self._storage.load(self.STATE_TYPE, state_id)
                    if file_data:
                        # Save to new location
                        if self._storage.save(self.STATE_TYPE, new_state_id, file_data):
                            # Delete old location
                            self._storage.delete(self.STATE_TYPE, state_id)
                            moved_count += 1
            
            return {
                "success": True,
                "path": path,
                "new_path": new_path,
                "type": "directory",
                "moved_count": moved_count,
                "message": f"Directory renamed: {path} -> {new_path}",
            }
        
        # It's a file
        file_data = self._get_file_data(path)
        if file_data is None:
            return {
                "success": False,
                "error": f"File not found: {path}",
            }
        
        # Check if new path already exists
        if self._storage.exists(self.STATE_TYPE, new_path):
            return {
                "success": False,
                "error": f"Target path already exists: {new_path}",
            }
        
        # Save to new location
        if self._save_file_data(new_path, file_data.get("content", "")):
            # Delete old location
            self._storage.delete(self.STATE_TYPE, path)
            return {
                "success": True,
                "path": path,
                "new_path": new_path,
                "type": "file",
                "message": f"File renamed: {path} -> {new_path}",
            }
        else:
            return {
                "success": False,
                "error": f"Failed to rename file: {path}",
            }
    
    def cleanup(self) -> None:
        """Cleanup module resources."""
        if self._storage:
            self._storage.cleanup()

