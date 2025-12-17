"""
Legacy setuptools entrypoint.

All package metadata is defined in `pyproject.toml` (PEP 621 / PEP 517).
This file remains only for compatibility with older tooling that still invokes
`setup.py` directly.
"""

from setuptools import setup

setup()

