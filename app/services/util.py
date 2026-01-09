from __future__ import annotations

import hashlib
import json
from typing import Any


def stable_json_hash(obj: Any) -> str:
    s = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(s).hexdigest()
