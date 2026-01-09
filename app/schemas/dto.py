from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class DTO(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceOut(DTO):
    id: UUID
    filename: str
    content_type: str
    path: str
    tags: list[str]
    created_at: datetime
    notes: Optional[str] = None


class HypothesisOut(DTO):
    id: UUID
    name: str
    status: str
    mechanism: str
    falsifiable_prediction: str
    null_hypothesis: str
    decision_timing: str
    horizons_ms: list[int]
    primary_metrics: list[str]
    acceptance_criteria: list[dict]
    tradability_constraints: str
    failure_modes: list[str]
    tags: list[str]
    source_refs: list[dict]
    created_at: datetime
    created_by: str
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None


class HypothesisCreate(DTO):
    name: str
    mechanism: str
    falsifiable_prediction: str
    null_hypothesis: str
    decision_timing: str = "on_trade_event"
    horizons_ms: list[int] = Field(default_factory=list)
    primary_metrics: list[str] = Field(default_factory=list)
    acceptance_criteria: list[dict] = Field(default_factory=list)
    tradability_constraints: str = ""
    failure_modes: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    source_refs: list[dict] = Field(default_factory=list)


class HypothesisApprove(DTO):
    approved_by: str = "local-user"


class ManifestOut(DTO):
    id: UUID
    hypothesis_id: UUID
    name: str
    manifest_json: dict
    locked: bool
    lock_reason: Optional[str] = None
    created_at: datetime
    created_by: str
    locked_at: Optional[datetime] = None
    locked_by: Optional[str] = None


class ManifestCreate(DTO):
    hypothesis_id: UUID
    name: str
    manifest_json: dict = Field(default_factory=dict)


class ManifestLock(DTO):
    locked_by: str = "local-user"
    reason: str = "preregistered"


class RunOut(DTO):
    id: UUID
    hypothesis_id: UUID
    manifest_id: UUID
    status: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    metrics: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    artifacts_dir: str


class RunCreate(DTO):
    manifest_id: UUID


class CodePatchOut(DTO):
    id: UUID
    path: str
    content: str
    metadata: dict
    status: str
    created_at: datetime
    created_by: str


class CodePatchCreate(DTO):
    path: str
    content: str
    metadata: dict = Field(default_factory=dict)


class CodePatchApply(DTO):
    approved_by: str = "local-user"


class StrategyOut(DTO):
    id: UUID
    name: str
    run_id: UUID
    manifest_id: UUID
    hypothesis_id: UUID
    version: str
    readiness: str
    parameters: dict
    monitoring_spec: dict
    created_at: datetime
    created_by: str
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None


class StrategyCreate(DTO):
    name: str
    run_id: UUID
    manifest_id: UUID
    hypothesis_id: UUID
    version: str = "0.1.0"
    parameters: dict = Field(default_factory=dict)
    monitoring_spec: dict = Field(default_factory=dict)


class StrategyApprove(DTO):
    approved_by: str = "local-user"


class LiveInstanceOut(DTO):
    id: UUID
    strategy_id: UUID
    mode: str
    status: str
    created_at: datetime
    stopped_at: Optional[datetime] = None
    stats: dict = Field(default_factory=dict)


class LiveStart(DTO):
    strategy_id: UUID
    mode: str = "SHADOW"  # SHADOW/PAPER


class ProviderOut(DTO):
    name: str
    status: str
    capabilities: dict = Field(default_factory=dict)
