from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field, Column, JSON


def utcnow() -> datetime:
    return datetime.utcnow()


class Source(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    filename: str
    content_type: str = "application/octet-stream"
    path: str
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)
    notes: Optional[str] = None


class Hypothesis(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    status: str = "DRAFT"
    mechanism: str
    falsifiable_prediction: str
    null_hypothesis: str
    decision_timing: str = "on_trade_event"
    horizons_ms: list[int] = Field(default_factory=list, sa_column=Column(JSON))
    primary_metrics: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    acceptance_criteria: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    tradability_constraints: str = ""
    failure_modes: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    source_refs: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)
    created_by: str = "local-user"
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None


class Manifest(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    hypothesis_id: UUID
    name: str
    manifest_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    locked: bool = False
    lock_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)
    created_by: str = "local-user"
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    locked_at: Optional[datetime] = None
    locked_by: Optional[str] = None


class Run(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    hypothesis_id: UUID
    manifest_id: UUID
    status: str = "QUEUED"
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    code_version: str = "git:unknown"
    dataset_hash: str = ""
    feature_hash: str = ""
    label_hash: str = ""
    model_hash: str = ""
    execution_hash: str = ""

    metrics: dict = Field(default_factory=dict, sa_column=Column(JSON))
    plots: dict = Field(default_factory=dict, sa_column=Column(JSON))
    warnings: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    logs_path: Optional[str] = None
    artifacts_dir: str = ""


class CodePatch(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    path: str
    content: str
    metadata: dict = Field(default_factory=dict, sa_column=Column(JSON))
    status: str = "PROPOSED"  # PROPOSED/APPLIED/REJECTED
    created_at: datetime = Field(default_factory=utcnow)
    created_by: str = "agent"
    applied_at: Optional[datetime] = None
    applied_by: Optional[str] = None


class Strategy(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    run_id: UUID
    manifest_id: UUID
    hypothesis_id: UUID
    version: str = "0.1.0"
    code_version: str = "git:unknown"
    parameters: dict = Field(default_factory=dict, sa_column=Column(JSON))
    readiness: str = "DRAFT"
    monitoring_spec: dict = Field(default_factory=dict, sa_column=Column(JSON))
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)
    created_by: str = "local-user"


class LiveInstance(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    strategy_id: UUID
    mode: str = "SHADOW"  # SHADOW/PAPER
    status: str = "STARTING"  # STARTING/RUNNING/STOPPED/ERROR
    created_at: datetime = Field(default_factory=utcnow)
    stopped_at: Optional[datetime] = None
    last_heartbeat_at: Optional[datetime] = None
    stats: dict = Field(default_factory=dict, sa_column=Column(JSON))
