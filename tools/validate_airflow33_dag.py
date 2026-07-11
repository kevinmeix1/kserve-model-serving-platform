from __future__ import annotations

import argparse
import json
import runpy
from pathlib import Path

from airflow.sdk import DAG


def validate(path: Path) -> dict[str, object]:
    namespace = runpy.run_path(str(path))
    expected = set(namespace.get("AIRFLOW_33_DAG_IDS", ()))
    dags = {
        value.dag_id: value for value in namespace.values() if isinstance(value, DAG)
    }
    missing = sorted(expected - dags.keys())
    if missing:
        raise RuntimeError(f"Expected DAGs were not registered: {missing}")
    if not expected:
        raise RuntimeError("DAG module must declare AIRFLOW_33_DAG_IDS")

    task_counts: dict[str, int] = {}
    for dag_id in sorted(expected):
        dag = dags[dag_id]
        dag.validate()
        task_counts[dag_id] = len(dag.task_dict)
        if task_counts[dag_id] == 0:
            raise RuntimeError(f"DAG {dag_id!r} has no tasks")

    return {
        "airflow_contract": "3.3.0",
        "module": str(path),
        "dag_ids": sorted(expected),
        "task_counts": task_counts,
        "status": "passed",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Parse and validate an Airflow 3.3 DAG module"
    )
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate(args.path.resolve()), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
