from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class Provider:
    name: str
    status: str = "NOT_CONFIGURED"
    capabilities: Dict[str, Any] | None = None


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: Dict[str, Provider] = {
            "ibkr": Provider(name="ibkr", status="NOT_CONFIGURED", capabilities={"supports_streaming": True, "supports_l2": True}),
            "alpaca": Provider(name="alpaca", status="NOT_CONFIGURED", capabilities={"supports_streaming": True, "supports_l2": False}),
            "polygon": Provider(name="polygon", status="NOT_CONFIGURED", capabilities={"supports_streaming": True, "supports_l2": False}),
            "finnhub": Provider(name="finnhub", status="NOT_CONFIGURED", capabilities={"supports_streaming": True, "supports_l2": False}),
            "alphavantage": Provider(name="alphavantage", status="NOT_CONFIGURED", capabilities={"supports_streaming": False, "supports_l2": False}),
            "finchat": Provider(name="finchat", status="NOT_CONFIGURED", capabilities={"supports_streaming": False, "supports_l2": False}),
            "upload": Provider(name="upload", status="READY", capabilities={"supports_streaming": False, "supports_l2": True}),
        }

    def list(self) -> List[Provider]:
        return list(self._providers.values())


provider_registry = ProviderRegistry()
