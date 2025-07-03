"""
Configuration Management Package

This package handles all configuration settings for the RAG agent,
including environment variables, model settings, and service configurations.
"""

from .settings import Settings, settings

__all__ = ["Settings", "settings"] 