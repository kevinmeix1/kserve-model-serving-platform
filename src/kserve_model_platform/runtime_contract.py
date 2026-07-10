MODEL_NAME = "credit-risk-router"
SERVER_VERSION = "0.2.0"

INPUT_SPECS = {
    "customer_id": "BYTES",
    "product": "BYTES",
    "income": "FP64",
    "debt_ratio": "FP64",
    "delinquencies": "INT64",
    "utilization": "FP64",
    "employment_years": "FP64",
}

OUTPUT_SPECS = {
    "risk_score": "FP64",
    "risk_band": "BYTES",
    "model_version": "BYTES",
    "selected_alias": "BYTES",
}
