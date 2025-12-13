"""
Module Registry - Discovers and manages plug-and-play brain modules
Automatically finds all modules in brain_modules directory
Refactored to be importable as a package while maintaining backward compatibility
"""

import importlib.util
import inspect
import os
import sys
import threading
import time
from pathlib import Path
from typing import Type, Optional, Union

# Import base module from package
from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import (
    ModuleDiscoveryError,
    ModuleInitializationError,
)

class ModuleRegistry:
    """Registry for all brain modules - enables plug-and-play architecture"""

    _modules: dict[str, Type[BaseBrainModule]] = {}
    _instances: dict[str, BaseBrainModule] = {}
    _metadata: dict[str, ModuleMetadata] = {}
    _discovered: bool = False  # Track if discovery has run
    _discovering: bool = False  # Track if discovery is in progress
    _discovery_lock: threading.Lock = threading.Lock()
    _modules_dir: Optional[Path] = None  # Cached modules directory
    
    @staticmethod
    def _import_with_timeout(module_file: Path, spec, module, timeout: float = 5.0) -> bool:
        """Import a module with timeout to prevent hanging"""
        import signal
        import os
        
        result = [None]
        exception = [None]
        thread_id = [None]
        
        def import_module():
            try:
                thread_id[0] = threading.get_ident()
                spec.loader.exec_module(module)
                result[0] = True
            except Exception as e:
                exception[0] = e
        
        thread = threading.Thread(target=import_module, daemon=True)
        thread.start()
        thread.join(timeout=timeout)
        
        if thread.is_alive():
            # Module import is taking too long, skip it
            # Note: daemon threads will be killed when main thread exits
            # but we can't forcefully kill them here
            return False
        
        if exception[0]:
            raise exception[0]
        
        return result[0] is True

    @classmethod
    def set_modules_dir(cls, modules_dir: Path) -> None:
        """Set the modules directory (for package usage)"""
        cls._modules_dir = modules_dir
        cls._discovered = False  # Reset discovery when directory changes

    @classmethod
    def get_modules_dir(cls) -> Optional[Path]:
        """Get the modules directory - only mavaia_core/brain/modules/"""
        if cls._modules_dir is not None:
            return cls._modules_dir
        
        # Only use modules directory within mavaia-core package
        # This ensures we only discover actual brain modules
        package_dir = Path(__file__).parent.parent.parent
        brain_modules_dir = package_dir / "mavaia_core" / "brain" / "modules"
        if brain_modules_dir.exists():
            return brain_modules_dir
        
        return None

    @classmethod
    def discover_modules(
        cls,
        modules_dir: Optional[Union[str, Path]] = None,
        verbose: bool = False,
        background: bool = False
    ) -> Optional[tuple[int, int]]:
        """
        Module discovery: Automatically discover all modules in brain_modules directory

        This enables plug-and-play architecture for Python brain modules. Any Python file
        with a class inheriting from BaseBrainModule is automatically discovered and registered.

        Features:
        - Auto-discovers new modules without code changes
        - Validates module structure and metadata
        - Initializes modules on discovery
        - Supports dynamic module loading

        Args:
            modules_dir: Directory containing modules (optional, auto-detected if not provided)
            verbose: Enable verbose logging
            background: If True, run discovery in background thread (non-blocking)
        """
        # Skip if already discovered (within same process)
        if cls._discovered and modules_dir is None:
            return None
        
        # If already discovering, wait for it to complete
        if cls._discovering:
            if not background:
                # Wait for discovery to complete
                while cls._discovering:
                    time.sleep(0.1)
            return None
        
        # Start discovery in background if requested
        if background:
            def discover_in_background():
                with cls._discovery_lock:
                    cls._discovering = True
                    try:
                        cls._discover_modules_internal(modules_dir, verbose)
                    finally:
                        cls._discovering = False
            
            thread = threading.Thread(target=discover_in_background, daemon=True)
            thread.start()
            return None
        
        # Synchronous discovery
        with cls._discovery_lock:
            cls._discovering = True
            try:
                return cls._discover_modules_internal(modules_dir, verbose)
            finally:
                cls._discovering = False
    
    @classmethod
    def _discover_modules_internal(
        cls,
        modules_dir: Optional[Union[str, Path]] = None,
        verbose: bool = False
    ) -> tuple[int, int]:
        """Internal discovery implementation
        
        Returns:
            tuple[int, int]: (discovered_count, failed_count)
        """

        if modules_dir is None:
            modules_dir = cls.get_modules_dir()
            if modules_dir is None:
                # Only use mavaia_core/brain/modules/ - no fallbacks
                if verbose:
                    print(f"[ModuleRegistry] Modules directory not found: mavaia_core/brain/modules/", file=sys.stderr)
                return (0, 0)
        else:
            modules_dir = Path(modules_dir)

        if not modules_dir.exists():
            if verbose:
                print(f"[ModuleRegistry] Modules directory not found: {modules_dir}", file=sys.stderr)
            return (0, 0)

        modules_dir = Path(modules_dir)
        discovered_count = 0
        failed_count = 0

        # Add modules directory to path for imports
        if str(modules_dir) not in sys.path:
            sys.path.insert(0, str(modules_dir))

        # Collect all Python files to process
        python_files = []
        
        # Get direct Python files
        for module_file in modules_dir.glob("*.py"):
            # Skip base files and data model files (not brain modules)
            if module_file.name in [
                "__init__.py",
                "base_module.py",
                "module_registry.py",
                "model_manager.py",
                "tot_models.py",  # Data models, not brain modules
                "cot_models.py",  # Data models, not brain modules
                "mcts_models.py",  # Data models, not brain modules
                "tool_calling_models.py",  # Data models, not brain modules
            ]:
                continue
            python_files.append(module_file)
        
        # Also check subdirectories (like symbolic_solvers/)
        # Skip 'models' subdirectory as it contains data models, not brain modules
        for subdir in modules_dir.iterdir():
            if subdir.is_dir() and not subdir.name.startswith("__") and subdir.name != "models":
                for module_file in subdir.glob("*.py"):
                    if module_file.name != "__init__.py":
                        python_files.append(module_file)
        
        # Process all collected files
        for module_file in python_files:
            try:
                # Import the module
                # Use relative path from modules_dir for module name to avoid conflicts
                module_name = module_file.stem
                if module_file.parent != modules_dir:
                    # For subdirectory modules, include parent directory in name
                    rel_path = module_file.relative_to(modules_dir)
                    module_name = str(rel_path.with_suffix("")).replace("/", "_")
                spec = importlib.util.spec_from_file_location(module_name, module_file)
                if spec is None or spec.loader is None:
                    continue

                module = importlib.util.module_from_spec(spec)

                # Ensure base_module resolves to the package definition so issubclass works
                try:
                    from mavaia_core.brain import base_module as package_base_module
                    sys.modules["base_module"] = package_base_module  # alias for local imports
                    module.BaseBrainModule = package_base_module.BaseBrainModule
                    module.ModuleMetadata = package_base_module.ModuleMetadata
                except ImportError:
                    # Fallback: try importing from local directory (backward compatibility)
                    try:
                        import base_module as local_base_module
                        module.BaseBrainModule = local_base_module.BaseBrainModule
                        module.ModuleMetadata = local_base_module.ModuleMetadata
                    except ImportError:
                        # Last resort: try relative import
                        from . import base_module as relative_base_module
                        module.BaseBrainModule = relative_base_module.BaseBrainModule
                        module.ModuleMetadata = relative_base_module.ModuleMetadata
                
                # Import module with timeout to prevent hanging
                try:
                    # Increase timeout for modules that may have heavy imports
                    # Some modules like python_code_embeddings import transformers/jax which can take time
                    timeout = 10.0 if 'embedding' in module_file.name.lower() or 'model' in module_file.name.lower() else 5.0
                    if not cls._import_with_timeout(module_file, spec, module, timeout=timeout):
                        # Always show errors, not just when verbose
                        print(
                            f"Failed to import {module_file.name}: import timeout (>{timeout}s)",
                            file=sys.stderr,
                        )
                        failed_count += 1
                        continue
                except Exception as e:
                    failed_count += 1
                    # Always show errors, not just when verbose
                    error_msg = f"Failed to import {module_file.name}: {e}"
                    print(
                        error_msg,
                        file=sys.stderr,
                    )
                    # Store error for potential re-raising if needed
                    continue

                # Find all classes that inherit from BaseBrainModule
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, BaseBrainModule) and obj is not BaseBrainModule:

                        # Create instance to get metadata (with timeout)
                        try:
                            instance_result = [None]
                            instance_exception = [None]
                            
                            def create_instance():
                                try:
                                    instance_result[0] = obj()
                                except Exception as e:
                                    instance_exception[0] = e
                            
                            instance_thread = threading.Thread(target=create_instance, daemon=True)
                            instance_thread.start()
                            instance_thread.join(timeout=2.0)  # 2 second timeout for instance creation
                            
                            if instance_thread.is_alive():
                                # Instance creation is taking too long, skip this module
                                failed_count += 1
                                # Always show errors, not just when verbose
                                print(
                                    f"Failed to initialize {name}: instance creation timeout (>2s)",
                                    file=sys.stderr,
                                )
                                continue
                            
                            if instance_exception[0]:
                                raise instance_exception[0]
                            
                            instance = instance_result[0]
                            if instance is None:
                                continue
                                
                            metadata = instance.metadata

                            # Register module
                            cls.register_module(metadata.name, obj, metadata)
                            discovered_count += 1
                            # Don't print individual module discoveries - only show errors
                        except Exception as e:
                            failed_count += 1
                            # Always show errors, not just when verbose
                            error_msg = f"Failed to initialize {name}: {e}"
                            print(
                                error_msg,
                                file=sys.stderr,
                            )
                            # Could raise ModuleInitializationError here if needed

            except Exception as e:
                failed_count += 1
                # Always show errors, not just when verbose
                print(
                    f"Failed to load {module_file.name}: {e}",
                    file=sys.stderr,
                )

        # Mark as discovered
        cls._discovered = True
        # Return counts to caller
        return (discovered_count, failed_count)

    @classmethod
    def register_module(
        cls,
        name: str,
        module_class: Type[BaseBrainModule],
        metadata: ModuleMetadata
    ) -> None:
        """Manually register a module"""
        cls._modules[name] = module_class
        cls._metadata[name] = metadata

    @classmethod
    def get_module(
        cls, name: str, auto_discover: bool = True, wait_timeout: float = 10.0
    ) -> Optional[BaseBrainModule]:
        """Get an instance of a module by name"""
        if auto_discover and not cls._modules and not cls._discovered:
            # Start discovery in background (non-blocking)
            cls.discover_modules(background=True, verbose=False)
        
        # Wait briefly for the specific module to be discovered
        if auto_discover and name not in cls._modules:
            start_time = time.time()
            while name not in cls._modules and (time.time() - start_time) < wait_timeout:
                if cls._discovered:
                    # Discovery complete, module not found
                    break
                time.sleep(0.1)

        if name not in cls._modules:
            return None

        # Return cached instance or create new one
        if name not in cls._instances:
            module_class = cls._modules[name]
            instance = module_class()

            # Initialize the module
            try:
                if not instance.initialize():
                    raise ModuleInitializationError(
                        name,
                        "initialize() returned False"
                    )
                
                # Wrap execute method for automatic metrics tracking
                try:
                    from mavaia_core.brain.wrapper import MetricsTrackingWrapper
                    instance.execute = MetricsTrackingWrapper.wrap_execute(instance)
                except Exception:
                    # Silently fail if wrapper not available
                    pass
                
                cls._instances[name] = instance
            except Exception as e:
                raise ModuleInitializationError(
                    name,
                    str(e)
                ) from e

        return cls._instances[name]

    @classmethod
    def list_modules(cls) -> list[str]:
        """List all registered module names"""
        return list(cls._modules.keys())

    @classmethod
    def get_metadata(cls, name: str) -> Optional[ModuleMetadata]:
        """Get metadata for a module"""
        return cls._metadata.get(name)

    @classmethod
    def is_module_available(cls, name: str) -> bool:
        """Check if a module is available"""
        return name in cls._modules

    @classmethod
    def unregister_module(cls, name: str) -> None:
        """Unregister a module (for testing/dynamic reloading)"""
        if name in cls._instances:
            cls._instances[name].cleanup()
            del cls._instances[name]
        if name in cls._modules:
            del cls._modules[name]
        if name in cls._metadata:
            del cls._metadata[name]

    @classmethod
    def reload_modules(cls, verbose: bool = False) -> None:
        """Reload all modules (for hot-reload support)"""
        # Cleanup existing instances
        for name in list(cls._instances.keys()):
            cls.unregister_module(name)
        
        # Reset discovery flag
        cls._discovered = False
        
        # Rediscover modules
        cls.discover_modules(verbose=verbose)
