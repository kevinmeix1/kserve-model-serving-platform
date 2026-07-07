# Minikube And KServe Notes

The default project runs without Kubernetes. To exercise the manifests locally:

```bash
minikube start --cpus=4 --memory=8192
kubectl create namespace mlops-serving --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f kserve/inferenceservice-canary.yaml
```

Production changes needed:

- Replace `pvc://` model URIs with S3, GCS, Azure Blob, or a mounted PVC.
- Add service authentication and network policies.
- Configure KServe autoscaling for traffic patterns.
- Export model artifacts from MLflow with stable aliases.
- Add Prometheus scraping and Grafana dashboards.
- Add trace IDs to every prediction log.

