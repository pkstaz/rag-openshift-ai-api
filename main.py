#!/usr/bin/env python3
"""
RAG OpenShift AI API - Main Entry Point

This is the main entry point for the RAG OpenShift AI API application.
It imports and runs the FastAPI application defined in src/main.py.
"""

import uvicorn
from src.config.settings import settings

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.environment == "development",
        log_level=settings.logging.level.lower(),
        access_log=True
    ) 