# Supply Chain Provenance

This project treats generated serving reports as build subjects. The CI workflow uploads them as review artifacts and signs their provenance with GitHub artifact attestations.

## What The Demo Generates

- `.local/reports/supply_chain_evidence.json` - artifact inventory, SHA-256 digests, controls, verification commands, and residual risks.
- `.local/supply-chain/subject.checksums.txt` - checksum subject list for deterministic local review.
- `kubernetes/supply-chain-policy.yaml` - Sigstore policy-controller sketch for keyless GitHub Actions identities.

## CI Attestation Flow

The workflow grants only the permissions needed for provenance: read-only contents, OIDC token minting, attestation write, and artifact metadata write. After `make demo`, `make ci-verify`, and `make test` pass, `actions/attest@v4` signs `.local/reports/**`.

This follows GitHub's artifact-attestation model, which emits signed claims about where and how an artifact was built, and SLSA's provenance framing for describing the build inputs and builder.

## Kubernetes Admission Flow

The Sigstore policy-controller manifest opts the `mlops-serving` namespace into verification and starts with `no-match-policy: warn`. Production rollout should move to deny mode only after every KServe image has digest-pinned signatures and provenance attestations.

The ClusterImagePolicy expects keyless certificates issued through GitHub Actions OIDC and checks for a SLSA provenance attestation type.

## Verification Examples

```bash
gh attestation verify .local/reports/index.html --owner kevinmeix1
gh attestation verify .local/reports --repo kevinmeix1/kserve-model-serving-platform
cosign verify-attestation --type slsaprovenance ghcr.io/kevinmeix1/kserve-model-serving-platform@sha256:<digest>
```

## Production Notes

In a real serving platform, the same pattern should be applied to model server images, model artifacts, SBOMs, and rollout bundles. The next hardening step would add image builds, SBOM generation, vulnerability scan attestations, digest-pinned KServe manifests, and scheduled OpenSSF Scorecard-style repository posture checks.

## Research Basis

- GitHub artifact attestations: https://docs.github.com/actions/security-for-github-actions/using-artifact-attestations
- GitHub `actions/attest`: https://github.com/actions/attest
- SLSA specification: https://slsa.dev/spec/v1.2/
- Sigstore policy-controller: https://docs.sigstore.dev/policy-controller/overview/
- OpenSSF security baseline: https://baseline.openssf.org/
