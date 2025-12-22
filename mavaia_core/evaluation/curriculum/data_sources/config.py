"""
Data Source Configuration

Handles loading and managing data source configurations.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


class SourceConfig:
    """Configuration for a single data source"""
    
    def __init__(self, config_dict: Dict[str, Any]):
        """
        Initialize source config from dictionary
        
        Args:
            config_dict: Configuration dictionary
        """
        self.type = config_dict.get("type", "local")
        self.name = config_dict.get("name", "unknown")
        self.auto_discover = config_dict.get("auto_discover", False)
        self.fallback_only = config_dict.get("fallback_only", False)
        self.config = config_dict
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.config


class DataSourceConfig:
    """Manager for data source configurations"""
    
    DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "data" / "curriculum_sources.yaml"
    ENV_CONFIG_PATH = os.getenv("MAVAIA_CURRICULUM_SOURCES_CONFIG")
    
    # Default auto-discovered sources
    DEFAULT_SOURCES = [
        {
            "type": "huggingface",
            "dataset": "hendrycks/MMLU",
            "name": "MMLU",
            "auto_discover": True,
        },
        {
            "type": "huggingface",
            "dataset": "gsm8k",
            "name": "GSM8K",
            "auto_discover": True,
        },
        {
            "type": "huggingface",
            "dataset": "hendrycks/MATH",
            "name": "MATH",
            "auto_discover": True,
        },
    ]
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize configuration manager
        
        Args:
            config_path: Path to configuration file (optional)
        """
        self.config_path = config_path or self._find_config_path()
        self.sources: List[SourceConfig] = []
        # Don't load HuggingFace sources immediately - they can be slow
        # Only load local source by default
        self._load_minimal()
    
    def _find_config_path(self) -> Optional[Path]:
        """Find configuration file path"""
        # Check environment variable first
        if self.ENV_CONFIG_PATH:
            path = Path(self.ENV_CONFIG_PATH)
            if path.exists():
                return path
        
        # Check default location
        if self.DEFAULT_CONFIG_PATH.exists():
            return self.DEFAULT_CONFIG_PATH
        
        return None
    
    def _load_minimal(self) -> None:
        """Load minimal configuration (local source only)"""
        # Only load local source initially to avoid slow HuggingFace imports
        self.sources = []
    
    def load(self) -> None:
        """Load full configuration from file or use defaults"""
        if self.config_path and self.config_path.exists():
            try:
                if self.config_path.suffix in [".yaml", ".yml"]:
                    if not YAML_AVAILABLE:
                        raise ImportError("PyYAML not available. Install with: pip install pyyaml")
                    with open(self.config_path, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                else:
                    # Assume JSON
                    with open(self.config_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                
                sources_data = data.get("sources", [])
                self.sources = [SourceConfig(s) for s in sources_data]
            except Exception:
                # Fall back to defaults on error
                self.sources = [SourceConfig(s) for s in self.DEFAULT_SOURCES]
        else:
            # Use defaults (but skip HuggingFace to avoid slow imports)
            # Only include local source
            pass
    
    def get_sources(self, include_fallback_only: bool = False) -> List[SourceConfig]:
        """
        Get all sources
        
        Args:
            include_fallback_only: Include sources marked as fallback_only
        
        Returns:
            List of source configurations
        """
        if include_fallback_only:
            return self.sources
        return [s for s in self.sources if not s.fallback_only]
    
    def get_auto_discover_sources(self) -> List[SourceConfig]:
        """Get sources marked for auto-discovery"""
        return [s for s in self.sources if s.auto_discover]
    
    def save(self, path: Optional[Path] = None) -> None:
        """
        Save configuration to file
        
        Args:
            path: Path to save to (defaults to config_path)
        """
        save_path = path or self.config_path or self.DEFAULT_CONFIG_PATH
        
        # Ensure directory exists
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "sources": [s.to_dict() for s in self.sources]
        }
        
        if save_path.suffix in [".yaml", ".yml"]:
            if not YAML_AVAILABLE:
                raise ImportError("PyYAML not available. Install with: pip install pyyaml")
            with open(save_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False)
        else:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

