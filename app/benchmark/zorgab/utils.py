from __future__ import annotations


def normalize_agb_target_id(target_id: str) -> str:
    if target_id.startswith("agb-z:"):
        return "agb:" + target_id.split("agb-z:", 1)[1]
    return target_id
