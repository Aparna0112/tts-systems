#!/usr/bin/env python3
"""
Kokkoro TTS Model Service
"""

import os
import time
import base64
import logging
from io import BytesIO
from typing import Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from model import KokkoroTTS, TTSError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Kokkoro TTS Service",
    description="Kokkoro Text-to-Speech model service",
    version="1.0.0"
)

# Global model instance
tts_model: Optional[KokkoroTTS] = None

@app.on_event("startup")
async def startup_event():
    """Initialize the TTS model on startup"""
    global tts_model
    
    logger.info("Initializing Kokkoro TTS model...")
    
    try:
        tts_model = KokkoroTTS()
        
        # Preload model if environment variable is set
        if os.getenv("PRELOAD_MODEL", "false").lower() == "true":
            logger.info("Preloading model...")
            await tts_model.load_model()
            logger.info("Model preloaded successfully")
        
        logger.info("Kokkoro TTS service started successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize Kokkoro TTS model: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global tts_model
    
    logger.info("Shutting down Kokkoro TTS service...")
    
    if tts_model:
        await tts_model.cleanup()
    
    logger.info("Kokkoro TTS service shut down")

class TTSRequest(BaseModel):
    """TTS generation request"""
    text: str = Field(..., min_length=1, max_length=1000)
    voice_id: Optional[str] = Field("default", description="Voice ID")
    language: Optional[str] = Field("ja", description="Language code")
    speed: Optional[float] = Field(1.0, ge=0.1, le=3.0)
    pitch: Optional[float] = Field(1.0, ge=0.1, le=3.0)
    volume: Optional[float] = Field(1.0, ge=0.1, le=2.0)
    format: Optional[str] = Field("wav", description="Audio format")
    sample_rate: Optional[int] = Field(22050, ge=8000, le=48000)
    normalize: Optional[bool] = Field(True)
    remove_silence: Optional[bool] = Field(False)

class TTSResponse(BaseModel):
    """TTS generation response"""
    success: bool
    audio_data: Optional[str] = None
    audio_format: str
    duration: Optional[float] = None
    sample_rate: int
    model_used: str = "kokkoro"
    voice_used: Optional[str] = None
    language: Optional[str] = None
    processing_time: Optional[float] = None
    text_length: int
    error: Optional[str] = None
    warnings: Optional[list] = None

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Kokkoro TTS",
        "version": "1.0.0",
        "model": "kokkoro",
        "status": "ready" if tts_model and tts_model.is_loaded else "loading"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if not tts_model:
        return JSONResponse(
            content={"status": "error", "message": "Model not initialized"},
            status_code=503
        )
    
    return {
        "status": "healthy",
        "model_loaded": tts_model.is_loaded,
        "timestamp": time.time(),
        "version": "1.0.0"
    }

@app.get("/info")
async def model_info():
    """Get model information"""
    return {
        "name": "kokkoro",
        "display_name": "Kokkoro TTS",
        "description": "High-quality Japanese TTS model with Kokkoro voice",
        "languages": ["ja", "en"],
        "voices": ["default", "cheerful", "calm"],
        "formats": ["wav", "mp3"],
        "max_text_length": 1000,
        "sample_rates": [16000, 22050, 44100],
        "capabilities": {
            "speed_control": True,
            "pitch_control": True,
            "emotion_control": True,
            "multi_language": True
        }
    }

@app.post("/generate", response_model=TTSResponse)
async def generate_tts(request: TTSRequest) -> TTSResponse:
    """
    Generate TTS audio from text
    """
    if not tts_model:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TTS model not initialized"
        )
    
    start_time = time.time()
    
    try:
        # Generate audio
        logger.info(f"Generating TTS for text: '{request.text[:50]}...'")
        
        audio_data, metadata = await tts_model.generate(
            text=request.text,
            voice_id=request.voice_id,
            language=request.language,
            speed=request.speed,
            pitch=request.pitch,
            volume=request.volume,
            format=request.format,
            sample_rate=request.sample_rate,
            normalize=request.normalize,
            remove_silence=request.remove_silence
        )
        
        # Convert audio to base64
        if isinstance(audio_data, bytes):
            audio_b64 = base64.b64encode(audio_data).decode('utf-8')
        else:
            # If audio_data is a file path or BytesIO
            if hasattr(audio_data, 'read'):
                audio_bytes = audio_data.read()
            else:
                with open(audio_data, 'rb') as f:
                    audio_bytes = f.read()
            audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        processing_time = time.time() - start_time
        
        logger.info(f"TTS generation completed in {processing_time:.2f}s")
        
        return TTSResponse(
            success=True,
            audio_data=audio_b64,
            audio_format=request.format or "wav",
            duration=metadata.get("duration"),
            sample_rate=metadata.get("sample_rate", request.sample_rate),
            voice_used=request.voice_id,
            language=request.language,
            processing_time=processing_time,
            text_length=len(request.text),
            warnings=metadata.get("warnings")
        )
        
    except TTSError as e:
        logger.error(f"TTS generation failed: {str(e)}")
        return TTSResponse(
            success=False,
            audio_format=request.format or "wav",
            sample_rate=request.sample_rate or 22050,
            text_length=len(request.text),
            error=str(e),
            processing_time=time.time() - start_time
        )
        
    except Exception as e:
        logger.error(f"Unexpected error during TTS generation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@app.post("/preload")
async def preload_model():
    """Preload the model for faster inference"""
    if not tts_model:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TTS model not initialized"
        )
    
    if tts_model.is_loaded:
        return {"status": "already_loaded", "message": "Model is already loaded"}
    
    try:
        await tts_model.load_model()
        return {"status": "loaded", "message": "Model loaded successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load model: {str(e)}"
        )

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
