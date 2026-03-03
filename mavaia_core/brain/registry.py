from __future__ import annotations
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
    _discovering_thread_id: Optional[int] = None  # Thread currently performing discovery
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
                    cls._discovering_thread_id = threading.get_ident()
                    try:
                        cls._discover_modules_internal(modules_dir, verbose)
                    finally:
                        cls._discovering = False
                        cls._discovering_thread_id = None
            
            thread = threading.Thread(target=discover_in_background, daemon=True)
            thread.start()
            return None
        
        # Synchronous discovery
        with cls._discovery_lock:
            cls._discovering = True
            cls._discovering_thread_id = threading.get_ident()
            try:
                return cls._discover_modules_internal(modules_dir, verbose)
            finally:
                cls._discovering = False
                cls._discovering_thread_id = None
    
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
        failed_modules = []  # Track failed module names

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

                # Proactively skip modules that will try to pull large HF models at import-time.
                # This avoids long hangs/timeouts on live servers and keeps core cognition responsive.
                try:
                    import os
                    enable_heavy = os.getenv("MAVAIA_ENABLE_HEAVY_MODULES", "false").lower() in (
                        "true",
                        "1",
                        "yes",
                    )
                    
                    text = module_file.read_text(encoding="utf-8", errors="ignore")

                    if not enable_heavy and any(
                        m in text
                        for m in (
                            "from_pretrained(",
                            "hf_hub_download(",
                            "snapshot_download(",
                            "SentenceTransformer(",
                            "sentence_transformers",
                        )
                    ):
                        continue

                    # On live servers, default to skipping modules that import heavy ML stacks at
                    # module import-time (TensorFlow/torch/transformers/JAX). These are optional
                    # for core cognition, and can cause latency/noise/hangs.
                    if not enable_heavy and any(
                        m in text
                        for m in (
                            "import tensorflow",
                            "tensorflow_hub",
                            "import torch",
                            "import transformers",
                            "import jax",
                            "from transformers import",
                        )
                    ):
                        continue
                except Exception:
                    pass

                spec = importlib.util.spec_from_file_location(module_name, module_file)
                if spec is None or spec.loader is None:
                    continue

                module = importlib.util.module_from_spec(spec)
                # Add to sys.modules for dataclass/typing compatibility on Python 3.9
                # when using from __future__ import annotations
                sys.modules[module_name] = module

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
                
                # Import module with a configurable timeout to prevent hangs on
                # misbehaving modules, while still allowing heavy but valid
                # modules to load. The timeout can be tuned via the
                # MAVAIA_MODULE_IMPORT_TIMEOUT environment variable.
                try:
                    import os

                    default_timeout = 60.0
                    try:
                        timeout = float(os.getenv("MAVAIA_MODULE_IMPORT_TIMEOUT", default_timeout))
                    except ValueError:
                        timeout = default_timeout

                    # Allow disabling the threaded timeout path entirely via env
                    disable_timeout = os.getenv(
                        "MAVAIA_DISABLE_IMPORT_TIMEOUT", "false"
                    ).lower() in ("true", "1", "yes")

                    if disable_timeout:
                        # Synchronous import on main thread
                        spec.loader.exec_module(module)
                    else:
                        if not cls._import_with_timeout(
                            module_file, spec, module, timeout=timeout
                        ):
                            failed_count += 1
                            failed_modules.append(f"{module_file.name}: import timeout (>{timeout}s)")
                            continue

                except Exception as e:
                    failed_count += 1
                    failed_modules.append(f"{module_file.name}: {e}")
                    continue

                # Find all classes that inherit from BaseBrainModule
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, BaseBrainModule) and obj is not BaseBrainModule:

                        # Create instance to get metadata.
                        # This used to run in a short-lived thread with a hard timeout,
                        # which caused legitimate but heavy modules to be dropped.
                        # We now construct synchronously so *all* valid modules can
                        # load and expose metadata, even if initialization is slower.
                        try:
                            instance = obj()
                            if instance is None:
                                continue

                            metadata = instance.metadata

                            # Register module
                            cls.register_module(metadata.name, obj, metadata)
                            discovered_count += 1
                            # Don't print individual module discoveries - only show errors
                        except Exception as e:
                            failed_count += 1
                            failed_modules.append(f"{module_file.name} ({name}): initialization failed: {e}")

            except Exception as e:
                failed_count += 1
                failed_modules.append(f"{module_file.name}: {e}")

        # Mark as discovered
        cls._discovered = True
        
        # Print single status line with counts
        print(
            f"[ModuleRegistry] imported({discovered_count})/failed({failed_count})",
            file=sys.stderr,
            flush=True,
        )
        
        # Only show failed imports
        if failed_modules:
            for failed in failed_modules:
                print(
                    f"  Failed to import {failed}",
                    file=sys.stderr,
                )
        
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
        cls, name: str, auto_discover: bool = True, wait_timeout: float = 30.0
    ) -> Optional[BaseBrainModule]:
        """Get an instance of a module by name"""
        if auto_discover and not cls._modules and not cls._discovered:
            # Start discovery in background (non-blocking)
            cls.discover_modules(background=True, verbose=False)
        
        # If a module tries to resolve dependencies during discovery, never block waiting for
        # discovery to finish (this can deadlock). Only short-circuit when we're *inside* the
        # discovery thread; other threads may safely wait.
        if (
            cls._discovering
            and cls._discovering_thread_id is not None
            and threading.get_ident() == cls._discovering_thread_id
            and name not in cls._modules
        ):
            return None

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
    def get_module_or_fallback(
        cls,
        name: str,
        operation: Optional[str] = None,
        auto_discover: bool = True,
        wait_timeout: float = 30.0
    ) -> tuple[Optional[BaseBrainModule], Optional[str], bool, Optional[str]]:
        """
        Get module instance or automatic fallback
        
        Args:
            name: Name of primary module
            operation: Optional operation name (for operation-specific fallbacks)
            auto_discover: Whether to auto-discover modules
            wait_timeout: Maximum time to wait for module discovery
        
        Returns:
            Tuple of (module_instance, actual_module_name, is_fallback, mapped_operation)
            is_fallback indicates if fallback was used
            mapped_operation is the operation name to use (may differ from input if fallback used)
        """
        # Try to get primary module first
        try:
            module = cls.get_module(name, auto_discover=auto_discover, wait_timeout=wait_timeout)
            if module is not None:
                # Check if module is available and healthy via availability manager
                try:
                    from mavaia_core.brain.availability import get_availability_manager
                    availability_manager = get_availability_manager()
                    
                    if availability_manager._initialized:
                        # Use availability manager to get module or fallback
                        result = availability_manager.get_module_or_fallback(
                            name,
                            operation
                        )
                        module, actual_name, is_fallback, mapped_op = result
                        return module, actual_name, is_fallback, mapped_op
                except Exception:
                    # Availability manager not available or error, use primary module
                    pass
                
                return module, name, False, operation
        except Exception:
            # Primary module failed, try fallback
            pass
        
        # Try fallback if primary failed
        try:
            from mavaia_core.brain.degraded_classifier import get_degraded_classifier
            classifier = get_degraded_classifier()
            fallback_name = classifier.get_fallback_module(name, operation)
            
            if fallback_name:
                fallback_module = cls.get_module(
                    fallback_name,
                    auto_discover=auto_discover,
                    wait_timeout=wait_timeout
                )
                if fallback_module:
                    # Get mapped operation for fallback
                    mapped_operation = None
                    if operation:
                        try:
                            mapped_operation = classifier.get_fallback_operation(
                                name, operation, fallback_name
                            )
                        except Exception:
                            mapped_operation = operation  # Use original if mapping fails
                    return fallback_module, fallback_name, True, mapped_operation
        except Exception:
            # Fallback failed, return None
            pass
        
        return None, None, False, None

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
