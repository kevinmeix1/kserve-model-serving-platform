from __future__ import annotations

from pathlib import Path

from .io import write_json


ALLOWED_FLOWS = [
    {
        "source": "credit-risk-gateway",
        "destination": "champion-predictor",
        "port": 8080,
        "protocol": "HTTP over mesh mTLS",
        "justification": "serve production prediction traffic",
    },
    {
        "source": "credit-risk-gateway",
        "destination": "challenger-predictor",
        "port": 8080,
        "protocol": "HTTP over mesh mTLS",
        "justification": "serve canary and shadow traffic",
    },
    {
        "source": "airflow-rollout-controller",
        "destination": "kserve-api",
        "port": 443,
        "protocol": "HTTPS over mesh mTLS",
        "justification": "adjust traffic weights and run rollback checks",
    },
]


DENIED_FLOWS = [
    {
        "source": "challenger-predictor",
        "destination": "champion-predictor",
        "reason": "model runtimes should not call each other directly",
    },
    {
        "source": "gateway",
        "destination": "model-registry",
        "reason": "gateway routes predictions only; registry access is rollout-controller owned",
    },
]


def build_network_security_report(root: str | Path) -> dict:
    root = Path(root)
    report = {
        "platform": "kserve-model-serving-platform",
        "namespace": "mlops-serving",
        "default_policy": "deny all ingress and egress, then allow gateway, predictor, and rollout-controller flows",
        "mtls_mode": "STRICT",
        "gateway_boundary": "Gateway API owns north-south traffic; predictors only accept gateway traffic",
        "allowed_flow_count": len(ALLOWED_FLOWS),
        "denied_flow_count": len(DENIED_FLOWS),
        "allowed_flows": ALLOWED_FLOWS,
        "denied_by_default": DENIED_FLOWS,
        "controls": [
            "default deny NetworkPolicy for serving namespace",
            "DNS egress allow for service discovery",
            "gateway may call champion and challenger predictors",
            "Istio AuthorizationPolicy blocks direct runtime-to-runtime calls",
        ],
    }
    write_json(root / "reports" / "network_security.json", report)
    return report
