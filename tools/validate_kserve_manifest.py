from __future__ import annotations

import argparse
import urllib.request
from pathlib import Path

import jsonschema
import yaml


KSERVE_VERSION = "0.18.0"
DEFAULT_CRD_URL = (
    "https://raw.githubusercontent.com/kserve/kserve/"
    f"v{KSERVE_VERSION}/config/crd/full/serving.kserve.io_inferenceservices.yaml"
)


def read_crd(url: str) -> dict:
    request = urllib.request.Request(
        url, headers={"User-Agent": "kserve-portfolio-schema-validator"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return next(yaml.safe_load_all(response.read().decode("utf-8")))


def validate_manifest(manifest_path: Path, *, crd_url: str) -> list[str]:
    crd = read_crd(crd_url)
    version = next(
        item for item in crd["spec"]["versions"] if item["name"] == "v1beta1"
    )
    schema = version["schema"]["openAPIV3Schema"]
    validator = jsonschema.Draft7Validator(schema)
    errors: list[str] = []
    for document_index, manifest in enumerate(
        yaml.safe_load_all(manifest_path.read_text(encoding="utf-8"))
    ):
        if manifest is None or manifest.get("kind") != "InferenceService":
            continue
        for error in sorted(
            validator.iter_errors(manifest), key=lambda item: list(item.path)
        ):
            location = ".".join(str(part) for part in error.path) or "<root>"
            errors.append(f"document {document_index}: {location}: {error.message}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate an InferenceService against the pinned KServe CRD"
    )
    parser.add_argument(
        "manifest",
        nargs="?",
        type=Path,
        default=Path("kserve/custom-runtime-inferenceservice.yaml"),
    )
    parser.add_argument("--crd-url", default=DEFAULT_CRD_URL)
    args = parser.parse_args()

    errors = validate_manifest(args.manifest, crd_url=args.crd_url)
    if errors:
        print("\n".join(errors))
        return 1
    print(
        f"KServe v{KSERVE_VERSION} InferenceService schema validation passed: {args.manifest}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
