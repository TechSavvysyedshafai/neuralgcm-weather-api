"""
API Key Authentication & Rate Limiting
Simple in-memory API key management for monetization
"""
import os
import hashlib
import secrets
from datetime import datetime
from typing import Optional, Dict
from fastapi import HTTPException, Request, Depends
from fastapi.security import APIKeyHeader


# In-memory API key store (use Redis/DB in production)
API_KEYS: Dict[str, dict] = {}

# Demo API keys for testing (always available)
DEMO_KEYS = {
    "demo-free-key-2026": {
        "name": "Demo Free User",
        "tier": "free",
        "rate_limit": 10,  # requests per minute
        "created": datetime.utcnow().isoformat()
    },
    "demo-pro-key-2026": {
        "name": "Demo Pro User", 
        "tier": "pro",
        "rate_limit": 100,
        "created": datetime.utcnow().isoformat()
    }
}

# API Key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def generate_api_key() -> str:
    """Generate a secure API key"""
    return f"ngcm_{secrets.token_urlsafe(32)}"


def create_api_key(name: str, tier: str = "free") -> dict:
    """Create a new API key"""
    key = generate_api_key()
    
    rate_limits = {
        "free": 10,      # 10 req/min
        "starter": 60,   # 60 req/min
        "pro": 300,      # 300 req/min
        "enterprise": 1000  # 1000 req/min
    }
    
    key_data = {
        "name": name,
        "tier": tier,
        "rate_limit": rate_limits.get(tier, 10),
        "created": datetime.utcnow().isoformat(),
        "requests_today": 0,
        "last_request": None
    }
    
    API_KEYS[key] = key_data
    
    return {
        "api_key": key,
        **key_data
    }


def get_key_info(api_key: str) -> Optional[dict]:
    """Get API key information"""
    # Check demo keys first
    if api_key in DEMO_KEYS:
        return DEMO_KEYS[api_key]
    
    # Check registered keys
    if api_key in API_KEYS:
        return API_KEYS[api_key]
    
    return None


async def verify_api_key(
    request: Request,
    api_key: str = Depends(api_key_header)
) -> Optional[dict]:
    """
    Verify API key - allows both authenticated and unauthenticated requests
    Returns key info if provided, None for public endpoints
    """
    # If no API key provided, allow access (for demo/public endpoints)
    if not api_key:
        return None
    
    # Verify the key
    key_info = get_key_info(api_key)
    if not key_info:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key. Get a free key at /api/register"
        )
    
    return key_info


async def require_api_key(
    request: Request,
    api_key: str = Depends(api_key_header)
) -> dict:
    """
    Require valid API key for protected endpoints
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Get a free key at /api/register or use demo key: demo-free-key-2026"
        )
    
    key_info = get_key_info(api_key)
    if not key_info:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    return key_info


# Rate limit tracking (simple in-memory)
REQUEST_COUNTS: Dict[str, list] = {}

def check_rate_limit(api_key: str, limit: int) -> bool:
    """Check if request is within rate limit"""
    import time
    now = time.time()
    minute_ago = now - 60
    
    if api_key not in REQUEST_COUNTS:
        REQUEST_COUNTS[api_key] = []
    
    # Clean old requests
    REQUEST_COUNTS[api_key] = [t for t in REQUEST_COUNTS[api_key] if t > minute_ago]
    
    # Check limit
    if len(REQUEST_COUNTS[api_key]) >= limit:
        return False
    
    # Record request
    REQUEST_COUNTS[api_key].append(now)
    return True
