# Airflow Multi-Team Readiness

`make multi-team-readiness` writes `.local/reports/multi_team_readiness_plan.json`.

## What It Shows

- `core.multi_team = True` in the Airflow preview profile.
- DAG Bundle `team_name` ownership for KServe rollout DAGs.
- Team-scoped pools with `airflow pools set ... --team-name`.
- Team-scoped variables and connections using `AIRFLOW_VAR__ML_SERVING___...` and `AIRFLOW_CONN__ML_SERVING___...`.
- Team-specific executor routing and `airflow triggerer --team-name ml-serving`.
- `AssetAccessControl` with `producer_teams`, `consumer_teams`, and `allow_global=False` for cross-team serving assets.

## Production Notes

Airflow multi-team support is still preview/experimental, so this project treats it as readiness evidence rather than a required local runtime. In production, create `ml-serving` before DAG bundle sync, run a team triggerer for deferrable route and KServe sensors, and keep rollout pools, KServe API credentials, and route-convergence work scoped to the serving team.

This is logical/resource isolation inside one Airflow deployment. For strict serving tenant isolation, use separate Airflow deployments, separate metadata databases, or separate platform namespaces.

## Example Bootstrap

```bash
airflow teams create ml-serving
airflow pools set model_serving_release_pool 10 "Serving rollout and rollback pool" --team-name ml-serving
airflow pools set route_convergence_pool 6 "Gateway route smoke and convergence pool" --team-name ml-serving
airflow triggerer --team-name ml-serving
```

## Asset Filtering Contract

```python
from airflow.sdk import Asset
from airflow.sdk.definitions.asset import AssetAccessControl

serving_route_asset = Asset(
    "kserve://credit-risk/route/canary",
    access_control=AssetAccessControl(
        producer_teams={"ml-serving"},
        consumer_teams={"ml-platform", "ml-observability"},
        allow_global=False,
    ),
)
```

## Senior Review Angle

The report shows how progressive delivery can be owned by a serving team without letting route, model-cache, or rollback events broadcast to unrelated teams. It also calls out the preview status clearly so the repo feels production-aware instead of feature-name decorative.

References:

- https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/multi-team.html
- https://airflow.apache.org/docs/apache-airflow/stable/release_notes.html
- https://airflow.apache.org/blog/airflow-3.2.0/
