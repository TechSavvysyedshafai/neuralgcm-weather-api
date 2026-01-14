"""
NeuralGCM Weather Prediction API
AI-powered weather forecasting inspired by Google's NeuralGCM model
With API key authentication and rate limiting for monetization
"""
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv

from weather_client import get_client
from auth import (
    verify_api_key, require_api_key, create_api_key,
    get_key_info, check_rate_limit
)

# Load environment variables
load_dotenv()

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI app
app = FastAPI(
    title="NeuralGCM Weather API",
    description="""
## AI-Powered Weather Prediction API

15-day precipitation forecasts powered by NeuralGCM-inspired AI + Open-Meteo data.

### Authentication
- **Free tier**: Use demo key `demo-free-key-2026` (10 req/min)
- **Pro tier**: Register for higher limits at `/api/register`

### Rate Limits
| Tier | Requests/min | Monthly Price |
|------|-------------|---------------|
| Free | 10 | $0 |
| Starter | 60 | $29 |
| Pro | 300 | $99 |
| Enterprise | 1000 | $499 |
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add rate limit handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def serve_frontend():
    """Serve the main frontend page"""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse(
        status_code=404,
        content={"error": "Frontend not found"}
    )


@app.get("/health")
async def health_check():
    """API health check endpoint"""
    return {
        "status": "healthy",
        "service": "NeuralGCM Weather API",
        "version": "1.0.0",
        "model": "NeuralGCM-inspired + Open-Meteo",
        "pricing": {
            "free": "10 req/min - $0",
            "starter": "60 req/min - $29/mo",
            "pro": "300 req/min - $99/mo",
            "enterprise": "1000 req/min - $499/mo"
        }
    }


# ============== API Key Management ==============

@app.post("/api/register")
async def register_api_key(name: str = Query(..., description="Your name or company")):
    """
    Register for a FREE API key
    
    Returns a unique API key for accessing the weather API.
    Free tier: 10 requests/minute
    """
    key_data = create_api_key(name, tier="free")
    return {
        "success": True,
        "message": "API key created! Save it securely - it won't be shown again.",
        **key_data,
        "usage": "Add header: X-API-Key: <your-key>",
        "upgrade": "Contact us for higher rate limits"
    }


@app.get("/api/key-info")
async def get_api_key_info(key_info: dict = Depends(require_api_key)):
    """Get information about your API key (requires API key)"""
    return {
        "success": True,
        "key_info": key_info
    }


# ============== Weather Endpoints ==============

@app.get("/forecast/{latitude}/{longitude}")
@limiter.limit("30/minute")
async def get_forecast(
    request: Request,
    latitude: float,
    longitude: float,
    days: int = Query(default=15, ge=1, le=16, description="Number of forecast days"),
    key_info: Optional[dict] = Depends(verify_api_key)
):
    """
    Get weather forecast for a location
    
    - **latitude**: Location latitude (-90 to 90)
    - **longitude**: Location longitude (-180 to 180)
    - **days**: Number of forecast days (1-16, default 15)
    
    Returns precipitation, temperature, and weather conditions.
    """
    # Validate coordinates
    if not -90 <= latitude <= 90:
        raise HTTPException(status_code=400, detail="Latitude must be between -90 and 90")
    if not -180 <= longitude <= 180:
        raise HTTPException(status_code=400, detail="Longitude must be between -180 and 180")
    
    client = get_client()
    result = await client.get_forecast(latitude, longitude, days)
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
    
    # Add tier info if authenticated
    if key_info:
        result["authenticated"] = True
        result["tier"] = key_info.get("tier", "free")
    else:
        result["authenticated"] = False
        result["tier"] = "public"
    
    return result


@app.get("/api/precipitation")
@limiter.limit("30/minute")
async def get_precipitation(
    request: Request,
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    days: int = Query(default=15, ge=1, le=16)
):
    """Get detailed precipitation forecast"""
    client = get_client()
    result = await client.get_forecast(lat, lon, days)
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    precipitation_forecast = []
    for day in result.get("forecast", []):
        precipitation_forecast.append({
            "date": day["date"],
            "precipitation_mm": day["precipitation"]["amount"],
            "probability_percent": day["precipitation"]["probability"],
            "conditions": day["conditions"]["description"],
            "icon": day["conditions"]["icon"]
        })
    
    return {
        "location": result["location"],
        "precipitation": precipitation_forecast,
        "summary": {
            "total_mm": result["summary"]["total_precipitation_mm"],
            "rainy_days": result["summary"]["rainy_days"]
        }
    }


@app.get("/api/extreme-events")
@limiter.limit("20/minute")
async def get_extreme_events(
    request: Request,
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude")
):
    """Check for extreme weather events"""
    client = get_client()
    result = await client.get_extreme_events(lat, lon)
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result


# Preset locations
PRESET_LOCATIONS = {
    "delhi": {"lat": 28.6139, "lon": 77.2090, "name": "Delhi, India"},
    "mumbai": {"lat": 19.0760, "lon": 72.8777, "name": "Mumbai, India"},
    "bangalore": {"lat": 12.9716, "lon": 77.5946, "name": "Bangalore, India"},
    "chennai": {"lat": 13.0827, "lon": 80.2707, "name": "Chennai, India"},
    "kolkata": {"lat": 22.5726, "lon": 88.3639, "name": "Kolkata, India"},
    "patna": {"lat": 25.5941, "lon": 85.1376, "name": "Patna, India"},
    "london": {"lat": 51.5074, "lon": -0.1278, "name": "London, UK"},
    "newyork": {"lat": 40.7128, "lon": -74.0060, "name": "New York, USA"},
    "tokyo": {"lat": 35.6762, "lon": 139.6503, "name": "Tokyo, Japan"},
    "sydney": {"lat": -33.8688, "lon": 151.2093, "name": "Sydney, Australia"},
}


@app.get("/api/presets")
async def get_presets():
    """Get preset locations for quick access"""
    return {"locations": PRESET_LOCATIONS}


@app.get("/api/location/{city}")
@limiter.limit("30/minute")
async def get_by_city(
    request: Request,
    city: str,
    days: int = Query(default=15, ge=1, le=16)
):
    """Get forecast for a preset city"""
    city_lower = city.lower()
    if city_lower not in PRESET_LOCATIONS:
        raise HTTPException(
            status_code=404,
            detail=f"City '{city}' not found. Available: {', '.join(PRESET_LOCATIONS.keys())}"
        )
    
    location = PRESET_LOCATIONS[city_lower]
    client = get_client()
    result = await client.get_forecast(location["lat"], location["lon"], days)
    
    if result.get("success"):
        result["location"]["name"] = location["name"]
    
    return result


# ============== Startup ==============

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8001))
    
    print("\n" + "="*60)
    print("🌧️ NeuralGCM Weather Prediction API")
    print("="*60)
    print("📡 AI-powered global precipitation forecasting")
    print("📊 15-day forecasts • Extreme event alerts • Real-time data")
    print("🔑 API Keys: demo-free-key-2026 (free tier)")
    print(f"\n🌐 Open http://localhost:{port} in your browser")
    print(f"📚 API Docs: http://localhost:{port}/docs")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=port)
