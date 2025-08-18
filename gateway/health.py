#!/usr/bin/env python3
"""
Health check endpoints for TTS Gateway
"""

import time
import psutil
import asyncio
import httpx
from datetime import datetime, timezone
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from models import HealthResponse, ModelInfo
from config import Settings, get_settings

# Global variables for tracking
start_time = time.time()
request_counter = 0

health_router = APIRouter()

def increment_request_count():
    """Increment global request counter"""
    global request_counter
    request_counter += 1

def get_uptime() -> float:
    """Get service uptime in seconds"""
    return time.time() - start_time

def get_system_stats() -> Dict[str, Optional[float]]:
    """Get system resource usage statistics"""
    try:
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        
        return {
            "memory_usage": memory.percent,
            "cpu_usage": cpu_percent
        }
    except Exception:
        return {
            "memory_usage": None,
            "cpu_usage": None
        }

async def check_model_health(endpoint: str, timeout: float = 5.0) -> bool:
    """Check if a model endpoint is healthy"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{endpoint}/health", timeout=timeout)
            return response.status_code == 200
    except Exception:
        return False

async def get_models_status(settings: Settings) -> Dict[str, bool]:
    """Get health status of all configured models"""
    models_status = {}
    
    # Check Kokkoro
    if settings.kokkoro_endpoint:
        models_status["kokkoro"] = await check_model_health(settings.kokkoro_endpoint)
    else:
        models_status["kokkoro"] = False
    
    # Check Chatterbox
    if settings.chatterbox_endpoint:
        models_status["chatterbox"] = await check_model_health(settings.chatterbox_endpoint)
    else:
        models_status["chatterbox"] = False
    
    return models_status

@health_router.get("/", response_model=HealthResponse)
async def health_check(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """
    Comprehensive health check endpoint
    Returns overall service health and model availability
    """
    increment_request_count()
    
    # Get system stats
    system_stats = get_system_stats()
    
    # Check model availability
    models_status = await get_models_status(settings)
    
    # Determine overall status
    any_model_available = any(models_status.values())
    overall_status = "healthy" if any_model_available else "degraded"
    
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="1.0.0",
        uptime=get_uptime(),
        request_count=request_counter,
        models=models_status,
        memory_usage=system_stats["memory_usage"],
        cpu_usage=system_stats["cpu_usage"]
    )

@health_router.get("/quick")
async def quick_health_check():
    """
    Quick health check for load balancers
    Returns simple OK/ERROR response
    """
    increment_request_count()
    
    return JSONResponse(
        content={"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()},
        status_code=200
    )

@health_router.get("/models")
async def models_health_check(settings: Settings = Depends(get_settings)):
    """
    Detailed health check for all models
    """
    models_status = await get_models_status(settings)
    
    detailed_status = {}
    for model_name, is_healthy in models_status.items():
        endpoint = getattr(settings, f"{model_name}_endpoint", None)
        detailed_status[model_name] = {
            "healthy": is_healthy,
            "endpoint": endpoint,
            "configured": bool(endpoint)
        }
    
    return {
        "models": detailed_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_healthy": sum(models_status.values()),
        "total_configured": len([m for m in detailed_status.values() if m["configured"]])
    }

@health_router.get("/models/{model_name}")
async def single_model_health_check(
    model_name: str, 
    settings: Settings = Depends(get_settings)
):
    """
    Health check for a specific model
    """
    if model_name not in ["kokkoro", "chatterbox"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_name}' not found"
        )
    
    endpoint = getattr(settings, f"{model_name}_endpoint", None)
    
    if not endpoint:
        return JSONResponse(
            content={
                "model": model_name,
                "healthy": False,
                "configured": False,
                "error": f"Model {model_name} is not configured",
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            status_code=503
        )
    
    is_healthy = await check_model_health(endpoint)
    
    status_code = 200 if is_healthy else 503
    
    return JSONResponse(
        content={
            "model": model_name,
            "healthy": is_healthy,
            "configured": True,
            "endpoint": endpoint,
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        status_code=status_code
    )

@health_router.get("/stats")
async def service_stats():
    """
    Service statistics and metrics
    """
    system_stats = get_system_stats()
    
    return {
        "uptime_seconds": get_uptime(),
        "total_requests": request_counter,
        "requests_per_second": request_counter / max(get_uptime(), 1),
        "memory_usage_percent": system_stats["memory_usage"],
        "cpu_usage_percent": system_stats["cpu_usage"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
