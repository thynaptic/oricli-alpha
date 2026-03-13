"""
Setup script for oricli-core package
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="oricli-core",
    version="1.0.0",
    description="Oricli-Alpha Core - Modular AI Core Package with OpenAI-compatible API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Thynaptic Research",
    author_email="ai@thynaptic.com",
    url="https://github.com/thynaptic/oricli-core",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "fastapi>=0.104.0",
        "uvicorn[standard]>=0.24.0",
        "pydantic>=2.0.0",
        "pandas>=1.5.0",
        "numpy>=1.23.0",
        "scikit-learn>=1.2.0",
        "flask>=3.0.0",
        "httpx>=0.24.0",
        "docker>=6.0.0",
        "psutil>=5.9.0",
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "PyPDF2>=3.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "httpx>=0.24.0",
            "black>=23.0.0",
            "ruff>=0.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "oricli-server=oricli_core.api.server:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="ai llm cognitive openai api",
)

