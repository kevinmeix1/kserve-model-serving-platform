# Security And Governance Layer

This repo now includes a manifest policy audit and admission-policy examples.

## Commands

- `make policy-audit` writes `.local/reports/policy_audit.json`.
- `make demo` also emits the same audit report.

## What Is Checked

- Restricted pod security labels.
- Resource requests and limits.
- Non-root execution, dropped capabilities, and read-only root filesystems.
- Kueue queue admission, KEDA event-driven scaling, and weighted Gateway routes.
- Mutable image tags and missing digest references.

## Why The Audit Flags Image Immutability

The local manifests pin workload images to explicit release tags, and the audit now treats `:latest` references as a release-blocking policy failure. In a real release, images should still be scanned, signed, and promoted to digest references after provenance generation.
