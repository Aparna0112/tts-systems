#!/usr/bin/env python3
"""
TTS Gateway Service - Routes requests to appropriate TTS models
"""

import os
import asyncio
import httpx
import logging
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, status
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from config import Settings, get_settings
from models import TTSRequest, TTSResponse, HealthResponse
from health import health_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global HTTP client
http_client: Optional[httpx.AsyncClient] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global http_client
    
    # Startup
    logger.info("Starting TTS Gateway...")
    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(60.0),
        limits=httpx.Limits(max_keepalive_connections=10, max_connections=100)
    )
    
    # Validate model endpoints on startup
    settings = get_settings()
    await validate_model_endpoints(settings)
    
    yield
    
    # Shutdown
    logger.info("Shutting down TTS Gateway...")
    if http_client:
        await http_client.aclose()

# Create FastAPI app
app = FastAPI(
    title="TTS Gateway",
    description="Centralized gateway for multiple TTS models",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include health check router
app.include_router(health_router, prefix="/health", tags=["health"])

# Model endpoint mappings
MODEL_ENDPOINTS = {
    "kokkoro": "KOKKORO_ENDPOINT",
    "chatterbox": "CHATTERBOX_ENDPOINT"
}

async def validate_model_endpoints(settings: Settings) -> None:
    """Validate that all model endpoints are accessible"""
    if not http_client:
        logger.error("HTTP client not initialized")
        return
        
    for model_name, env_var in MODEL_ENDPOINTS.items():
        endpoint = getattr(settings, env_var.lower(), None)
        if not endpoint:
            logger.warning(f"No endpoint configured for {model_name}")
            continue
            
        try:
            response = await http_client.get(f"{endpoint}/health", timeout=10.0)
            if response.status_code == 200:
                logger.info(f"✓ {model_name} endpoint is healthy: {endpoint}")
            else:
                logger.warning(f"✗ {model_name} endpoint unhealthy: {endpoint} (status: {response.status_code})")
        except Exception as e:
            logger.error(f"✗ Cannot reach {model_name} endpoint {endpoint}: {str(e)}")

async def get_http_client() -> httpx.AsyncClient:
    """Dependency to get HTTP client"""
    if not http_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="HTTP client not available"
        )
    return http_client

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "TTS Gateway",
        "version": "1.0.0",
        "available_models": list(MODEL_ENDPOINTS.keys()),
        "endpoints": {
            "health": "/health",
            "generate": "/tts/{model_name}",
            "docs": "/docs"
        }
    }

@app.get("/models")
async def list_models():
    """List available TTS models"""
    settings = get_settings()
    models_status = {}
    
    for model_name, env_var in MODEL_ENDPOINTS.items():
        endpoint = getattr(settings, env_var.lower(), None)
        models_status[model_name] = {
            "available": bool(endpoint),
            "endpoint": endpoint if endpoint else "Not configured"
        }
    
    return {
        "models": models_status,
        "total_models": len(MODEL_ENDPOINTS)
    }

async def forward_request(
    endpoint: str, 
    request_data: dict, 
    client: httpx.AsyncClient,
    timeout: float = 60.0
) -> httpx.Response:
    """Forward request to model endpoint with proper error handling"""
    try:
        logger.info(f"Forwarding request to: {endpoint}")
        logger.debug(f"Request data: {request_data}")
        
        response = await client.post(
            f"{endpoint}/generate",
            json=request_data,
            timeout=timeout,
            headers={"Content-Type": "application/json"}
        )
        
        logger.info(f"Received response from {endpoint}: {response.status_code}")
        return response
        
    except httpx.TimeoutException:
        logger.error(f"Timeout while forwarding to {endpoint}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Model endpoint timeout: {endpoint}"
        )
    except httpx.RequestError as e:
        logger.error(f"Request error while forwarding to {endpoint}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Cannot reach model endpoint: {endpoint}"
        )
    except Exception as e:
        logger.error(f"Unexpected error while forwarding to {endpoint}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@app.post("/tts/{model_name}", response_model=TTSResponse)
async def generate_tts(
    model_name: str,
    request: TTSRequest,
    settings: Settings = Depends(get_settings),
    client: httpx.AsyncClient = Depends(get_http_client)
) -> TTSResponse:
    """
    Generate TTS audio using specified model
    
    Args:
        model_name: Name of the TTS model (kokkoro, chatterbox)
        request: TTS generation request
        
    Returns:
        TTSResponse with generated audio data
    """
    
    # Validate model name
    if model_name not in MODEL_ENDPOINTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown model: {model_name}. Available models: {list(MODEL_ENDPOINTS.keys())}"
        )
    
    # Get model endpoint
    env_var = MODEL_ENDPOINTS[model_name]
    endpoint = getattr(settings, env_var.lower(), None)
    
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Model {model_name} is not configured. Please set {env_var} environment variable."
        )
    
    # Prepare request data
    request_data = request.dict()
    request_data["model"] = model_name  # Add model info for the endpoint
    
    # Forward request to model endpoint
    try:
        response = await forward_request(endpoint, request_data, client)
        
        # Handle successful response
        if response.status_code == 200:
            response_data = response.json()
            return TTSResponse(**response_data)
        
        # Handle error responses from model endpoint
        elif response.status_code == 422:
            error_detail = response.json().get("detail", "Validation error")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Model validation error: {error_detail}"
            )
        else:
            error_detail = response.text if response.text else f"HTTP {response.status_code}"
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Model endpoint error: {error_detail}"
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generate_tts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@app.post("/tts/{model_name}/stream")
async def generate_tts_stream(
    model_name: str,
    request: TTSRequest,
    settings: Settings = Depends(get_settings),
    client: httpx.AsyncClient = Depends(get_http_client)
):
    """
    Generate TTS audio with streaming response (if supported by model)
    """
    
    if model_name not in MODEL_ENDPOINTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown model: {model_name}"
        )
    
    env_var = MODEL_ENDPOINTS[model_name]
    endpoint = getattr(settings, env_var.lower(), None)
    
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Model {model_name} is not configured"
        )
    
    # Try streaming endpoint first, fall back to regular if not available
    stream_endpoint = f"{endpoint}/generate/stream"
    request_data = request.dict()
    request_data["model"] = model_name
    
    try:
        async with client.stream('POST', stream_endpoint, json=request_data, timeout=120.0) as response:
            if response.status_code == 404:
                # Streaming not supported, fall back to regular endpoint
                logger.info(f"Streaming not supported for {model_name}, falling back to regular endpoint")
                return await generate_tts(model_name, request, settings, client)
            
            response.raise_for_status()
            
            async def generate():
                async for chunk in response.aiter_bytes():
                    yield chunk
            
            return Response(
                generate(),
                media_type="audio/wav",
                headers={"Content-Disposition": f"attachment; filename=tts_{model_name}.wav"}
            )
    
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            # Streaming not supported, fall back to regular endpoint
            return await generate_tts(model_name, request, settings, client)
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Model endpoint error: {e.response.text}"
        )

if __name__ == "__main__":
    # Load settings
    settings = get_settings()
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        log_level="info",
        reload=settings.debug
    )
