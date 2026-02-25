from __future__ import annotations
"""
Mavaia Core Custom Exceptions

Custom exception hierarchy for better error handling and context.
"""


class MavaiaError(Exception):
    """Base exception for all Mavaia Core errors"""
    
    def __init__(self, message: str, context: dict[str, str] | None = None):
        """
        Initialize Mavaia error
        
        Args:
            message: Error message
            context: Additional context for debugging
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}
    
    def __str__(self) -> str:
        """Return error message with context if available"""
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} (context: {context_str})"
        return self.message


class ModuleError(MavaiaError):
    """Base exception for module-related errors"""
    pass


class ModuleNotFoundError(ModuleError):
    """Raised when a module is not found"""
    
    def __init__(self, module_name: str):
        """
        Initialize module not found error
        
        Args:
            module_name: Name of the module that was not found
        """
        super().__init__(
            f"Module '{module_name}' not found",
            context={"module_name": module_name}
        )
        self.module_name = module_name


class ModuleInitializationError(ModuleError):
    """Raised when module initialization fails"""
    
    def __init__(self, module_name: str, reason: str):
        """
        Initialize module initialization error
        
        Args:
            module_name: Name of the module that failed to initialize
            reason: Reason for initialization failure
        """
        super().__init__(
            f"Failed to initialize module '{module_name}': {reason}",
            context={"module_name": module_name, "reason": reason}
        )
        self.module_name = module_name
        self.reason = reason


class ModuleOperationError(ModuleError):
    """Raised when a module operation fails"""
    
    def __init__(self, module_name: str, operation: str, reason: str):
        """
        Initialize module operation error
        
        Args:
            module_name: Name of the module
            operation: Operation that failed
            reason: Reason for operation failure
        """
        super().__init__(
            f"Operation '{operation}' failed in module '{module_name}': {reason}",
            context={
                "module_name": module_name,
                "operation": operation,
                "reason": reason
            }
        )
        self.module_name = module_name
        self.operation = operation
        self.reason = reason


class InvalidParameterError(MavaiaError):
    """Raised when invalid parameters are provided"""
    
    def __init__(self, parameter: str, value: str, reason: str):
        """
        Initialize invalid parameter error
        
        Args:
            parameter: Parameter name
            value: Parameter value
            reason: Reason for invalidity
        """
        super().__init__(
            f"Invalid parameter '{parameter}': {reason}",
            context={"parameter": parameter, "value": str(value), "reason": reason}
        )
        self.parameter = parameter
        self.value = value
        self.reason = reason


class APIError(MavaiaError):
    """Base exception for API-related errors"""
    pass


class AuthenticationError(APIError):
    """Raised when API authentication fails"""
    
    def __init__(self, reason: str = "Invalid API key"):
        """
        Initialize authentication error
        
        Args:
            reason: Reason for authentication failure
        """
        super().__init__(
            f"Authentication failed: {reason}",
            context={"reason": reason}
        )
        self.reason = reason


class ValidationError(APIError):
    """Raised when API request validation fails"""
    
    def __init__(self, field: str, reason: str):
        """
        Initialize validation error
        
        Args:
            field: Field that failed validation
            reason: Reason for validation failure
        """
        super().__init__(
            f"Validation failed for field '{field}': {reason}",
            context={"field": field, "reason": reason}
        )
        self.field = field
        self.reason = reason


class ClientError(MavaiaError):
    """Base exception for client-related errors"""
    pass


class ClientInitializationError(ClientError):
    """Raised when client initialization fails"""
    
    def __init__(self, reason: str):
        """
        Initialize client initialization error
        
        Args:
            reason: Reason for initialization failure
        """
        super().__init__(
            f"Client initialization failed: {reason}",
            context={"reason": reason}
        )
        self.reason = reason


class RegistryError(MavaiaError):
    """Base exception for registry-related errors"""
    pass


class ModuleDiscoveryError(RegistryError):
    """Raised when module discovery fails"""
    
    def __init__(self, module_file: str, reason: str):
        """
        Initialize module discovery error
        
        Args:
            module_file: Path to module file
            reason: Reason for discovery failure
        """
        super().__init__(
            f"Failed to discover module from '{module_file}': {reason}",
            context={"module_file": module_file, "reason": reason}
        )
        self.module_file = module_file
        self.reason = reason

