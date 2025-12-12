"""
Command Validator - Allowlist and Blacklist Validation

Implements strict allowlist (whitelist) validation as primary security mechanism,
with blacklist as secondary defense layer.
"""

import re
from typing import Set, List, Tuple, Optional
from pathlib import Path


class CommandValidationError(Exception):
    """Raised when command validation fails."""
    pass


class CommandValidator:
    """
    Validates commands against allowlists and blacklists.
    
    Primary security: Strict allowlist - only explicitly permitted commands allowed.
    Secondary security: Blacklist blocks known dangerous patterns.
    """
    
    # Bash/Shell Allowed Commands (strict allowlist)
    BASH_ALLOWED_COMMANDS: Set[str] = {
        "echo", "cat", "grep", "sed", "ls", "touch", "mv", "cp", "tar",
        "find", "head", "tail", "wc", "sort", "uniq", "diff", "mkdir",
        "rm", "pwd", "which",
    }
    
    # Bash/Shell Denied Commands (blacklist - secondary defense)
    BASH_DENIED_COMMANDS: Set[str] = {
        # System modification
        "sudo", "su", "chmod", "chown", "chgrp", "mkfs", "fdisk", "dd",
        "mount", "umount", "mkfs.ext*", "mkfs.vfat", "mkfs.ntfs",
        # Network utilities
        "nc", "netcat", "curl", "wget", "ssh", "scp", "rsync", "telnet",
        "ftp", "tftp", "ncftp",
        # Process management
        "kill", "killall", "pkill", "nohup", "screen", "tmux", "bg", "fg",
        # Container escape
        "chroot", "unshare", "nsenter", "setns",
        # Dangerous shell built-ins
        "exec", "eval",
    }
    
    # Python Allowed Imports (strict allowlist)
    PYTHON_ALLOWED_MODULES: Set[str] = {
        # Data types
        "collections", "dataclasses", "enum", "typing",
        # Data processing
        "json", "csv", "xml.etree.ElementTree",
        # String/text
        "re", "string", "textwrap",
        # Math
        "math", "statistics", "decimal", "fractions", "random",
        # Date/time
        "datetime", "time", "calendar",
        # File I/O (sandbox-restricted)
        "pathlib", "io",
        # Utilities
        "itertools", "functools", "operator", "copy", "pickle",
        # System (limited)
        "os", "sys",
        # Built-in functions allowed (validated separately)
    }
    
    # Python Denied Imports (blacklist)
    PYTHON_DENIED_MODULES: Set[str] = {
        # Network
        "socket", "urllib", "urllib2", "urllib3", "requests", "http",
        "http.client", "ftplib", "smtplib",
        # Process execution
        "subprocess", "multiprocessing",
        # Code execution
        "eval", "exec", "compile", "__import__",
        # Security-sensitive
        "ctypes", "cffi", "importlib",
    }
    
    # Node.js Allowed Modules (strict allowlist)
    NODE_ALLOWED_MODULES: Set[str] = {
        "fs", "path", "os", "crypto", "util", "events", "stream", "buffer",
    }
    
    # Node.js Denied Modules (blacklist)
    NODE_DENIED_MODULES: Set[str] = {
        # Network
        "http", "https", "net", "dgram", "tls", "http2",
        # Process execution
        "child_process", "cluster", "worker_threads",
        # Code execution
        "vm",
    }
    
    # Dangerous patterns (blacklist)
    DANGEROUS_PATTERNS: List[Tuple[str, str]] = [
        # Path traversal
        (r"\.\.\/", "Path traversal detected"),
        (r"\.\.\\\\", "Path traversal detected"),
        # Absolute paths outside sandbox
        (r"^/(?!tmp|home|usr/bin/(cat|echo|ls|grep|sed|head|tail|wc|sort|uniq|mkdir|rm|pwd|which|find|diff|mv|cp|tar|touch))", "Absolute path outside sandbox"),
        # Shell escaping attempts
        (r"`[^`]*`", "Backtick command substitution"),
        (r"\$\([^)]+\)", "Command substitution"),
        (r"eval\s+", "Eval usage"),
        (r"exec\s+", "Exec usage"),
    ]
    
    def __init__(self, sandbox_root: str = "/sandbox"):
        """
        Initialize command validator.
        
        Args:
            sandbox_root: Root directory of the sandbox (for path validation)
        """
        self.sandbox_root = Path(sandbox_root).resolve()
    
    def validate_bash_command(self, command: str) -> Tuple[bool, Optional[str]]:
        """
        Validate bash command against allowlist and blacklist.
        
        Args:
            command: Command string to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Strip leading/trailing whitespace
        command = command.strip()
        
        if not command:
            return False, "Empty command"
        
        # Secondary defense: Check blacklist patterns
        for pattern, message in self.DANGEROUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"Blacklist violation: {message}"
        
        # Check against denied commands (blacklist)
        command_lower = command.lower()
        for denied_cmd in self.BASH_DENIED_COMMANDS:
            if command_lower.startswith(denied_cmd + " ") or command_lower == denied_cmd:
                return False, f"Denied command: {denied_cmd}"
            # Check for patterns like mkfs.ext*
            if denied_cmd.endswith("*") and command_lower.startswith(denied_cmd[:-1]):
                return False, f"Denied command pattern: {denied_cmd}"
        
        # Primary defense: Check allowlist
        # Extract first token (command name)
        first_token = command.split()[0].strip()
        # Remove path if present
        if "/" in first_token:
            first_token = first_token.split("/")[-1]
        
        if first_token not in self.BASH_ALLOWED_COMMANDS:
            # Check if it's a shell built-in or redirection
            if first_token in (">", ">>", "<", "|", "&&", "||"):
                # These are allowed as operators, but validate the full command structure
                # Extract actual commands from the command string
                parts = re.split(r'[|&<>]+', command)
                for part in parts:
                    part = part.strip()
                    if part:
                        cmd_name = part.split()[0] if part.split() else ""
                        if "/" in cmd_name:
                            cmd_name = cmd_name.split("/")[-1]
                        if cmd_name and cmd_name not in self.BASH_ALLOWED_COMMANDS:
                            return False, f"Command not in allowlist: {cmd_name}"
                return True, None
            return False, f"Command not in allowlist: {first_token}"
        
        return True, None
    
    def validate_python_import(self, module_name: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Python import against allowlist and blacklist.
        
        Args:
            module_name: Module name to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Handle relative imports
        if module_name.startswith("."):
            return False, "Relative imports not allowed"
        
        # Extract base module name (before first dot)
        base_module = module_name.split(".")[0]
        
        # Secondary defense: Check blacklist
        if base_module in self.PYTHON_DENIED_MODULES:
            return False, f"Denied Python module: {base_module}"
        
        # Check full module name in denied list
        if module_name in self.PYTHON_DENIED_MODULES:
            return False, f"Denied Python module: {module_name}"
        
        # Primary defense: Check allowlist
        if base_module not in self.PYTHON_ALLOWED_MODULES:
            # Special handling for submodules of allowed modules
            allowed = False
            for allowed_mod in self.PYTHON_ALLOWED_MODULES:
                if module_name.startswith(allowed_mod + "."):
                    allowed = True
                    break
            if not allowed:
                return False, f"Python module not in allowlist: {base_module}"
        
        # Additional checks for restricted modules
        if base_module == "os":
            # Only allow specific os functions (path operations)
            # This is validated at runtime, not import time
            pass
        
        if base_module == "sys":
            # Only allow version info, no modification
            # This is validated at runtime
            pass
        
        if base_module == "pickle":
            # Only allow reading, not unpickling arbitrary data
            # This is validated at runtime
            pass
        
        return True, None
    
    def validate_node_require(self, module_name: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Node.js require() against allowlist and blacklist.
        
        Args:
            module_name: Module name to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Secondary defense: Check blacklist
        if module_name in self.NODE_DENIED_MODULES:
            return False, f"Denied Node.js module: {module_name}"
        
        # Primary defense: Check allowlist
        if module_name not in self.NODE_ALLOWED_MODULES:
            return False, f"Node.js module not in allowlist: {module_name}"
        
        return True, None
    
    def validate_path(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """
        Validate file path stays within sandbox.
        
        Args:
            file_path: File path to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Resolve path
            resolved_path = Path(file_path).resolve()
            
            # Check if path is within sandbox root
            try:
                resolved_path.relative_to(self.sandbox_root)
            except ValueError:
                return False, f"Path outside sandbox: {file_path}"
            
            # Check for dangerous patterns
            path_str = str(resolved_path)
            for pattern, message in self.DANGEROUS_PATTERNS[:2]:  # Path traversal patterns
                if re.search(pattern, path_str):
                    return False, f"Path validation failed: {message}"
            
            return True, None
        except Exception as e:
            return False, f"Path validation error: {str(e)}"
    
    def extract_commands_from_bash(self, command: str) -> List[str]:
        """
        Extract individual commands from a bash command string.
        
        Args:
            command: Bash command string (may contain pipes, &&, ||, etc.)
            
        Returns:
            List of individual command tokens
        """
        # Split by operators
        parts = re.split(r'[|&<>]+', command)
        commands = []
        for part in parts:
            part = part.strip()
            if part:
                # Extract first token (command name)
                first_token = part.split()[0].strip()
                if "/" in first_token:
                    first_token = first_token.split("/")[-1]
                commands.append(first_token)
        return commands

