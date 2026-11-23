"""Check a local semantic mapping against supplied schema metadata."""

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

CARDINALITIES = {"one-to-one", "one-to-many", "many-to-one", "many-to-many"}


def validate(bundle: object) -> dict:
    """Return structural errors and checks that still require human review."""
    if not isinstance(bundle, dict):
        raise ValueError("expected a JSON object")

    errors: list[str] = []
    review = [
        "Reconcile totals and breakdowns with an approved baseline and check the actual join cardinality.",
        "Confirm the calculation, filters, date rules, and owner approval before publishing.",
    ]
    tables = bundle.get("schema")
    columns: dict[str, set[str]] = {}
    if not isinstance(tables, dict) or not tables:
        errors.append("schema must be a non-empty object mapping tables to column lists")
    else:
        for table, names in tables.items():
            if not table.strip() or not isinstance(names, list) or not names or any(
                not isinstance(name, str) or not name.strip() for name in names
            ):
                errors.append(f"schema[{table!r}] must name a table and a non-empty list of columns")
                continue
            columns[table] = set(names)
            if len(columns[table]) != len(names):
                errors.append(f"schema[{table!r}] contains duplicate columns")

    def check_ref(ref: object, location: str) -> None:
        if not isinstance(ref, str) or "." not in ref:
            errors.append(f"{location} must be a table.column reference")
            return
        table, column = ref.rsplit(".", 1)
        if column not in columns.get(table, ()):
            errors.append(f"{location} references unknown column {ref!r}")

    metric = bundle.get("metric")
    if not isinstance(metric, dict):
        errors.append("metric must be an object")
        metric = {}
    for field in ("name", "owner", "grain", "calculation"):
        value = metric.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"metric.{field} must be a non-empty string")

    refs = metric.get("columns")
    if not isinstance(refs, list) or not refs:
        errors.append("metric.columns must be a non-empty list")
    else:
        for index, ref in enumerate(refs):
            check_ref(ref, f"metric.columns[{index}]")

    joins = metric.get("joins")
    if not isinstance(joins, list):
        errors.append("metric.joins must be a list (empty for a single-table metric)")
    else:
        for index, join in enumerate(joins):
            location = f"metric.joins[{index}]"
            if not isinstance(join, dict):
                errors.append(f"{location} must be an object")
                continue
            for side in ("left", "right"):
                check_ref(join.get(side), f"{location}.{side}")
            cardinality = join.get("cardinality")
            if not isinstance(cardinality, str) or cardinality not in CARDINALITIES:
                errors.append(f"{location}.cardinality must be one of {', '.join(sorted(CARDINALITIES))}")
            elif cardinality != "one-to-one":
                review.append(f"{location} is declared {cardinality}; check for fan-out at the metric grain.")

    name = metric.get("name")
    return {
        "metric": name if isinstance(name, str) else None,
        "status": "fail" if errors else "pass",
        "errors": errors,
        "human_review": review,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mapping", type=Path, help="JSON file with schema and metric objects")
    args = parser.parse_args(argv)

    try:
        report = validate(json.loads(args.mapping.read_text(encoding="utf-8-sig")))
    except (OSError, ValueError) as exc:
        print(f"Could not read mapping: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(report, indent=2))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
