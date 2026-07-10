from __future__ import annotations

import argparse
import importlib.metadata
import json
import re
from pathlib import Path


PROJECT_NAME = "kserve-model-serving-platform"


def canonical_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def read_lock(path: Path) -> dict[str, str]:
    locked: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "==" not in line:
            raise ValueError(f"lock entry is not exact: {line}")
        name, version = line.split("==", 1)
        key = canonical_name(name)
        if key in locked:
            raise ValueError(f"duplicate lock entry: {name}")
        locked[key] = version
    return locked


def audit_environment(path: Path) -> dict[str, object]:
    locked = read_lock(path)
    installed = {
        canonical_name(distribution.metadata["Name"]): distribution.version
        for distribution in importlib.metadata.distributions()
        if distribution.metadata["Name"]
    }
    installed.pop(canonical_name(PROJECT_NAME), None)

    missing = sorted(set(locked) - set(installed))
    unpinned = sorted(set(installed) - set(locked))
    mismatched = {
        name: {"locked": locked[name], "installed": installed[name]}
        for name in sorted(set(locked) & set(installed))
        if locked[name] != installed[name]
    }
    return {
        "passed": not missing and not unpinned and not mismatched,
        "locked_distributions": len(locked),
        "missing": missing,
        "unpinned": unpinned,
        "mismatched": mismatched,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify that the active environment exactly matches a flat lock"
    )
    parser.add_argument("lock", type=Path)
    args = parser.parse_args()
    report = audit_environment(args.lock)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
