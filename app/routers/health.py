"""Health check endpoints for monitoring application and external services."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlmodel import Session, text

from ..config import Settings, get_settings
from ..db import engine
from ..utils.logging import get_logger, log_health_check

logger = get_logger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


class ServiceCheck(BaseModel):
    """Individual service check result."""

    status: str  # "healthy" or "unhealthy"
    duration_ms: float
    error: Optional[str] = None


class HealthStatus(BaseModel):
    """Health check response model."""

    status: str  # "healthy" or "unhealthy"
    timestamp: float
    version: str = "0.1.0"
    checks: dict[str, Any]


async def check_database(db_url: str, timeout: float) -> ServiceCheck:
    """
    Check database connectivity.

    Args:
        db_url: Database connection string (unused, uses global engine)
        timeout: Timeout in seconds

    Returns:
        ServiceCheck with database status
    """
    start_time = time.time()

    try:
        # Attempt to connect and execute simple query
        def check_db() -> bool:
            with Session(engine) as session:
                # Use connection-level execute for raw SQL
                session.connection().execute(text("SELECT 1"))
                return True

        await asyncio.wait_for(asyncio.to_thread(check_db), timeout=timeout)

        duration_ms = (time.time() - start_time) * 1000
        log_health_check(service="database", status="healthy", duration_ms=duration_ms)

        return ServiceCheck(status="healthy", duration_ms=duration_ms)

    except asyncio.TimeoutError:
        duration_ms = (time.time() - start_time) * 1000
        error = f"Database connection timeout after {timeout}s"
        log_health_check(
            service="database", status="unhealthy", duration_ms=duration_ms, error=error
        )

        return ServiceCheck(status="unhealthy", duration_ms=duration_ms, error=error)

    except Exception as e:  # noqa: BLE001
        duration_ms = (time.time() - start_time) * 1000
        error = f"Database connection failed: {str(e)}"
        log_health_check(
            service="database", status="unhealthy", duration_ms=duration_ms, error=error
        )

        return ServiceCheck(status="unhealthy", duration_ms=duration_ms, error=error)


async def check_qdrant(qdrant_url: str, timeout: float) -> ServiceCheck:
    """
    Check Qdrant vector database connectivity.

    Args:
        qdrant_url: Qdrant server URL
        timeout: Timeout in seconds

    Returns:
        ServiceCheck with Qdrant status
    """
    start_time = time.time()

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"{qdrant_url}/health")
            response.raise_for_status()

        duration_ms = (time.time() - start_time) * 1000
        log_health_check(service="qdrant", status="healthy", duration_ms=duration_ms)

        return ServiceCheck(status="healthy", duration_ms=duration_ms)

    except asyncio.TimeoutError:
        duration_ms = (time.time() - start_time) * 1000
        error = f"Qdrant connection timeout ({qdrant_url})"
        log_health_check(
            service="qdrant", status="unhealthy", duration_ms=duration_ms, error=error
        )

        return ServiceCheck(status="unhealthy", duration_ms=duration_ms, error=error)

    except Exception as e:  # noqa: BLE001
        duration_ms = (time.time() - start_time) * 1000
        error = f"Qdrant connection failed: {str(e)}"
        log_health_check(
            service="qdrant", status="unhealthy", duration_ms=duration_ms, error=error
        )

        return ServiceCheck(status="unhealthy", duration_ms=duration_ms, error=error)


async def check_searxng(searxng_url: str, timeout: float) -> ServiceCheck:
    """
    Check SearXNG web search service connectivity.

    Args:
        searxng_url: SearXNG server URL
        timeout: Timeout in seconds

    Returns:
        ServiceCheck with SearXNG status
    """
    start_time = time.time()

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            # SearXNG doesn't have a dedicated health endpoint, so we check the homepage
            response = await client.get(searxng_url)
            response.raise_for_status()

        duration_ms = (time.time() - start_time) * 1000
        log_health_check(service="searxng", status="healthy", duration_ms=duration_ms)

        return ServiceCheck(status="healthy", duration_ms=duration_ms)

    except asyncio.TimeoutError:
        duration_ms = (time.time() - start_time) * 1000
        error = f"SearXNG connection timeout ({searxng_url})"
        log_health_check(
            service="searxng", status="unhealthy", duration_ms=duration_ms, error=error
        )

        return ServiceCheck(status="unhealthy", duration_ms=duration_ms, error=error)

    except Exception as e:  # noqa: BLE001
        duration_ms = (time.time() - start_time) * 1000
        error = f"SearXNG connection failed: {str(e)}"
        log_health_check(
            service="searxng", status="unhealthy", duration_ms=duration_ms, error=error
        )

        return ServiceCheck(status="unhealthy", duration_ms=duration_ms, error=error)


async def perform_health_checks(settings: Settings) -> dict[str, ServiceCheck]:
    """
    Perform all configured health checks concurrently.

    Args:
        settings: Application settings

    Returns:
        Dictionary of service names to their check results
    """
    checks: dict[str, ServiceCheck] = {}
    tasks = []

    # Always check database (required service)
    tasks.append(
        ("database", check_database(settings.db_url, settings.health_check_timeout))
    )

    # Check Qdrant if configured
    if settings.qdrant_url and settings.qdrant_url != "http://localhost:6333":
        tasks.append(
            ("qdrant", check_qdrant(settings.qdrant_url, settings.health_check_timeout))
        )

    # Check SearXNG if configured
    if settings.searxng_url and settings.searxng_url != "http://localhost:8080":
        tasks.append(
            (
                "searxng",
                check_searxng(settings.searxng_url, settings.health_check_timeout),
            )
        )

    # Run all checks concurrently
    if tasks:
        results = await asyncio.gather(
            *[task[1] for task in tasks], return_exceptions=True
        )

        for i, (service_name, _) in enumerate(tasks):
            result = results[i]
            if isinstance(result, ServiceCheck):
                checks[service_name] = result
            elif isinstance(result, Exception):
                # Handle unexpected exceptions
                checks[service_name] = ServiceCheck(
                    status="unhealthy",
                    duration_ms=0,
                    error=f"Unexpected error: {str(result)}",
                )
            else:
                # Unexpected result type
                checks[service_name] = ServiceCheck(
                    status="unhealthy", duration_ms=0, error="Unexpected result type"
                )

    return checks


@router.get("/", response_model=HealthStatus)
async def health_check(settings: Settings = Depends(get_settings)):
    """
    Comprehensive health check endpoint.

    Checks all configured external services and returns overall health status.
    Returns 503 if any service is unhealthy.

    Returns:
        HealthStatus with overall status and individual service checks
    """
    timestamp = time.time()

    # Perform all health checks
    checks = await perform_health_checks(settings)

    # Determine overall status
    overall_status = "healthy"
    if checks:
        # If any check is unhealthy, overall status is unhealthy
        if any(check.status == "unhealthy" for check in checks.values()):
            overall_status = "unhealthy"

    # Create response
    health_status = HealthStatus(
        status=overall_status,
        timestamp=timestamp,
        checks={name: check.model_dump() for name, check in checks.items()},
    )

    # Log overall health check result
    logger.info(
        "Health check completed: %s",
        overall_status,
        extra={
            "overall_status": overall_status,
            "services_checked": len(checks),
            "timestamp": timestamp,
        },
    )

    # Return appropriate HTTP status
    if overall_status == "unhealthy":
        raise HTTPException(status_code=503, detail=health_status.model_dump())

    return health_status


@router.get("/live")
async def liveness_check():
    """
    Simple liveness check - confirms the application process is running.

    This is useful for Kubernetes liveness probes.
    Returns 200 if the process is alive.
    """
    return {"status": "alive", "timestamp": time.time()}


@router.get("/ready")
async def readiness_check(settings: Settings = Depends(get_settings)):
    """
    Readiness check - confirms the app can serve requests.

    This is useful for Kubernetes readiness probes.
    Checks critical services (database) and returns 503 if they're unhealthy.
    """
    checks = await perform_health_checks(settings)

    # Define critical services that must be healthy for readiness
    critical_services = ["database"]

    is_ready = True
    for service_name, check in checks.items():
        if service_name in critical_services and check.status == "unhealthy":
            logger.info(
                "Critical service %s is unhealthy: %s", service_name, check.status
            )
            is_ready = False
            break

    status_code = 200 if is_ready else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if is_ready else "not_ready",
            "timestamp": time.time(),
            "checks": {name: check.model_dump() for name, check in checks.items()},
        },
    )
