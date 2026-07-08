# Kueue Cohort Fair Sharing

`make cohort-fair-sharing` writes `.local/reports/cohort_fair_sharing_plan.json` and pairs it with `kubernetes/kueue-cohort-fair-sharing.yaml`.

## What It Shows

- Kueue Fair Sharing with `preemptionStrategies` for borrowed serving-analysis resources.
- Admission Fair Sharing so `LocalQueue` admission accounts for decayed historical usage and entry penalties.
- `borrowingLimit` and `lendingLimit` for online-serving, canary-analysis, and load-test tenants.
- `fairSharing.weight` that protects online serving and rollback from synthetic load.
- Preemption policy separation between `withinClusterQueue` and `reclaimWithinCohort`.

## Production Notes

Serving platforms need elasticity for canary analysis and load testing, but online serving and rollback must stay protected. Cohort borrowing keeps spare capacity useful, while Fair Sharing, lending limits, and weighted queues prevent background analysis from starving hot-path serving work.

Admission Fair Sharing adds a second layer inside each `ClusterQueue`: noisy `LocalQueue` submitters build up historical usage and lose admission priority until their share decays.

## References

- Kueue ClusterQueue: <https://kueue.sigs.k8s.io/docs/concepts/cluster_queue/>
- Kueue Cohort: <https://kueue.sigs.k8s.io/docs/concepts/cohort/>
- Kueue Preemption and Fair Sharing: <https://kueue.sigs.k8s.io/docs/concepts/preemption/>
- Kueue Admission Fair Sharing: <https://kueue.sigs.k8s.io/docs/concepts/admission_fair_sharing/>
