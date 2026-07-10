from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import risk_band, score, validate_payload
from .runtime_contract import INPUT_SPECS, OUTPUT_SPECS
from .runtime_state import ModelSnapshot
from .serving import request_hash


class TensorInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=128)
    shape: list[int] = Field(min_length=1, max_length=1)
    datatype: Literal["BYTES", "FP64", "INT64"]
    data: list[str | int | float]
    parameters: dict[str, str | int | float | bool] | None = None

    @model_validator(mode="after")
    def validate_tensor_shape(self) -> TensorInput:
        if self.shape[0] <= 0:
            raise ValueError("tensor batch dimension must be positive")
        if self.shape[0] != len(self.data):
            raise ValueError("tensor shape does not match data length")
        return self


class RequestedOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=128)
    parameters: dict[str, str | int | float | bool] | None = None


class InferenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = Field(default=None, min_length=1, max_length=128)
    parameters: dict[str, str | int | float | bool] | None = None
    inputs: list[TensorInput] = Field(min_length=1, max_length=len(INPUT_SPECS))
    outputs: list[RequestedOutput] | None = Field(
        default=None,
        max_length=len(OUTPUT_SPECS),
    )


class ProtocolError(ValueError):
    pass


class ModelVersionNotFound(LookupError):
    pass


def _check_scalar(datatype: str, value: str | int | float) -> bool:
    if datatype == "BYTES":
        return isinstance(value, str)
    if datatype == "INT64":
        return isinstance(value, int) and not isinstance(value, bool)
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def decode_batch(request: InferenceRequest, *, max_batch_size: int) -> list[dict]:
    tensors = {tensor.name: tensor for tensor in request.inputs}
    if len(tensors) != len(request.inputs):
        raise ProtocolError("input tensor names must be unique")
    missing = sorted(set(INPUT_SPECS) - set(tensors))
    unexpected = sorted(set(tensors) - set(INPUT_SPECS))
    if missing or unexpected:
        raise ProtocolError(
            "input tensors do not match the model signature; "
            f"missing={missing}, unexpected={unexpected}"
        )

    batch_sizes = {tensor.shape[0] for tensor in tensors.values()}
    if len(batch_sizes) != 1:
        raise ProtocolError("all input tensors must have the same batch dimension")
    batch_size = batch_sizes.pop()
    if batch_size > max_batch_size:
        raise ProtocolError(f"batch size {batch_size} exceeds limit {max_batch_size}")

    for name, datatype in INPUT_SPECS.items():
        tensor = tensors[name]
        if tensor.datatype != datatype:
            raise ProtocolError(f"tensor {name} must use datatype {datatype}")
        if not all(_check_scalar(datatype, value) for value in tensor.data):
            raise ProtocolError(
                f"tensor {name} contains values incompatible with {datatype}"
            )

    rows: list[dict] = []
    for index in range(batch_size):
        row = {name: tensors[name].data[index] for name in INPUT_SPECS}
        validation = validate_payload({"request_id": f"batch-{index}", **row})
        if not validation["valid"]:
            raise ProtocolError(
                f"row {index} violates the prediction contract: {validation['errors']}"
            )
        rows.append(row)
    return rows


def _selected_outputs(request: InferenceRequest) -> list[str]:
    if request.outputs is None:
        return list(OUTPUT_SPECS)
    names = [output.name for output in request.outputs]
    if len(names) != len(set(names)):
        raise ProtocolError("requested output names must be unique")
    unsupported = sorted(set(names) - set(OUTPUT_SPECS))
    if unsupported:
        raise ProtocolError(f"unsupported outputs requested: {unsupported}")
    return names


def infer(
    request: InferenceRequest,
    *,
    request_id: str,
    snapshot: ModelSnapshot,
    model_name: str,
    requested_version: str | None,
    max_batch_size: int,
) -> dict:
    rows = decode_batch(request, max_batch_size=max_batch_size)
    output_names = _selected_outputs(request)
    if requested_version is not None and requested_version not in snapshot.models:
        raise ModelVersionNotFound(f"model version is not loaded: {requested_version}")

    results: list[dict] = []
    for index, row in enumerate(rows):
        row_request_id = f"{request_id}:{index}"
        if requested_version is not None:
            selected_alias = "version"
            version = requested_version
        elif (
            snapshot.challenger
            and request_hash(row_request_id) < snapshot.challenger_percent
        ):
            selected_alias = "challenger"
            version = snapshot.challenger
        else:
            selected_alias = "champion"
            version = snapshot.champion
        model = snapshot.models[version]
        probability = score(model, row)
        results.append(
            {
                "risk_score": probability,
                "risk_band": risk_band(probability),
                "model_version": version,
                "selected_alias": selected_alias,
            }
        )

    outputs = [
        {
            "name": name,
            "shape": [len(results)],
            "datatype": OUTPUT_SPECS[name],
            "data": [result[name] for result in results],
        }
        for name in output_names
    ]
    versions = sorted({result["model_version"] for result in results})
    return {
        "model_name": model_name,
        "model_version": versions[0] if len(versions) == 1 else snapshot.generation,
        "id": request_id,
        "parameters": {
            "batch_size": len(results),
            "idempotent_replay": False,
            "snapshot_generation": snapshot.generation,
        },
        "outputs": outputs,
    }


def output_values(response: dict, name: str) -> list[Any]:
    for output in response.get("outputs", []):
        if output.get("name") == name:
            return list(output.get("data", []))
    return []


def model_metadata(
    model_name: str,
    snapshot: ModelSnapshot,
    version: str | None = None,
) -> dict:
    versions = sorted(snapshot.models)
    if version is not None:
        if version not in snapshot.models:
            raise ModelVersionNotFound(f"model version is not loaded: {version}")
        versions = [version]
    return {
        "name": model_name,
        "versions": versions,
        "platform": "python_logistic_runtime",
        "inputs": [
            {"name": name, "datatype": datatype, "shape": [-1]}
            for name, datatype in INPUT_SPECS.items()
        ],
        "outputs": [
            {"name": name, "datatype": datatype, "shape": [-1]}
            for name, datatype in OUTPUT_SPECS.items()
        ],
    }
