from __future__ import annotations

from datetime import datetime
from typing import List
from uuid import UUID

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
from sqlmodel import Session

from ..db import engine
from ..models import ManifestDraft, ExperimentManifest, HypothesisCard
from ..settings import settings


class ManifestPayload(BaseModel):
    hypothesis_id: str
    name: str
    manifest_json: dict = Field(default_factory=dict)


def create_manifest_draft(hypothesis_id: UUID) -> ManifestDraft:
    with Session(engine) as session:
        hypothesis = session.get(HypothesisCard, hypothesis_id)
        if not hypothesis or hypothesis.status != "APPROVED":
            raise RuntimeError("Hypothesis must be approved")

    model = ChatOpenAI(model=settings.llm_openai_model, api_key=settings.openai_api_key)
    structured = model.with_structured_output(ManifestPayload)
    prompt = "Draft an experiment manifest with dataset, features, labels, execution, and evaluation blocks."

    output = structured.invoke(
        [
            SystemMessage(content=prompt),
            HumanMessage(content=f"Hypothesis: {hypothesis.name}\n{hypothesis.falsifiable_prediction}"),
        ]
    )
    payload = output.model_dump()

    draft = ManifestDraft(
        hypothesis_id=hypothesis_id,
        status="PROPOSED",
        payload_json=payload,
        validation_report_json={},
        thread_id=f"manifest:{hypothesis_id}",
        created_by="local-user",
        created_at=datetime.utcnow(),
    )
    with Session(engine) as session:
        session.add(draft)
        session.commit()
        session.refresh(draft)
    return draft


def validate_manifest_draft(draft_id: UUID) -> ManifestDraft:
    with Session(engine) as session:
        draft = session.get(ManifestDraft, draft_id)
        if not draft:
            raise RuntimeError("Draft not found")
        payload = draft.payload_json or {}
        manifest = payload.get("manifest_json", {})

        report = {
            "data_availability": "dataset" in manifest,
            "feature_label_alignment": "features" in manifest and "labels" in manifest,
            "cost_model": "execution" in manifest,
            "split_plan": "evaluation" in manifest,
        }
        if all(report.values()):
            draft.status = "READY_TO_LOCK"
        else:
            draft.status = "FAILED_VALIDATION"
        draft.validation_report_json = report
        draft.updated_at = datetime.utcnow()
        session.add(draft)
        session.commit()
        session.refresh(draft)
        return draft


def lock_manifest_draft(draft_id: UUID) -> ExperimentManifest:
    with Session(engine) as session:
        draft = session.get(ManifestDraft, draft_id)
        if not draft:
            raise RuntimeError("Draft not found")
        if draft.status != "READY_TO_LOCK":
            raise RuntimeError("Draft must be READY_TO_LOCK")
        payload = draft.payload_json or {}
        manifest = ExperimentManifest(
            hypothesis_id=draft.hypothesis_id,
            name=payload.get("name") or f"Manifest {draft.id}",
            manifest_json=payload.get("manifest_json") or {},
            locked=True,
            lock_reason="preregistered",
            locked_at=datetime.utcnow(),
            locked_by=draft.created_by,
        )
        session.add(manifest)
        draft.status = "LOCKED"
        draft.updated_at = datetime.utcnow()
        session.add(draft)
        session.commit()
        session.refresh(manifest)
        return manifest
