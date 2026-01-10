from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import relationship
from sqlmodel import SQLModel, Field, Relationship, Column, JSON


def utcnow() -> datetime:
    return datetime.utcnow()


# -------------------------
# Core registry tables
# -------------------------

class Source(SQLModel, table=True):
    """Research input: uploaded file, URL, pasted text, note, or derived artifact."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    kind: str = Field(default="UPLOAD", index=True)  # UPLOAD|URL|TEXT|NOTE|DERIVED
    title: str = Field(default="", index=True)
    filename: str = Field(default="", index=True)
    uri: str = Field(default="", index=True)

    content_type: str = "application/octet-stream"
    checksum_sha256: str = ""
    bytes: int = 0

    storage_path: str = ""
    notes: Optional[str] = None

    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    metadata_: dict = Field(default_factory=dict, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=utcnow)
    created_by: str = "local-user"

    hypothesis_links: list["HypothesisSourceLink"] = Relationship(
        sa_relationship=relationship("HypothesisSourceLink", back_populates="source")
    )


class HypothesisCard(SQLModel, table=True):
    """Falsifiable preregistered hypothesis card."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    name: str = Field(index=True)
    status: str = Field(default="DRAFT", index=True)  # DRAFT|APPROVED|REJECTED|ARCHIVED

    mechanism: str
    falsifiable_prediction: str
    null_hypothesis: str = "No conditional edge after costs."

    decision_timing: str = "on_trade_event"
    horizons_ms: list[int] = Field(default_factory=list, sa_column=Column(JSON))
    primary_metrics: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    acceptance_criteria: list[dict] = Field(default_factory=list, sa_column=Column(JSON))

    tradability_constraints: str = ""
    failure_modes: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=utcnow)
    created_by: str = "local-user"
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None

    sources: list["HypothesisSourceLink"] = Relationship(
        sa_relationship=relationship("HypothesisSourceLink", back_populates="hypothesis")
    )
    manifests: list["ExperimentManifest"] = Relationship(
        sa_relationship=relationship("ExperimentManifest", back_populates="hypothesis")
    )
    runs: list["Run"] = Relationship(
        sa_relationship=relationship("Run", back_populates="hypothesis")
    )
    strategies: list["StrategyPackage"] = Relationship(
        sa_relationship=relationship("StrategyPackage", back_populates="hypothesis")
    )


class HypothesisSourceLink(SQLModel, table=True):
    """Many-to-many link between HypothesisCard and Source, with citation metadata_."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    hypothesis_id: UUID = Field(foreign_key="hypothesiscard.id", index=True)
    source_id: UUID = Field(foreign_key="source.id", index=True)

    citation: dict = Field(default_factory=dict, sa_column=Column(JSON))
    relevance_note: str = ""

    created_at: datetime = Field(default_factory=utcnow)
    created_by: str = "local-user"

    hypothesis: HypothesisCard = Relationship(
        sa_relationship=relationship("HypothesisCard", back_populates="sources")
    )
    source: Source = Relationship(
        sa_relationship=relationship("Source", back_populates="hypothesis_links")
    )


class ExperimentManifest(SQLModel, table=True):
    """Preregistered experiment configuration. Must be locked before a run."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    hypothesis_id: UUID = Field(foreign_key="hypothesiscard.id", index=True)
    name: str = Field(index=True)

    manifest_json: dict = Field(default_factory=dict, sa_column=Column(JSON))

    locked: bool = Field(default=False, index=True)
    lock_reason: Optional[str] = None

    created_at: datetime = Field(default_factory=utcnow)
    created_by: str = "local-user"
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    locked_at: Optional[datetime] = None
    locked_by: Optional[str] = None

    hypothesis: HypothesisCard = Relationship(
        sa_relationship=relationship("HypothesisCard", back_populates="manifests")
    )
    runs: list["Run"] = Relationship(
        sa_relationship=relationship("Run", back_populates="manifest")
    )


class Run(SQLModel, table=True):
    """Execution of a locked ExperimentManifest."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    hypothesis_id: UUID = Field(foreign_key="hypothesiscard.id", index=True)
    manifest_id: UUID = Field(foreign_key="experimentmanifest.id", index=True)

    status: str = Field(default="QUEUED", index=True)  # QUEUED|RUNNING|FAILED|SUCCEEDED|CANCELED
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    code_version: str = "git:unknown"
    dataset_hash: str = ""
    feature_hash: str = ""
    label_hash: str = ""
    model_hash: str = ""
    execution_hash: str = ""

    summary_metrics: dict = Field(default_factory=dict, sa_column=Column(JSON))
    warnings: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    artifacts_dir: str = ""
    logs_path: Optional[str] = None

    hypothesis: HypothesisCard = Relationship(
        sa_relationship=relationship("HypothesisCard", back_populates="runs")
    )
    manifest: ExperimentManifest = Relationship(
        sa_relationship=relationship("ExperimentManifest", back_populates="runs")
    )
    artifacts: list["RunArtifact"] = Relationship(
        sa_relationship=relationship("RunArtifact", back_populates="run")
    )
    events: list["RunEvent"] = Relationship(
        sa_relationship=relationship("RunEvent", back_populates="run")
    )


class RunArtifact(SQLModel, table=True):
    """Artifact produced by a run (metrics, plots, reports, models, files)."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    run_id: UUID = Field(foreign_key="run.id", index=True)
    kind: str = Field(default="METRICS", index=True)  # METRICS|PLOT|REPORT|MODEL|FILE|TABLE
    name: str = Field(default="", index=True)

    media_type: str = "application/json"
    storage_path: str = ""
    json_payload: dict = Field(default_factory=dict, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=utcnow)

    run: Run = Relationship(
        sa_relationship=relationship("Run", back_populates="artifacts")
    )


class RunEvent(SQLModel, table=True):
    """Persisted event log for a run (optional but useful for auditability)."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    run_id: UUID = Field(foreign_key="run.id", index=True)
    ts: datetime = Field(default_factory=utcnow, index=True)
    level: str = Field(default="INFO", index=True)
    msg: str
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON))

    run: Run = Relationship(
        sa_relationship=relationship("Run", back_populates="events")
    )


class StrategyPackage(SQLModel, table=True):
    """Deployable strategy package derived from a succeeded run."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    name: str = Field(index=True)

    run_id: UUID = Field(foreign_key="run.id", index=True)
    manifest_id: UUID = Field(foreign_key="experimentmanifest.id", index=True)
    hypothesis_id: UUID = Field(foreign_key="hypothesiscard.id", index=True)

    version: str = "0.1.0"
    readiness: str = Field(default="DRAFT", index=True)  # DRAFT|APPROVED_FOR_SHADOW|APPROVED_FOR_PAPER|APPROVED_FOR_LIVE|RETIRED

    code_version: str = "git:unknown"
    parameters: dict = Field(default_factory=dict, sa_column=Column(JSON))
    monitoring_spec: dict = Field(default_factory=dict, sa_column=Column(JSON))
    package_path: str = ""

    created_at: datetime = Field(default_factory=utcnow)
    created_by: str = "local-user"
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None

    hypothesis: HypothesisCard = Relationship(
        sa_relationship=relationship("HypothesisCard", back_populates="strategies")
    )


class LiveInstance(SQLModel, table=True):
    """Running instance of a StrategyPackage (shadow/paper/live)."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    strategy_id: UUID = Field(foreign_key="strategypackage.id", index=True)

    mode: str = Field(default="SHADOW", index=True)  # SHADOW|PAPER|LIVE
    status: str = Field(default="STARTING", index=True)  # STARTING|RUNNING|STOPPED|ERROR

    created_at: datetime = Field(default_factory=utcnow)
    stopped_at: Optional[datetime] = None
    last_heartbeat_at: Optional[datetime] = None

    stats: dict = Field(default_factory=dict, sa_column=Column(JSON))


# -------------------------
# MVP ingestion + RAG tables
# -------------------------


class IngestionJob(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    source_id: UUID = Field(foreign_key="source.id", index=True)

    status: str = Field(default="QUEUED", index=True)  # QUEUED|RUNNING|FAILED|SUCCEEDED
    attempts: int = 0
    last_error: Optional[str] = None
    thread_id: str = ""

    config_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    stats_json: dict = Field(default_factory=dict, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=utcnow, index=True)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None


class Document(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    source_id: UUID = Field(foreign_key="source.id", index=True)
    kind: str = Field(default="text", index=True)  # pdf_page|html|markdown|text
    title: str = ""
    uri: str = ""
    metadata_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow, index=True)


class DocumentChunk(SQLModel, table=True):
    id: UUID = Field(primary_key=True)  # deterministic
    document_id: UUID = Field(foreign_key="document.id", index=True)
    source_id: UUID = Field(foreign_key="source.id", index=True)
    chunk_index: int = Field(index=True)
    text: str
    char_start: int
    char_end: int
    token_count: int
    metadata_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow, index=True)


class ChunkEmbedding(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    chunk_id: UUID = Field(foreign_key="documentchunk.id", index=True)
    embedding_model: str = Field(index=True)
    vector_id: str = Field(index=True)
    dim: int
    checksum: str
    created_at: datetime = Field(default_factory=utcnow, index=True)


# -------------------------
# Research chat + drafts
# -------------------------


class ResearchChatSession(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = "New chat"
    created_by: str = "local-user"
    created_at: datetime = Field(default_factory=utcnow, index=True)
    state_json: dict = Field(default_factory=dict, sa_column=Column(JSON))


class ResearchChatMessage(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    session_id: UUID = Field(foreign_key="researchchatsession.id", index=True)
    role: str = Field(default="user", index=True)  # user|assistant|tool
    content: str
    tool_name: Optional[str] = None
    tool_payload_json: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow, index=True)


class HypothesisDraft(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    session_id: UUID = Field(foreign_key="researchchatsession.id", index=True)
    status: str = Field(default="PROPOSED", index=True)  # PROPOSED|REVISED|APPROVED|REJECTED
    payload_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    citations_json: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    rationale_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    thread_id: str = ""
    created_by: str = "local-user"
    created_at: datetime = Field(default_factory=utcnow, index=True)
    updated_at: Optional[datetime] = None


class ManifestDraft(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    hypothesis_id: UUID = Field(foreign_key="hypothesiscard.id", index=True)
    status: str = Field(default="PROPOSED", index=True)  # PROPOSED|FAILED_VALIDATION|READY_TO_LOCK|LOCKED
    payload_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    validation_report_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    thread_id: str = ""
    created_by: str = "local-user"
    created_at: datetime = Field(default_factory=utcnow, index=True)
    updated_at: Optional[datetime] = None
