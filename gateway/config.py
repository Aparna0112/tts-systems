#!/usr/bin/env python3
"""
Configuration management for TTS Gateway
"""

import os
from functools import lru_cache
from typing import Optional

from pydantic import BaseSettings, validator


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Server configuration
    port: int = 8000
    debug: bool = False
    log_level: str = "info"
    
    # Model endpoints - these should be set via environment variables
    kokkoro_endpoint: Optional[str] = None
    chatterbox_endpoint: Optional[str] = None
    
    # RunPod specific settings
    runpod_api_key: Optional[str] = None
    runpod_endpoint_id: Optional[str] = None
    
    # Request settings
    default_timeout: float = 60.0
    max_retries: int = 3
    
    # Security settings (for production)
    api_key: Optional[str] = None
    allowed_origins: list = ["*"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @validator("kokkoro_endpoint", "chatterbox_endpoint")
    def validate_endpoints(cls, v):
        """Validate endpoint URLs"""
        if v and not v.startswith(("http://", "https://")):
            raise ValueError("Endpoint must start with http:// or https://")
        return v
    
    @validator("port")
    def validate_port(cls, v):
        """Validate port number"""
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v
    
    def get_model_endpoint(self, model_name: str) -> Optional[str]:
        """Get endpoint for specific model"""
        return getattr(self, f"{model_name}_endpoint", None)
    
    def is_model_available(self, model_name: str) -> bool:
        """Check if model endpoint is configured"""
        endpoint = self.get_model_endpoint(model_name)
        return endpoint is not None and endpoint.strip() != ""


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


def load_environment():
    """Load environment variables from .env file if it exists"""
    env_file = ".env"
    if os.path.exists(env_file):
        from dotenv import load_dotenv
        load_dotenv(env_file)
        print(f"Loaded environment variables from {env_file}")
    else:
        print("No .env file found, using system environment variables")


# Load environment on import
load_environment()


# Development/testing helper functions
def get_development_settings() -> Settings:
    """Get settings configured for development"""
    return Settings(
        debug=True,
        log_level="debug",
        kokkoro_endpoint="http://kokkoro:8001",
        chatterbox_endpoint="http://chatterbox:8002",
        allowed_origins=["http://localhost:3000", "http://127.0.0.1:3000"]
    )


def get_production_settings() -> Settings:
    """Get settings configured for production"""
    return Settings(
        debug=False,
        log_level="info",
        # Production endpoints should be set via environment variables
    )


def get_runpod_settings() -> Settings:
    """Get settings configured for RunPod deployment"""
    return Settings(
        debug=False,
        log_level="info",
        port=int(os.getenv("PORT", 8000)),
        # RunPod endpoints will be set via environment variables
        kokkoro_endpoint=os.getenv("KOKKORO_ENDPOINT"),
        chatterbox_endpoint=os.getenv("CHATTERBOX_ENDPOINT"),
        runpod_api_key=os.getenv("RUNPOD_API_KEY"),
        runpod_endpoint_id=os.getenv("RUNPOD_ENDPOINT_ID")
    )
