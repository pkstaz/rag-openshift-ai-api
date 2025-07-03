#!/usr/bin/env python3
"""
Setup configuration for RAG OpenShift AI API
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="rag-openshift-ai-api",
    version="0.1.0",
    author="Carlos Estay",
    author_email="cestay@redhat.com",
    description="A Retrieval-Augmented Generation (RAG) agent for OpenShift AI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pkstaz/rag-openshift-ai-api",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-cov>=4.1.0",
            "black>=23.11.0",
            "flake8>=6.1.0",
            "mypy>=1.7.1",
        ],
    },
    entry_points={
        "console_scripts": [
            "rag-api=main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
) 