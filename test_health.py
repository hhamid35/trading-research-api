#!/usr/bin/env python3
"""Test script to verify health check endpoints work correctly."""
import asyncio
import sys
from app.main import create_app
from app.config import get_settings


async def test_health_checks():
    """Test all health check endpoints."""
    print("=" * 60)
    print("Testing Health Check Endpoints")
    print("=" * 60)
    
    # Create the application
    print("\n1. Creating FastAPI application...")
    app = create_app()
    print("   ✓ Application created successfully\n")
    
    # Get settings for comparison
    settings = get_settings()
    
    # Import the health check functions
    from app.routers.health import check_database, check_qdrant, check_searxng
    
    print("2. Testing Database Health Check...")
    try:
        db_result = await check_database(str(settings.db_url), settings.health_check_timeout)
        print(f"   Status: {db_result.status}")
        print(f"   Duration: {db_result.duration_ms:.2f}ms")
        if db_result.error:
            print(f"   Error: {db_result.error}")
        print()
    except Exception as e:
        print(f"   ✗ Exception: {e}\n")
    
    print("3. Testing Qdrant Health Check...")
    try:
        qdrant_result = await check_qdrant(str(settings.qdrant_url), settings.health_check_timeout)
        print(f"   Status: {qdrant_result.status}")
        print(f"   Duration: {qdrant_result.duration_ms:.2f}ms")
        if qdrant_result.error:
            print(f"   Error: {qdrant_result.error}")
        print()
    except Exception as e:
        print(f"   ✗ Exception: {e}\n")
    
    print("4. Testing SearXNG Health Check...")
    try:
        searxng_result = await check_searxng(str(settings.searxng_url), settings.health_check_timeout)
        print(f"   Status: {searxng_result.status}")
        print(f"   Duration: {searxng_result.duration_ms:.2f}ms")
        if searxng_result.error:
            print(f"   Error: {searxng_result.error}")
        print()
    except Exception as e:
        print(f"   ✗ Exception: {e}\n")
    
    # Test the overall health check function
    from app.routers.health import perform_health_checks
    
    print("5. Testing Overall Health Check...")
    try:
        all_checks = await perform_health_checks(settings)
        print(f"   Services checked: {len(all_checks)}")
        for service, check in all_checks.items():
            symbol = "✓" if check.status == "healthy" else "✗"
            print(f"   {symbol} {service}: {check.status} ({check.duration_ms:.2f}ms)")
            if check.error:
                print(f"     Error: {check.error}")
        print()
    except Exception as e:
        print(f"   ✗ Exception: {e}\n")
    
    print("=" * 60)
    print("Health Check Tests Complete")
    print("=" * 60)
    print("\nAvailable routes in the application:")
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            methods = ', '.join(route.methods) if route.methods else 'N/A'
            print(f"  {methods:10} {route.path}")


if __name__ == "__main__":
    asyncio.run(test_health_checks())
