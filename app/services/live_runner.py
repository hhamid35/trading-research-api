from __future__ import annotations

import asyncio
from datetime import datetime
from uuid import UUID

from sqlmodel import Session

from ..models import LiveInstance
from ..ws.hub import hub


async def simulate_live(session: Session, instance_id: UUID) -> None:
    inst = session.get(LiveInstance, instance_id)
    if not inst:
        return

    ch = await hub.get(f"live:{instance_id}")
    inst.status = "RUNNING"
    inst.last_heartbeat_at = datetime.utcnow()
    session.add(inst)
    session.commit()

    await ch.publish({"ts": datetime.utcnow().isoformat(), "level": "INFO", "msg": f"{inst.mode} started"})

    for i in range(40):
        await asyncio.sleep(0.25)
        inst.last_heartbeat_at = datetime.utcnow()
        inst.stats = {
            "heartbeat": i,
            "mode": inst.mode,
            "sim_fill_rate": 0.62,
            "sim_slippage_ticks": 0.7,
        }
        session.add(inst)
        session.commit()
        await ch.publish({"ts": datetime.utcnow().isoformat(), "level": "INFO", "msg": "heartbeat", "stats": inst.stats})

    inst.status = "STOPPED"
    inst.stopped_at = datetime.utcnow()
    session.add(inst)
    session.commit()
    await ch.publish({"ts": datetime.utcnow().isoformat(), "level": "INFO", "msg": "stopped"})
