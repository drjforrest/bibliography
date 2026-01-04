"""
OpenRouter API helper for checking credit balance and model availability.
"""

import httpx
from typing import Optional, Dict, Any


async def check_openrouter_balance(api_key: str) -> Dict[str, Any]:
    """
    Check OpenRouter credit balance and limits for a given API key.
    
    Returns:
        {
            "success": bool,
            "data": {
                "balance": float,  # USD remaining
                "usage": float,    # USD used
                "limit": float,    # USD limit (if any)
                "is_free_tier": bool
            },
            "error": Optional[str]
        }
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://openrouter.ai/api/v1/auth/key",
                headers={
                    "Authorization": f"Bearer {api_key}",
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                key_data = data.get("data", {})
                
                # Extract credit information
                limit = key_data.get("limit", 0)
                usage = key_data.get("usage", 0)
                balance = limit - usage if limit > 0 else 0
                is_free_tier = key_data.get("is_free_tier", False)
                
                return {
                    "success": True,
                    "data": {
                        "balance": balance,
                        "usage": usage,
                        "limit": limit,
                        "is_free_tier": is_free_tier,
                        "label": key_data.get("label", ""),
                    },
                    "error": None
                }
            elif response.status_code == 401:
                return {
                    "success": False,
                    "data": None,
                    "error": "Invalid API key"
                }
            else:
                return {
                    "success": False,
                    "data": None,
                    "error": f"OpenRouter API error: {response.status_code}"
                }
                
    except httpx.TimeoutException:
        return {
            "success": False,
            "data": None,
            "error": "Request timed out"
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }


async def estimate_generation_cost(
    generation_type: str,
    model: Optional[str] = None
) -> Dict[str, float]:
    """
    Estimate cost for different generation types.
    
    Args:
        generation_type: "podcast", "infographic", or "summary"
        model: Optional specific model (uses defaults if not provided)
        
    Returns:
        {
            "min_cost": float,
            "typical_cost": float,
            "max_cost": float,
            "currency": "USD"
        }
    """
    # Based on typical usage patterns
    estimates = {
        "podcast": {
            "min_cost": 0.12,
            "typical_cost": 0.14,
            "max_cost": 0.20,
            "details": "~20k input + 750 output tokens (Claude Sonnet 4)"
        },
        "infographic": {
            "min_cost": 0.03,
            "typical_cost": 0.04,
            "max_cost": 0.08,
            "details": "Single 1024x1024 image (Imagen 3 Fast)"
        },
        "summary": {
            "min_cost": 0.01,
            "typical_cost": 0.03,
            "max_cost": 0.05,
            "details": "~10k input + 500 output tokens (Claude Sonnet 4)"
        }
    }
    
    return {
        **estimates.get(generation_type, estimates["summary"]),
        "currency": "USD"
    }
