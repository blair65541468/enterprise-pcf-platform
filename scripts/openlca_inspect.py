from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Sequence

import httpx
import olca_ipc.rest as rest
import olca_schema as o
import requests


DEFAULT_ENV_FILE = Path(".env.openlca.local")
DEFAULT_CASE_FILE = Path("tests/openlca-case.local.json")


@dataclass(frozen=True)
class ConnectionConfig:
    endpoint: str
    token: str | None
    timeout: int


def load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        name, separator, value = stripped.partition("=")
        if not separator or not name.strip():
            raise ValueError(f"invalid dotenv entry at {path}:{line_number}")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ.setdefault(name.strip(), value)


def connection_config(args: argparse.Namespace) -> ConnectionConfig:
    host_port = os.environ.get("OPENLCA_HOST_PORT", "8080").strip() or "8080"
    endpoint = (
        args.url
        or os.environ.get("OPENLCA_URL")
        or f"http://127.0.0.1:{host_port}"
    ).rstrip("/")
    token = args.token if args.token is not None else os.environ.get("OPENLCA_API_TOKEN")
    timeout_text = str(
        args.timeout
        if args.timeout is not None
        else os.environ.get("OPENLCA_TIMEOUT_SECONDS", "600")
    )
    try:
        timeout = int(timeout_text)
    except ValueError as exc:
        raise ValueError("OPENLCA_TIMEOUT_SECONDS/--timeout must be an integer") from exc
    if timeout <= 0:
        raise ValueError("OPENLCA_TIMEOUT_SECONDS/--timeout must be greater than zero")
    if endpoint.startswith(("http://127.0.0.1", "http://localhost")):
        no_proxy = {
            item.strip()
            for item in os.environ.get("NO_PROXY", "").split(",")
            if item.strip()
        }
        no_proxy.update({"127.0.0.1", "localhost"})
        os.environ["NO_PROXY"] = ",".join(sorted(no_proxy))
    return ConnectionConfig(endpoint=endpoint, token=token or None, timeout=timeout)


def create_client(config: ConnectionConfig) -> rest.RestClient:
    headers = {"X-API-TOKEN": config.token} if config.token else None
    return rest.RestClient(config.endpoint, headers=headers, timeout=config.timeout)


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def descriptor_rows(
    client: rest.RestClient,
    model_type: type,
    name_filter: str | None = None,
) -> list[dict[str, Any]]:
    needle = name_filter.casefold() if name_filter else None
    rows = []
    for descriptor in client.get_descriptors(model_type):
        name = descriptor.name or ""
        if needle and needle not in name.casefold():
            continue
        rows.append(
            {
                "id": descriptor.id,
                "name": descriptor.name,
                "category": descriptor.category,
                "ref_type": _enum_value(descriptor.ref_type),
            }
        )
    return sorted(rows, key=lambda row: ((row["name"] or "").casefold(), row["id"] or ""))


def parameter_rows(
    client: rest.RestClient,
    product_system_id: str,
) -> list[dict[str, Any]]:
    rows = []
    for parameter in client.get_parameters(o.ProductSystem, product_system_id):
        context = getattr(parameter, "context", None)
        rows.append(
            {
                "name": parameter.name,
                "value": parameter.value,
                "description": parameter.description,
                "is_protected": getattr(parameter, "is_protected", None),
                "context": context.to_dict() if context else None,
            }
        )
    return sorted(rows, key=lambda row: (row["name"] or "").casefold())


def _require_descriptor(
    client: rest.RestClient,
    model_type: type,
    uid: str,
    label: str,
) -> o.Ref:
    descriptor = client.get_descriptor(model_type, uid=uid)
    if descriptor is None:
        raise RuntimeError(f"{label} not found in openLCA: {uid}")
    return descriptor


def _parameter_redefs(
    parameters: dict[str, Any],
    contexts: dict[str, dict[str, Any]],
) -> list[o.ParameterRedef]:
    return [
        o.ParameterRedef(
            name=name,
            value=float(value),
            context=o.Ref.from_dict(contexts[name]) if name in contexts else None,
        )
        for name, value in parameters.items()
    ]


def calculate_impacts(
    client: rest.RestClient,
    product_system_id: str,
    impact_method_id: str,
    parameters: dict[str, Any] | None = None,
    parameter_contexts: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    product_system = _require_descriptor(
        client, o.ProductSystem, product_system_id, "Product System"
    )
    impact_method = _require_descriptor(
        client, o.ImpactMethod, impact_method_id, "Impact Method"
    )
    setup = o.CalculationSetup(
        target=product_system,
        impact_method=impact_method,
        parameters=_parameter_redefs(parameters or {}, parameter_contexts or {}),
    )
    result = client.calculate(setup)
    if result is None:
        raise RuntimeError("openLCA returned no result handle")
    try:
        state = result.wait_until_ready()
        if getattr(state, "error", None):
            raise RuntimeError(f"openLCA calculation failed: {state.error}")
        rows = []
        for impact in result.get_total_impacts():
            category = impact.impact_category
            rows.append(
                {
                    "id": category.id if category else None,
                    "name": category.name if category else None,
                    "amount": str(Decimal(str(impact.amount))),
                }
            )
        return sorted(rows, key=lambda row: (row["name"] or "").casefold())
    finally:
        result.dispose()


def build_case_template(
    client: rest.RestClient,
    product_system_id: str,
    impact_method_id: str,
) -> dict[str, Any]:
    product_system = _require_descriptor(
        client, o.ProductSystem, product_system_id, "Product System"
    )
    impact_method = _require_descriptor(
        client, o.ImpactMethod, impact_method_id, "Impact Method"
    )
    parameters = parameter_rows(client, product_system_id)
    return {
        "product_system_uuid": product_system.id,
        "impact_method_uuid": impact_method.id,
        "impact_method": impact_method.name,
        "parameters": {row["name"]: row["value"] for row in parameters if row["name"]},
        "parameter_contexts": {
            row["name"]: row["context"]
            for row in parameters
            if row["name"] and row["context"]
        },
        "stage_process_uuids": {},
        "expected_total_kg_co2e": None,
        "absolute_tolerance_kg_co2e": 0.01,
        "relative_tolerance": 0.001,
        "_instructions": (
            "Set expected_total_kg_co2e from an independent openLCA Desktop baseline "
            "before running the integration test."
        ),
    }


def write_case_template(path: Path, payload: dict[str, Any], force: bool = False) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"refusing to overwrite existing test case: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_case_values(path: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    parameters = payload.get("parameters") or {}
    contexts = payload.get("parameter_contexts") or {}
    if not isinstance(parameters, dict) or not isinstance(contexts, dict):
        raise ValueError("case file parameters and parameter_contexts must be JSON objects")
    return parameters, contexts


def parse_parameter_values(values: Sequence[str]) -> dict[str, Decimal]:
    parsed: dict[str, Decimal] = {}
    for value in values:
        name, separator, raw = value.partition("=")
        if not separator or not name.strip() or not raw.strip():
            raise ValueError(f"parameter must use NAME=VALUE syntax: {value}")
        parsed[name.strip()] = Decimal(raw.strip())
    return parsed


def emit(value: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return
    if isinstance(value, dict):
        for key, item in value.items():
            print(f"{key}: {item}")
        return
    for row in value:
        if "amount" in row:
            print(f"{row.get('name') or ''}\t{row['amount']}\t{row.get('id') or ''}")
        elif "value" in row:
            context = json.dumps(row.get("context"), ensure_ascii=False)
            print(f"{row.get('name') or ''}\t{row.get('value')}\t{context}")
        else:
            print(f"{row.get('name') or ''}\t{row.get('id') or ''}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect a local gdt-server and prepare openLCA integration tests."
    )
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--url")
    parser.add_argument("--token")
    parser.add_argument("--timeout", type=int)
    subparsers = parser.add_subparsers(dest="command", required=True)

    health = subparsers.add_parser("health", help="check the openLCA REST version")
    health.add_argument("--json", action="store_true")

    descriptor_commands = {
        "list-product-systems": o.ProductSystem,
        "list-impact-methods": o.ImpactMethod,
        "list-processes": o.Process,
    }
    for name in descriptor_commands:
        command = subparsers.add_parser(name)
        command.add_argument("--filter")
        command.add_argument("--json", action="store_true")

    parameters = subparsers.add_parser("parameters")
    parameters.add_argument("--product-system-id", required=True)
    parameters.add_argument("--json", action="store_true")

    baseline = subparsers.add_parser("baseline")
    baseline.add_argument("--product-system-id", required=True)
    baseline.add_argument("--impact-method-id", required=True)
    baseline.add_argument("--parameter", action="append", default=[])
    baseline.add_argument("--case-file", type=Path)
    baseline.add_argument("--json", action="store_true")

    case_template = subparsers.add_parser("case-template")
    case_template.add_argument("--product-system-id", required=True)
    case_template.add_argument("--impact-method-id", required=True)
    case_template.add_argument("--output", type=Path)
    case_template.add_argument("--force", action="store_true")

    parser.set_defaults(descriptor_commands=descriptor_commands)
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    client_factory: Callable[[ConnectionConfig], rest.RestClient] = create_client,
    http_get: Callable[..., httpx.Response] = httpx.get,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    load_env_file(args.env_file)
    config = connection_config(args)

    try:
        if args.command == "health":
            headers = {"X-API-TOKEN": config.token} if config.token else None
            response = http_get(
                f"{config.endpoint}/api/version",
                headers=headers,
                timeout=min(config.timeout, 20),
                trust_env=False,
            )
            response.raise_for_status()
            payload = {
                "status": "ok",
                "endpoint": config.endpoint,
                "version": response.json(),
            }
            emit(payload, args.json)
            return 0

        client = client_factory(config)
        if args.command in args.descriptor_commands:
            rows = descriptor_rows(
                client,
                args.descriptor_commands[args.command],
                args.filter,
            )
            emit(rows, args.json)
            return 0
        if args.command == "parameters":
            emit(parameter_rows(client, args.product_system_id), args.json)
            return 0
        if args.command == "baseline":
            parameters: dict[str, Any] = {}
            contexts: dict[str, dict[str, Any]] = {}
            if args.case_file:
                parameters, contexts = load_case_values(args.case_file)
            parameters.update(parse_parameter_values(args.parameter))
            rows = calculate_impacts(
                client,
                args.product_system_id,
                args.impact_method_id,
                parameters,
                contexts,
            )
            emit(rows, args.json)
            return 0
        if args.command == "case-template":
            output = args.output or Path(
                os.environ.get("OPENLCA_TEST_CASE_FILE", str(DEFAULT_CASE_FILE))
            )
            payload = build_case_template(
                client,
                args.product_system_id,
                args.impact_method_id,
            )
            write_case_template(output, payload, force=args.force)
            print(f"Wrote openLCA test case template: {output.resolve()}")
            return 0
    except (
        FileExistsError,
        FileNotFoundError,
        ValueError,
        RuntimeError,
        httpx.HTTPError,
        requests.RequestException,
    ) as exc:
        parser.exit(1, f"error: {exc}\n")

    parser.error(f"unsupported command: {args.command}")
    return 2
