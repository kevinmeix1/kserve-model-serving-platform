# Event-Driven Assets

`make event-driven-assets` writes `.local/reports/event_driven_assets_plan.json`.

## What It Shows

- Airflow 3 event-driven scheduling for challenger model registration, KServe router readiness, and Gateway route convergence.
- `AssetWatcher` contracts for MLflow, Kubernetes InferenceService, and Gateway API HTTPRoute sources.
- `BaseEventTrigger` compatibility so serving rollouts do not accidentally reschedule in a loop.
- `shared_stream_key` planning so sibling watchers can share registry and Kubernetes watch streams.
- conditional asset expression: `(CHALLENGER & ROUTER & WEIGHTED_ROUTE) | ROLLBACK_REQUEST`.
- `AssetAlias` usage for runtime modelcar OCI and MLflow artifact URIs.
- Queued asset event inspection and deletion steps for stale route or registry events.

## Production Notes

The serving platform should not increase traffic from a model event alone. A challenger registration, a ready KServe router, and an accepted weighted route represent different control-plane truths. The rollout DAG only starts when those signals line up, while rollback stays available as an emergency override.

Watcher lag is treated as part of rollout reliability. A stale Kubernetes watch can be as dangerous as a slow predictor because it can promote a route based on old observedGeneration data.

## References

- Airflow event-driven scheduling: <https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/event-scheduling.html>
- Airflow asset-aware scheduling: <https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/asset-scheduling.html>
- Airflow asset definitions and AssetAlias: <https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/assets.html>
