#!/usr/bin/env python3
"""
Dependency Check Script

Checks if all required dependencies are installed.
"""

import sys
from importlib import import_module


REQUIRED_DEPENDENCIES = [
    ("fastapi", "FastAPI web framework"),
    ("uvicorn", "ASGI server"),
    ("pydantic", "Data validation"),
    ("flask", "Flask web framework"),
    ("httpx", "HTTP client"),
    ("pandas", "Data manipulation"),
    ("numpy", "Numerical computing"),
    ("sklearn", "Machine learning utilities"),
]


def check_dependencies() -> bool:
    """Check if all required dependencies are installed"""
    missing = []
    
    for module_name, description in REQUIRED_DEPENDENCIES:
        try:
            import_module(module_name)
            print(f"✓ {module_name} - {description}")
        except ImportError:
            print(f"✗ {module_name} - {description} (MISSING)")
            missing.append(module_name)
    
    if missing:
        print(f"\n❌ Missing dependencies: {', '.join(missing)}")
        print("\nTo install all dependencies, run:")
        print("  pip install -e .")
        print("\nOr for development:")
        print("  pip install -e '.[dev]'")
        return False
    else:
        print("\n✓ All dependencies are installed!")
        return True


if __name__ == "__main__":
    success = check_dependencies()
    sys.exit(0 if success else 1)

