#!/usr/bin/env python3
"""
Pydantic models for TTS Gateway API
"""

from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field, validator


class TTSModel(str, Enum):
    """Available TTS models"""
    KOKKORO = "kokkoro"
    CHATTERBOX = "chatterbox"


class AudioFormat(str, Enum):
    """Supported audio formats"""
    WAV = "wav"
    MP3 = "mp3"
    OGG = "ogg"
    FLAC = "flac"


class TTSRequest(BaseModel):
    """Request model for TTS generation"""
    
    text: str = Field(..., min_length=1, max_length=5000, description="Text to synthesize")
    
    # Voice settings
    voice_id: Optional[str] = Field(None, description="Voice ID or name")
    language: Optional[str] = Field("en", description="Language code (e.g., 'en', 'ja', 'zh')")
    
    # Audio settings
    format: AudioFormat = Field(AudioFormat.WAV, description="Output audio format")
    sample_rate: Optional[int] = Field(22050, ge=8000, le=48000, description="Sample rate in Hz")
    
    # Synthesis settings
    speed: Optional[float] = Field(1.0, ge=0.1, le=3.0, description="Speech speed multiplier")
    pitch: Optional[float] = Field(1.0, ge=0.1, le=3.0, description="Pitch multiplier")
    volume: Optional[float] = Field(1.0, ge=0.1, le=2.0, description="Volume multiplier")
    
    # Model-specific parameters
    model_params: Optional[Dict[str, Any]] = Field(None, description="Model-specific parameters")
    
    # Processing options
    normalize: bool = Field(True, description="Normalize audio output")
    remove_silence: bool = Field(False, description="Remove leading/trailing silence")
    
    @validator("text")
    def validate_text(cls, v):
        """Validate input text"""
        if not v.strip():
            raise ValueError("Text cannot be empty or whitespace only")
        return v.strip()
    
    @validator("language")
    def validate_language(cls, v):
        """Validate language code"""
        if v and len(v) not in [2, 5]:  # 'en' or 'en-US' format
            raise ValueError("Language code must be 2 or 5 characters (e.g., 'en' or 'en-US')")
        return v.lower() if v else v

    class Config:
        schema_extra = {
            "example": {
                "text": "Hello, this is a sample text for TTS generation.",
                "voice_id": "default",
                "language": "en",
                "format": "wav",
                "sample_rate": 22050,
                "speed": 1.0,
                "pitch": 1.0,
                "volume": 1.0,
                "normalize": True,
                "remove_silence": False
            }
        }


class TTSResponse(BaseModel):
    """Response model for TTS generation"""
    
    success: bool = Field(..., description="Whether the generation was successful")
    
    # Audio data
    audio_data: Optional[str] = Field(None, description="Base64 encoded audio data")
    audio_format: AudioFormat = Field(..., description="Format of the audio data")
    
    # Metadata
    duration: Optional[float] = Field(None, ge=0, description="Audio duration in seconds")
    sample_rate: int = Field(..., ge=8000, le=48000, description="Audio sample rate")
    
    # Generation info
    model_used: str = Field(..., description="Model that generated the audio")
    voice_used: Optional[str] = Field(None, description="Voice that was used")
    language: Optional[str] = Field(None, description="Language used for synthesis")
    
    # Processing info
    processing_time: Optional[float] = Field(None, ge=0, description="Processing time in seconds")
    text_length: int = Field(..., ge=1, description="Length of input text")
    
    # Error handling
    error: Optional[str] = Field(None, description="Error message if success is False")
    warnings: Optional[List[str]] = Field(None, description="Any warnings during processing")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "audio_data": "UklGRnoGAABXQVZFZm10IBAAAAABAAEA...",
                "audio_format": "wav",
                "duration": 3.5,
                "sample_rate": 22050,
                "model_used": "kokkoro",
                "voice_used": "default",
                "language": "en",
                "processing_time": 1.2,
                "text_length": 42,
                "error": None,
                "warnings": None
            }
        }


class HealthResponse(BaseModel):
    """Response model for health checks"""
    
    status: str = Field(..., description="Service status")
    timestamp: str = Field(..., description="Current timestamp")
    version: str = Field(..., description="Service version")
    
    # Service info
    uptime: float = Field(..., ge=0, description="Service uptime in seconds")
    request_count: Optional[int] = Field(None, ge=0, description="Total requests processed")
    
    # Model availability
    models: Dict[str, bool] = Field(..., description="Model availability status")
    
    # System info
    memory_usage: Optional[float] = Field(None, ge=0, le=100, description="Memory usage percentage")
    cpu_usage: Optional[float] = Field(None, ge=0, le=100, description="CPU usage percentage")

    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2025-08-14T10:30:00Z",
                "version": "1.0.0",
                "uptime": 3600.0,
                "request_count": 150,
                "models": {
                    "kokkoro": True,
                    "chatterbox": True
                },
                "memory_usage": 45.2,
                "cpu_usage": 12.8
            }
        }


class ModelInfo(BaseModel):
    """Information about a specific TTS model"""
    
    name: str = Field(..., description="Model name")
    display_name: str = Field(..., description="Human-readable model name")
    description: str = Field(..., description="Model description")
    
    # Capabilities
    languages: List[str] = Field(..., description="Supported languages")
    voices: List[str] = Field(..., description="Available voices")
    formats: List[AudioFormat] = Field(..., description="Supported audio formats")
    
    # Specifications
    max_text_length: int = Field(..., ge=1, description="Maximum text length")
    sample_rates: List[int] = Field(..., description="Supported sample rates")
    
    # Status
    available: bool = Field(..., description="Whether the model is available")
    endpoint: Optional[str] = Field(None, description="Model endpoint URL")
    
    # Performance info
    avg_processing_time: Optional[float] = Field(None, ge=0, description="Average processing time per character")
    quality_rating: Optional[float] = Field(None, ge=1, le=5, description="Quality rating (1-5)")

    class Config:
        schema_extra = {
            "example": {
                "name": "kokkoro",
                "display_name": "Kokkoro TTS",
                "description": "High-quality Japanese TTS model",
                "languages": ["ja", "en"],
                "voices": ["kokkoro_default", "kokkoro_cheerful"],
                "formats": ["wav", "mp3"],
                "max_text_length": 1000,
                "sample_rates": [16000, 22050, 44100],
                "available": True,
                "endpoint": "http://kokkoro:8001",
                "avg_processing_time": 0.05,
                "quality_rating": 4.8
            }
        }


class ErrorResponse(BaseModel):
    """Error response model"""
    
    success: bool = Field(False, description="Always False for error responses")
    error: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code for programmatic handling")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: str = Field(..., description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")

    class Config:
        schema_extra = {
            "example": {
                "success": False,
                "error": "Model 'unknown_model' is not available",
                "error_code": "MODEL_NOT_FOUND",
                "details": {
                    "available_models": ["kokkoro", "chatterbox"],
                    "requested_model": "unknown_model"
                },
                "timestamp": "2025-08-14T10:30:00Z",
                "request_id": "req_12345"
            }
        }
