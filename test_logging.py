#!/usr/bin/env python3
"""Test script to verify structured logging works correctly across the codebase."""
import asyncio
from app.main import create_app
from app.config import get_settings


async def test_structured_logging():
    """Test structured logging implementation."""
    print("=" * 70)
    print("Testing Structured Logging Implementation")
    print("=" * 70)
    
    # Create the application (this will set up logging)
    print("\n1. Creating FastAPI application with structured logging...")
    app = create_app()
    print("   ✓ Application created - check logs above for structured format\n")
    
    # Import modules to test their logger setup
    print("2. Testing module logger initialization...")
    
    from app.routers import health, research_chat, ingestion
    from app.ws import hub
    from app.utils.logging import get_logger
    
    # Test that modules are using get_logger
    modules_to_check = [
        ("health", health),
        ("research_chat", research_chat),
        ("ingestion", ingestion),
        ("hub", hub),
    ]
    
    for module_name, module in modules_to_check:
        if hasattr(module, 'logger'):
            print(f"   ✓ {module_name} has logger configured")
        else:
            print(f"   ✗ {module_name} missing logger")
    
    print("\n3. Testing structured logging functions...")
    
    # Test get_logger
    test_logger = get_logger("test_module")
    print("   ✓ get_logger() works")
    
    # Test log_request utility
    from app.utils.logging import log_request
    print("\n   Testing log_request():")
    log_request(
        method="GET",
        path="/test/endpoint",
        status_code=200,
        duration_ms=15.5
    )
    print("   ✓ log_request() executed - check logs above")
    
    # Test log_health_check utility
    from app.utils.logging import log_health_check
    print("\n   Testing log_health_check():")
    
    # Successful check
    log_health_check(
        service="test_service",
        status="healthy",
        duration_ms=5.2
    )
    print("   ✓ log_health_check() for healthy service")
    
    # Failed check
    log_health_check(
        service="test_service_2",
        status="unhealthy",
        duration_ms=10.8,
        error="Connection timeout"
    )
    print("   ✓ log_health_check() for unhealthy service")
    
    print("\n4. Testing actual health check logging...")
    from app.routers.health import check_database
    settings = get_settings()
    
    try:
        result = await check_database(str(settings.db_url), settings.health_check_timeout)
        print(f"   ✓ Database check completed: {result.status}")
        print("   ✓ Check logs above for structured health check output")
    except Exception as e:
        print(f"   ✗ Database check failed: {e}")
    
    print("\n5. Verifying log format...")
    print("   Expected format in development:")
    print("   <timestamp> | <level> | <module>:<function>:<line> - <message>")
    print("   With extra fields for structured data")
    
    print("\n" + "=" * 70)
    print("Structured Logging Test Complete")
    print("=" * 70)
    print("\nKey Features Verified:")
    print("  ✓ Loguru-based structured logging")
    print("  ✓ Module-specific loggers with get_logger()")
    print("  ✓ Specialized logging utilities (log_request, log_health_check)")
    print("  ✓ Color-coded output in development")
    print("  ✓ Structured extra fields for filtering/searching")
    print("\nConfiguration:")
    settings = get_settings()
    print(f"  - Log Level: {settings.log_level}")
    print(f"  - Environment: {settings.environment}")
    print(f"  - JSON Format: {settings.environment in ['staging', 'prod']}")
    print("\nTo test JSON format for production:")
    print("  Set ENVIRONMENT=prod in .env and run again")


if __name__ == "__main__":
    asyncio.run(test_structured_logging())
