from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .io import read_json, write_json
from .models import MODEL_CATALOG


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def registry_root(root: str | Path) -> Path:
    return Path(root) / "registry" / "credit-risk"


def seed_registry(root: str | Path) -> dict:
    base = registry_root(root)
    for version, model in MODEL_CATALOG.items():
        write_json(base / "versions" / version / "model.json", model)
        write_json(
            base / "versions" / version / "metadata.json",
            {
                "name": "credit-risk",
                "version": version,
                "stage": model["stage"],
                "signature": {
                    "inputs": ["product", "income", "debt_ratio", "delinquencies", "utilization", "employment_years"],
                    "outputs": ["risk_score", "risk_band"],
                },
                "registered_at": utc_iso(),
            },
        )
    aliases = {
        "champion": "risk-model-2026-07-01",
        "challenger": "risk-model-2026-07-15",
        "previous_champion": None,
        "updated_at": utc_iso(),
    }
    write_json(base / "aliases.json", aliases)
    return aliases


def aliases(root: str | Path) -> dict:
    path = registry_root(root) / "aliases.json"
    if not path.exists():
        return seed_registry(root)
    return read_json(path)


def model_by_alias(root: str | Path, alias: str) -> dict:
    model_version = aliases(root).get(alias)
    if not model_version:
        raise FileNotFoundError(f"registry alias does not exist: {alias}")
    return read_json(registry_root(root) / "versions" / model_version / "model.json")


def promote_challenger(root: str | Path) -> dict:
    current = aliases(root)
    if not current.get("challenger"):
        return {"promoted": False, "reason": "no_challenger"}
    previous = current["champion"]
    current["previous_champion"] = previous
    current["champion"] = current["challenger"]
    current["challenger"] = None
    current["updated_at"] = utc_iso()
    write_json(registry_root(root) / "aliases.json", current)
    return {"promoted": True, "champion": current["champion"], "previous_champion": previous}


def rollback(root: str | Path) -> dict:
    current = aliases(root)
    previous = current.get("previous_champion")
    if not previous:
        return {"rolled_back": False, "reason": "no_previous_champion"}
    old_champion = current["champion"]
    current["champion"] = previous
    current["challenger"] = old_champion
    current["previous_champion"] = None
    current["updated_at"] = utc_iso()
    write_json(registry_root(root) / "aliases.json", current)
    return {"rolled_back": True, "champion": current["champion"], "challenger": current["challenger"]}
