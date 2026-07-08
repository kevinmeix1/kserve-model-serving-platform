# Queue Capacity Simulation

The local queue simulator writes `.local/reports/queue_simulation.json`. It models Kueue quota, serving priority, GPU use, Airflow pool slots, and emergency rollback preemption.

## What It Demonstrates

- Champion predictor prewarm stays protected during rollout windows.
- Canary shadow analysis accounts for GPU and Airflow pool capacity.
- Emergency rollback can preempt low-priority serving experiments.
- Batch replay can remain pending without risking live serving rollback.

## Current References

- Kueue ClusterQueue borrowing and cohorts: <https://kueue.sigs.k8s.io/docs/concepts/cluster_queue/>
- Kueue WorkloadPriorityClass: <https://kueue.sigs.k8s.io/docs/concepts/workload_priority_class/>
- Kueue preemption: <https://kueue.sigs.k8s.io/docs/concepts/preemption/>
- Airflow pools: <https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/pools.html>
- Kubernetes pod priority and preemption: <https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/>

Run `make queue-simulation` after `make demo` to regenerate only this report.
