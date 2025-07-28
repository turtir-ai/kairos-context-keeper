#!/usr/bin/env python3
"""
Setup script for Kairos: The Context Keeper
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# Read requirements
requirements = []
try:
    with open('requirements.txt', 'r') as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
except FileNotFoundError:
    print("Warning: requirements.txt not found")

setup(
    name="kairos-context-keeper",
    version="0.5.0",
    author="Kairos Development Team",
    author_email="info@kairos-ai.dev",
    description="Autonomous Development Supervisor powered by Context Engineering",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-username/Kairos_The_Context_Keeper",
    project_urls={
        "Bug Tracker": "https://github.com/your-username/Kairos_The_Context_Keeper/issues",
        "Documentation": "https://kairos-ai.dev/docs",
        "Source Code": "https://github.com/your-username/Kairos_The_Context_Keeper",
    },
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: System :: Distributed Computing",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
            "pre-commit>=3.0.0",
        ],
        "gpu": [
            "torch[cuda]",
            "transformers[torch]",
        ],
        "full": [
            "neo4j>=5.0.0",
            "qdrant-client>=1.7.0",
            "spacy>=3.7.0",
            "opencv-python>=4.8.0",
            "librosa>=0.10.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "kairos=cli:main",
            "kairos-daemon=src.daemon:main",
            "kairos-benchmark=scripts.benchmark:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.toml", "*.yaml", "*.yml", "*.json", "*.md", "*.txt"],
    },
    zip_safe=False,
    keywords=[
        "artificial-intelligence",
        "context-engineering", 
        "autonomous-development",
        "multi-agent-system",
        "knowledge-graph",
        "memory-management",
        "llm-routing",
        "fastapi",
        "asyncio",
    ],
)
