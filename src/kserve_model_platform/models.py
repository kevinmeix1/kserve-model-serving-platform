from __future__ import annotations

import math
import random


FEATURES = ["income", "debt_ratio", "delinquencies", "utilization", "employment_years"]
REQUIRED_COLUMNS = ["request_id", "customer_id", "product", *FEATURES]


MODEL_CATALOG = {
    "risk-model-2026-07-01": {
        "version": "risk-model-2026-07-01",
        "stage": "champion",
        "bias": -1.05,
        "weights": {
            "income": -0.000018,
            "debt_ratio": 1.7,
            "delinquencies": 0.58,
            "utilization": 1.35,
            "employment_years": -0.08,
        },
        "product_adjustments": {"card": 0.12, "loan": 0.0, "mortgage": -0.25},
    },
    "risk-model-2026-07-15": {
        "version": "risk-model-2026-07-15",
        "stage": "challenger",
        "bias": -1.13,
        "weights": {
            "income": -0.000016,
            "debt_ratio": 1.82,
            "delinquencies": 0.61,
            "utilization": 1.42,
            "employment_years": -0.075,
        },
        "product_adjustments": {"card": 0.10, "loan": 0.0, "mortgage": -0.22},
    },
}


def sigmoid(value: float) -> float:
    return 1 / (1 + math.exp(-max(min(value, 35), -35)))


def validate_payload(payload: dict) -> dict:
    errors = []
    for column in REQUIRED_COLUMNS:
        if payload.get(column) in {"", None}:
            errors.append(f"missing:{column}")
    for feature in FEATURES:
        if feature not in payload:
            continue
        try:
            float(payload[feature])
        except Exception:
            errors.append(f"not_numeric:{feature}")
    if "debt_ratio" in payload and not 0 <= float(payload.get("debt_ratio", -1)) <= 2:
        errors.append("range:debt_ratio")
    if "utilization" in payload and not 0 <= float(payload.get("utilization", -1)) <= 1.5:
        errors.append("range:utilization")
    if "product" in payload and payload.get("product") not in {"card", "loan", "mortgage"}:
        errors.append("allowed:product")
    return {"valid": not errors, "errors": errors}


def score(model: dict, payload: dict) -> float:
    logit = float(model["bias"])
    for feature, weight in model["weights"].items():
        logit += float(weight) * float(payload[feature])
    logit += float(model.get("product_adjustments", {}).get(payload.get("product"), 0.0))
    return round(sigmoid(logit), 6)


def risk_band(probability: float) -> str:
    if probability >= 0.70:
        return "high"
    if probability >= 0.42:
        return "medium"
    return "low"


def generate_requests(count: int = 120, seed: int = 2026) -> list[dict]:
    rng = random.Random(seed)
    rows = []
    products = ["card", "loan", "mortgage"]
    for idx in range(count):
        product = products[idx % len(products)]
        income = max(24000, rng.gauss(92000 if product == "mortgage" else 68000, 18000))
        debt_ratio = min(max(rng.gauss(0.46 if product == "card" else 0.35, 0.18), 0.04), 1.4)
        utilization = min(max(rng.gauss(0.52 if product == "card" else 0.34, 0.22), 0.01), 1.25)
        delinquencies = max(0, int(rng.gauss(0.8 if product == "card" else 0.4, 0.9)))
        employment_years = max(0.2, rng.gauss(5.2 if product != "card" else 3.4, 2.1))
        rows.append(
            {
                "request_id": f"req_{idx:05d}",
                "customer_id": f"cust_{idx:05d}",
                "product": product,
                "income": round(income, 2),
                "debt_ratio": round(debt_ratio, 4),
                "delinquencies": delinquencies,
                "utilization": round(utilization, 4),
                "employment_years": round(employment_years, 2),
            }
        )
    return rows
