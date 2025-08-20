# TTS System API Documentation

## Overview

The TTS System provides a RESTful API for text-to-speech generation using multiple models (Kokkoro and Chatterbox) through a centralized gateway.

## Base URL

- **Local Development**: `http://localhost:8000`
- **Production**: `https://your-domain.com`
- **RunPod**: `https://api.runpod.ai/v2/your-endpoint-id/runsync`

## Authentication

Currently, the API is open. For production deployments, consider adding API key authentication.

## Endpoints

### Gateway Information

#### Get API Information
```http
GET /
```

**Response:**
```json
{
  "success": true,
  "audio_data": "UklGRnoGAABXQVZFZm10IBAAAAABAAEA...",
  "audio_format": "wav",
  "duration": 3.5,
  "sample_rate": 22050,
  "model_used": "kokkoro",
  "voice_used": "default",
  "language": "en",
  "processing_time": 1.2,
  "text_length": 42,
  "error": null,
  "warnings": null
}
```

**Error Response:**
```json
{
  "success": false,
  "audio_format": "wav",
  "sample_rate": 22050,
  "text_length": 42,
  "error": "Model endpoint not available",
  "processing_time": 0.1
}
```

#### Generate TTS Audio (Streaming)
```http
POST /tts/{model_name}/stream
```

Returns streaming audio data if supported by the model, otherwise falls back to regular generation.

**Response:** Binary audio data with appropriate content-type header.

## Model-Specific Information

### Kokkoro Model

**Endpoint:** `/tts/kokkoro`

**Characteristics:**
- **Languages:** Japanese (ja), English (en)
- **Voices:** default, cheerful, calm, energetic
- **Max Text Length:** 1000 characters
- **Optimal for:** Japanese text, anime-style voice
- **Sample Rates:** 16000, 22050, 44100

**Example Request:**
```json
{
  "text": "こんにちは、世界！今日はいい天気ですね。",
  "voice_id": "cheerful",
  "language": "ja",
  "speed": 1.1,
  "format": "wav"
}
```

### Chatterbox Model

**Endpoint:** `/tts/chatterbox`

**Characteristics:**
- **Languages:** English (en), Spanish (es), French (fr), German (de), Italian (it), Portuguese (pt)
- **Voices:** default, male, female, neutral, conversational, professional
- **Max Text Length:** 2000 characters
- **Optimal for:** Conversational text, multiple languages
- **Sample Rates:** 16000, 22050, 44100

**Example Request:**
```json
{
  "text": "Hello! This is a test of the Chatterbox TTS system. How are you today?",
  "voice_id": "conversational",
  "language": "en",
  "speed": 0.9,
  "format": "wav"
}
```

## Error Codes

| HTTP Code | Error | Description |
|-----------|-------|-------------|
| 200 | Success | Request completed successfully |
| 400 | Bad Request | Invalid model name or parameters |
| 422 | Validation Error | Invalid request body format |
| 500 | Internal Server Error | Server-side error |
| 503 | Service Unavailable | Model endpoint not available |
| 504 | Gateway Timeout | Model response timeout |

## Usage Examples

### cURL Examples

**Basic TTS Generation:**
```bash
curl -X POST "http://localhost:8000/tts/kokkoro" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello world!",
    "voice_id": "default",
    "language": "en"
  }'
```

**Advanced TTS Generation:**
```bash
curl -X POST "http://localhost:8000/tts/chatterbox" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "This is a more advanced example with custom settings.",
    "voice_id": "professional",
    "language": "en",
    "speed": 0.8,
    "pitch": 1.1,
    "volume": 1.2,
    "format": "wav",
    "sample_rate": 44100,
    "normalize": true,
    "remove_silence": true
  }'
```

**Health Check:**
```bash
curl "http://localhost:8000/health"
```

### Python Examples

**Basic Usage:**
```python
import requests
import base64

def generate_tts(text, model="chatterbox", voice="default"):
    url = f"http://localhost:8000/tts/{model}"
    
    payload = {
        "text": text,
        "voice_id": voice,
        "language": "en",
        "format": "wav"
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        data = response.json()
        if data["success"]:
            # Decode base64 audio data
            audio_bytes = base64.b64decode(data["audio_data"])
            
            # Save to file
            with open("output.wav", "wb") as f:
                f.write(audio_bytes)
            
            print(f"Audio generated: {data['duration']:.2f}s")
            return True
    
    return False

# Generate TTS
generate_tts("Hello, this is a test!")
```

**Advanced Usage with Error Handling:**
```python
import requests
import base64
import time

class TTSClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def check_health(self):
        """Check if the TTS service is healthy"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def list_models(self):
        """Get available models"""
        response = self.session.get(f"{self.base_url}/models")
        if response.status_code == 200:
            return response.json()
        return None
    
    def generate_tts(self, text, model="chatterbox", **kwargs):
        """Generate TTS audio"""
        url = f"{self.base_url}/tts/{model}"
        
        payload = {
            "text": text,
            "voice_id": kwargs.get("voice_id", "default"),
            "language": kwargs.get("language", "en"),
            "speed": kwargs.get("speed", 1.0),
            "pitch": kwargs.get("pitch", 1.0),
            "volume": kwargs.get("volume", 1.0),
            "format": kwargs.get("format", "wav"),
            "sample_rate": kwargs.get("sample_rate", 22050),
            "normalize": kwargs.get("normalize", True),
            "remove_silence": kwargs.get("remove_silence", False)
        }
        
        try:
            response = self.session.post(url, json=payload, timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                
                if data["success"]:
                    # Decode audio data
                    audio_bytes = base64.b64decode(data["audio_data"])
                    
                    return {
                        "success": True,
                        "audio_data": audio_bytes,
                        "metadata": {
                            "duration": data["duration"],
                            "sample_rate": data["sample_rate"],
                            "model_used": data["model_used"],
                            "processing_time": data["processing_time"]
                        }
                    }
                else:
                    return {
                        "success": False,
                        "error": data.get("error", "Unknown error")
                    }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except requests.RequestException as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}"
            }

# Usage example
client = TTSClient()

# Check if service is available
if client.check_health():
    print("TTS service is healthy")
    
    # Generate TTS
    result = client.generate_tts(
        text="Hello, this is an advanced TTS example!",
        model="chatterbox",
        voice_id="professional",
        speed=0.9,
        format="wav"
    )
    
    if result["success"]:
        # Save audio file
        with open("advanced_output.wav", "wb") as f:
            f.write(result["audio_data"])
        
        print(f"Generated {result['metadata']['duration']:.2f}s of audio")
        print(f"Processing time: {result['metadata']['processing_time']:.2f}s")
    else:
        print(f"TTS generation failed: {result['error']}")
else:
    print("TTS service is not available")
```

### JavaScript Examples

**Node.js Example:**
```javascript
const axios = require('axios');
const fs = require('fs');

class TTSClient {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
        this.client = axios.create({
            baseURL: baseUrl,
            timeout: 60000
        });
    }

    async generateTTS(text, options = {}) {
        const payload = {
            text: text,
            voice_id: options.voiceId || 'default',
            language: options.language || 'en',
            speed: options.speed || 1.0,
            pitch: options.pitch || 1.0,
            volume: options.volume || 1.0,
            format: options.format || 'wav',
            sample_rate: options.sampleRate || 22050,
            normalize: options.normalize !== false,
            remove_silence: options.removeSilence || false
        };

        try {
            const response = await this.client.post(`/tts/${options.model || 'chatterbox'}`, payload);
            
            if (response.data.success) {
                // Decode base64 audio
                const audioBuffer = Buffer.from(response.data.audio_data, 'base64');
                
                return {
                    success: true,
                    audioData: audioBuffer,
                    metadata: {
                        duration: response.data.duration,
                        sampleRate: response.data.sample_rate,
                        modelUsed: response.data.model_used,
                        processingTime: response.data.processing_time
                    }
                };
            } else {
                return {
                    success: false,
                    error: response.data.error
                };
            }
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    async checkHealth() {
        try {
            const response = await this.client.get('/health');
            return response.status === 200;
        } catch (error) {
            return false;
        }
    }
}

// Usage
async function main() {
    const client = new TTSClient();
    
    // Check health
    if (await client.checkHealth()) {
        console.log('TTS service is healthy');
        
        // Generate TTS
        const result = await client.generateTTS(
            'Hello from JavaScript!',
            {
                model: 'chatterbox',
                voiceId: 'conversational',
                speed: 1.1,
                format: 'wav'
            }
        );
        
        if (result.success) {
            // Save to file
            fs.writeFileSync('output.wav', result.audioData);
            console.log(`Generated ${result.metadata.duration.toFixed(2)}s of audio`);
        } else {
            console.error('TTS generation failed:', result.error);
        }
    } else {
        console.error('TTS service is not available');
    }
}

main().catch(console.error);
```

## Rate Limiting

Currently, there are no rate limits implemented. For production use, consider implementing:

- Request rate limiting per IP/API key
- Concurrent request limits per model
- Text length limits per time window

## Best Practices

1. **Always check service health** before making TTS requests
2. **Handle errors gracefully** with appropriate fallbacks
3. **Use appropriate timeouts** for your use case
4. **Cache generated audio** when possible to reduce load
5. **Monitor performance** and adjust parameters as needed
6. **Use streaming endpoints** for real-time applications when available
7. **Implement retry logic** with exponential backoff for production systems

## Troubleshooting

### Common Issues

1. **503 Service Unavailable**: Model endpoint is not ready or configured
2. **504 Gateway Timeout**: Text is too long or model is overloaded
3. **422 Validation Error**: Invalid request parameters
4. **Empty audio_data**: Check model logs for generation errors

### Debug Endpoints

- `GET /debug/config` - View current configuration (if debug mode enabled)
- `GET /health/models/{model_name}` - Check specific model status
- Review container logs for detailed error information
  "service": "TTS Gateway",
  "version": "1.0.0",
  "available_models": ["kokkoro", "chatterbox"],
  "endpoints": {
    "health": "/health",
    "generate": "/tts/{model_name}",
    "docs": "/docs"
  }
}
```

#### List Available Models
```http
GET /models
```

**Response:**
```json
{
  "models": {
    "kokkoro": {
      "available": true,
      "endpoint": "http://kokkoro:8001"
    },
    "chatterbox": {
      "available": true,
      "endpoint": "http://chatterbox:8002"
    }
  },
  "total_models": 2
}
```

### Health Checks

#### Gateway Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-14T10:30:00Z",
  "version": "1.0.0",
  "uptime": 3600.0,
  "request_count": 150,
  "models": {
    "kokkoro": true,
    "chatterbox": true
  },
  "memory_usage": 45.2,
  "cpu_usage": 12.8
}
```

#### Quick Health Check
```http
GET /health/quick
```

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2025-08-14T10:30:00Z"
}
```

#### Models Health Check
```http
GET /health/models
```

**Response:**
```json
{
  "models": {
    "kokkoro": {
      "healthy": true,
      "endpoint": "http://kokkoro:8001",
      "configured": true
    },
    "chatterbox": {
      "healthy": true,
      "endpoint": "http://chatterbox:8002",
      "configured": true
    }
  },
  "timestamp": "2025-08-14T10:30:00Z",
  "total_healthy": 2,
  "total_configured": 2
}
```

#### Individual Model Health
```http
GET /health/models/{model_name}
```

**Parameters:**
- `model_name`: Model name (`kokkoro` or `chatterbox`)

**Response:**
```json
{
  "model": "kokkoro",
  "healthy": true,
  "configured": true,
  "endpoint": "http://kokkoro:8001",
  "timestamp": "2025-08-14T10:30:00Z"
}
```

### TTS Generation

#### Generate TTS Audio
```http
POST /tts/{model_name}
```

**Parameters:**
- `model_name`: Model name (`kokkoro` or `chatterbox`)

**Request Body:**
```json
{
  "text": "Text to synthesize",
  "voice_id": "default",
  "language": "en",
  "speed": 1.0,
  "pitch": 1.0,
  "volume": 1.0,
  "format": "wav",
  "sample_rate": 22050,
  "normalize": true,
  "remove_silence": false
}
```

**Request Schema:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `text` | string | Yes | - | Text to synthesize (1-5000 chars) |
| `voice_id` | string | No | "default" | Voice identifier |
| `language` | string | No | "en" | Language code (e.g., "en", "ja") |
| `speed` | float | No | 1.0 | Speech speed (0.1-3.0) |
| `pitch` | float | No | 1.0 | Pitch multiplier (0.1-3.0) |
| `volume` | float | No | 1.0 | Volume multiplier (0.1-2.0) |
| `format` | string | No | "wav" | Audio format ("wav", "mp3") |
| `sample_rate` | integer | No | 22050 | Sample rate (8000-48000) |
| `normalize` | boolean | No | true | Normalize audio output |
| `remove_silence` | boolean | No | false | Remove leading/trailing silence |

**Response:**
```json
{
  "
