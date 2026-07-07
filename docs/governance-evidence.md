# Governance Evidence

The serving platform generates a release evidence bundle for canary promotion and rollback review:

- `governance/model_card.json`
- `governance/data_card.json`
- `governance/risk_register.json`
- `governance/approval_record.json`
- `governance/reproducibility_manifest.json`
- `reports/governance_evidence_bundle.json`

The bundle connects KServe serving state, registry aliases, prediction logs, request contracts, canary gates, and reproducibility hashes. It is intentionally machine-readable so the same output could be uploaded as a CI artifact or attached to a production change request.

Run it locally:

```bash
make demo
make governance-bundle
```

`kubernetes/governance-evidence.yaml` shows the production-shaped Job and scheduled review loop.
