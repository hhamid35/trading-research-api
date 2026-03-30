from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DTO(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class ResearchChatSessionCreate(DTO):
    title: Optional[str] = None


class ResearchChatSessionOut(DTO):
    id: UUID
    title: str
    created_by: str
    created_at: datetime
    state_json: dict = Field(default_factory=dict)


class ResearchChatMessageCreate(DTO):
    content: str


class ResearchChatMessageOut(DTO):
    id: UUID
    session_id: UUID
    role: str
    content: str
    tool_name: Optional[str] = None
    tool_payload_json: Optional[dict] = None
    created_at: datetime


class IngestionJobCreate(DTO):
    source_id: UUID
    config: dict = Field(default_factory=dict)


class IngestionJobOut(DTO):
    id: UUID
    source_id: UUID
    status: str
    attempts: int
    last_error: Optional[str] = None
    thread_id: str
    config_json: dict = Field(default_factory=dict)
    stats_json: dict = Field(default_factory=dict)
    created_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None


class SearchResultOut(DTO):
    title: str
    url: str
    snippet: str


class RetrievalHitOut(DTO):
    score: float
    chunk_id: str
    source_id: str
    document_id: str
    text: str
    char_start: int
    char_end: int


class HypothesisDraftCreate(DTO):
    session_id: UUID
    constraints: dict = Field(default_factory=dict)


class HypothesisDraftOut(DTO):
    id: UUID
    session_id: UUID
    status: str
    payload_json: dict
    citations_json: list[dict]
    rationale_json: dict
    thread_id: str
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class ManifestDraftCreate(DTO):
    hypothesis_id: UUID
    preferences: dict = Field(default_factory=dict)


class ManifestDraftOut(DTO):
    id: UUID
    hypothesis_id: UUID
    status: str
    payload_json: dict
    validation_report_json: dict
    thread_id: str
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None


# -------------------------
# Source schemas
# -------------------------


class SourceCreate(DTO):
    kind: str = "UPLOAD"
    title: str = ""
    filename: str = ""
    uri: str = ""
    content_type: str = "application/octet-stream"
    notes: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    metadata_: dict = Field(default_factory=dict, alias="metadata")


class SourceOut(DTO):
    id: UUID
    kind: str
    title: str
    filename: str
    uri: str
    content_type: str
    checksum_sha256: str
    bytes: int
    storage_path: str
    notes: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    metadata_: dict = Field(default_factory=dict, alias="metadata")
    created_at: datetime
    created_by: str


# -------------------------
# Hypothesis card schemas
# -------------------------


class HypothesisCardCreate(DTO):
    name: str
    mechanism: str
    falsifiable_prediction: str
    null_hypothesis: str = "No conditional edge after costs."
    decision_timing: str = "on_trade_event"
    horizons_ms: list[int] = Field(default_factory=list)
    primary_metrics: list[str] = Field(default_factory=list)
    acceptance_criteria: list[dict] = Field(default_factory=list)
    tradability_constraints: str = ""
    failure_modes: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class HypothesisCardOut(DTO):
    id: UUID
    name: str
    status: str
    mechanism: str
    falsifiable_prediction: str
    null_hypothesis: str
    decision_timing: str
    horizons_ms: list[int] = Field(default_factory=list)
    primary_metrics: list[str] = Field(default_factory=list)
    acceptance_criteria: list[dict] = Field(default_factory=list)
    tradability_constraints: str
    failure_modes: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    created_by: str
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None


# -------------------------
# Experiment manifest schemas
# -------------------------


class ExperimentManifestCreate(DTO):
    hypothesis_id: UUID
    name: str
    manifest_json: dict = Field(default_factory=dict)


class ExperimentManifestOut(DTO):
    id: UUID
    hypothesis_id: UUID
    name: str
    manifest_json: dict = Field(default_factory=dict)
    locked: bool
    lock_reason: Optional[str] = None
    created_at: datetime
    created_by: str
    locked_at: Optional[datetime] = None
    locked_by: Optional[str] = None


# -------------------------
# Run schemas
# -------------------------


class RunCreate(DTO):
    manifest_id: UUID
    hypothesis_id: UUID


class RunOut(DTO):
    id: UUID
    hypothesis_id: UUID
    manifest_id: UUID
    status: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    summary_metrics: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    artifacts_dir: str


class RunArtifactOut(DTO):
    id: UUID
    run_id: UUID
    kind: str
    name: str
    media_type: str
    storage_path: str
    json_payload: dict = Field(default_factory=dict)
    created_at: datetime


# -------------------------
# Strategy schemas
# -------------------------


class StrategyPackageCreate(DTO):
    name: str
    run_id: UUID
    manifest_id: UUID
    hypothesis_id: UUID
    version: str = "0.1.0"
    parameters: dict = Field(default_factory=dict)
    monitoring_spec: dict = Field(default_factory=dict)


class StrategyPackageOut(DTO):
    id: UUID
    name: str
    run_id: UUID
    manifest_id: UUID
    hypothesis_id: UUID
    version: str
    readiness: str
    code_version: str
    parameters: dict = Field(default_factory=dict)
    monitoring_spec: dict = Field(default_factory=dict)
    package_path: str
    created_at: datetime
    created_by: str
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None


# -------------------------
# Live instance schemas
# -------------------------


class LiveInstanceCreate(DTO):
    strategy_id: UUID
    mode: str = "SHADOW"


class LiveInstanceOut(DTO):
    id: UUID
    strategy_id: UUID
    mode: str
    status: str
    created_at: datetime
    stopped_at: Optional[datetime] = None
    last_heartbeat_at: Optional[datetime] = None
    stats: dict = Field(default_factory=dict)


# -------------------------
# Provider schemas
# -------------------------


class ProviderOut(DTO):
    name: str
    kind: str
    status: str
    base_url: str
    capabilities: dict = Field(default_factory=dict)


# -------------------------
# Dashboard schemas
# -------------------------


class DashboardStatsOut(DTO):
    sources_count: int = 0
    hypotheses_count: int = 0
    manifests_count: int = 0
    runs_count: int = 0
    strategies_count: int = 0
    live_instances_count: int = 0
    recent_runs: list[RunOut] = Field(default_factory=list)
