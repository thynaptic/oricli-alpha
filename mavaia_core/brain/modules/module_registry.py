"""
Module Registry - Discovers and manages plug-and-play brain modules
Automatically finds all modules in brain_modules directory
"""

import importlib.util
import inspect
import logging
import os
from pathlib import Path
from typing import Type

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata

logger = logging.getLogger(__name__)


class ModuleRegistry:
    """Registry for all brain modules - enables plug-and-play architecture"""

    _modules: dict[str, Type[BaseBrainModule]] = {}
    _instances: dict[str, BaseBrainModule] = {}
    _metadata: dict[str, ModuleMetadata] = {}
    _discovered: bool = False  # Track if discovery has run

    @classmethod
    def discover_modules(cls, modules_dir: str | None = None, verbose: bool = False):
        """
        Module discovery: Automatically discover all modules in brain_modules directory

        This enables plug-and-play architecture for Python brain modules. Any Python file
        with a class inheriting from BaseBrainModule is automatically discovered and registered.

        Features:
        - Auto-discovers new modules without code changes
        - Validates module structure and metadata
        - Initializes modules on discovery
        - Supports dynamic module loading

        New modules (like lora_loader.py and lora_inference.py) are automatically
        discovered and made available to the PythonBrainService without manual registration.

        Any Python file with a class inheriting from BaseBrainModule is auto-registered
        """
        # Skip if already discovered (within same process)
        if cls._discovered:
            return

        if modules_dir is None:
            # Get directory of this file (brain_modules/)
            modules_dir = Path(__file__).parent

        modules_dir = Path(modules_dir)

        discovered_count = 0
        failed_count = 0

        # Iterate through all Python files in the directory
        for module_file in modules_dir.glob("*.py"):
            # Skip base files
            if module_file.name in [
                "__init__.py",
                "base_module.py",
                "module_registry.py",
                "model_manager.py",
            ]:
                continue

            try:
                # Import the module
                module_name = module_file.stem
                spec = importlib.util.spec_from_file_location(module_name, module_file)
                if spec is None or spec.loader is None:
                    continue

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Find all classes that inherit from BaseBrainModule
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, BaseBrainModule) and obj is not BaseBrainModule:

                        # Create instance to get metadata
                        try:
                            instance = obj()
                            metadata = instance.metadata

                            # Register module
                            cls.register_module(metadata.name, obj, metadata)
                            discovered_count += 1
                            if verbose:
                                logger.info(
                                    "Discovered module %s v%s",
                                    metadata.name,
                                    metadata.version,
                                    extra={"module_name": "module_registry", "discovered": metadata.name},
                                )
                        except Exception as e:
                            failed_count += 1
                            if verbose:
                                logger.warning(
                                    "Failed to initialize candidate module class %s",
                                    name,
                                    exc_info=True,
                                    extra={"module_name": "module_registry", "error_type": type(e).__name__},
                                )

            except Exception as e:
                failed_count += 1
                if verbose:
                    logger.warning(
                        "Failed to load module file %s",
                        module_file.name,
                        exc_info=True,
                        extra={"module_name": "module_registry", "error_type": type(e).__name__},
                    )

        # Mark as discovered and log summary
        cls._discovered = True
        if discovered_count > 0 or failed_count > 0:
            status = f"Discovered {discovered_count} module(s)"
            if failed_count > 0:
                status += f", {failed_count} failed"
            if verbose:
                logger.info(
                    "%s",
                    status,
                    extra={
                        "module_name": "module_registry",
                        "discovered_count": discovered_count,
                        "failed_count": failed_count,
                    },
                )

    @classmethod
    def register_module(
        cls, name: str, module_class: Type[BaseBrainModule], metadata: ModuleMetadata
    ):
        """Manually register a module"""
        cls._modules[name] = module_class
        cls._metadata[name] = metadata

    @classmethod
    def get_module(
        cls, name: str, auto_discover: bool = True
    ) -> BaseBrainModule | None:
        """Get an instance of a module by name"""
        if auto_discover and not cls._modules:
            cls.discover_modules()

        if name not in cls._modules:
            return None

        # Return cached instance or create new one
        if name not in cls._instances:
            module_class = cls._modules[name]
            instance = module_class()

            # Initialize the module
            if instance.initialize():
                cls._instances[name] = instance
            else:
                logger.warning(
                    "Failed to initialize module instance %s",
                    name,
                    extra={"module_name": "module_registry", "instance": name},
                )
                return None

        return cls._instances[name]

    @classmethod
    def list_modules(cls) -> list[str]:
        """List all registered module names"""
        return list(cls._modules.keys())

    @classmethod
    def get_metadata(cls, name: str) -> ModuleMetadata | None:
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
