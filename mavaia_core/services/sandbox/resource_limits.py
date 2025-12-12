"""
Resource Limits for Sandbox Execution

Defines and validates resource limits for secure code execution in sandboxes.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ResourceLimits:
    """
    Resource limits for sandbox execution.
    
    Attributes:
        cpu_cores: Number of CPU cores (default: 1, max: 4)
        memory_mb: Memory limit in MB (default: 512, max: 2048)
        disk_mb: Disk space limit in MB (default: 100, max: 1024)
        timeout_seconds: Execution timeout in seconds (default: 30, max: 120)
    """
    
    cpu_cores: float = 1.0
    memory_mb: int = 512
    disk_mb: int = 100
    timeout_seconds: int = 30
    
    # Maximum caps
    MAX_CPU_CORES: float = 4.0
    MAX_MEMORY_MB: int = 2048
    MAX_DISK_MB: int = 1024
    MAX_TIMEOUT_SECONDS: int = 120
    
    def __post_init__(self) -> None:
        """Validate resource limits against maximum caps."""
        if self.cpu_cores > self.MAX_CPU_CORES:
            raise ValueError(
                f"CPU cores ({self.cpu_cores}) exceeds maximum ({self.MAX_CPU_CORES})"
            )
        if self.cpu_cores <= 0:
            raise ValueError(f"CPU cores must be positive, got {self.cpu_cores}")
            
        if self.memory_mb > self.MAX_MEMORY_MB:
            raise ValueError(
                f"Memory ({self.memory_mb}MB) exceeds maximum ({self.MAX_MEMORY_MB}MB)"
            )
        if self.memory_mb <= 0:
            raise ValueError(f"Memory must be positive, got {self.memory_mb}MB")
            
        if self.disk_mb > self.MAX_DISK_MB:
            raise ValueError(
                f"Disk ({self.disk_mb}MB) exceeds maximum ({self.MAX_DISK_MB}MB)"
            )
        if self.disk_mb <= 0:
            raise ValueError(f"Disk must be positive, got {self.disk_mb}MB")
            
        if self.timeout_seconds > self.MAX_TIMEOUT_SECONDS:
            raise ValueError(
                f"Timeout ({self.timeout_seconds}s) exceeds maximum ({self.MAX_TIMEOUT_SECONDS}s)"
            )
        if self.timeout_seconds <= 0:
            raise ValueError(f"Timeout must be positive, got {self.timeout_seconds}s")
    
    def to_dict(self) -> dict:
        """Convert resource limits to dictionary."""
        return {
            "cpu_cores": self.cpu_cores,
            "memory_mb": self.memory_mb,
            "disk_mb": self.disk_mb,
            "timeout_seconds": self.timeout_seconds,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ResourceLimits":
        """Create ResourceLimits from dictionary."""
        return cls(
            cpu_cores=data.get("cpu_cores", 1.0),
            memory_mb=data.get("memory_mb", 512),
            disk_mb=data.get("disk_mb", 100),
            timeout_seconds=data.get("timeout_seconds", 30),
        )
    
    def merge(self, other: Optional["ResourceLimits"]) -> "ResourceLimits":
        """
        Merge with another ResourceLimits instance, taking the minimum of each value.
        
        Args:
            other: Optional ResourceLimits to merge with
            
        Returns:
            New ResourceLimits with merged (minimum) values
        """
        if other is None:
            return ResourceLimits(
                cpu_cores=self.cpu_cores,
                memory_mb=self.memory_mb,
                disk_mb=self.disk_mb,
                timeout_seconds=self.timeout_seconds,
            )
        
        return ResourceLimits(
            cpu_cores=min(self.cpu_cores, other.cpu_cores),
            memory_mb=min(self.memory_mb, other.memory_mb),
            disk_mb=min(self.disk_mb, other.disk_mb),
            timeout_seconds=min(self.timeout_seconds, other.timeout_seconds),
        )


@dataclass
class ResourceUsage:
    """
    Actual resource usage during execution.
    
    Attributes:
        cpu_percent: CPU usage percentage
        memory_mb: Memory used in MB
        disk_mb: Disk space used in MB
        execution_time: Actual execution time in seconds
    """
    
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    disk_mb: float = 0.0
    execution_time: float = 0.0
    
    def to_dict(self) -> dict:
        """Convert resource usage to dictionary."""
        return {
            "cpu_percent": self.cpu_percent,
            "memory_mb": self.memory_mb,
            "disk_mb": self.disk_mb,
            "execution_time": self.execution_time,
        }

