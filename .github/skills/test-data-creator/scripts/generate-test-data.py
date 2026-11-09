#!/usr/bin/env python3
r"""
generate-test-data.py — Fast, streaming synthetic test data generator.

Generates realistic, schema-conformant mock datasets and high-volume performance test data
in SQL (INSERT batches), JSON (array or NDJSON), and CSV formats with constant O(1) memory usage.

Usage:
    # Generate 1,000 JSON user records:
    .\.venv\Scripts\python.exe .github/skills/test-data-creator/scripts/generate-test-data.py --preset users --count 1000 --format json --output scratch/users.json

    # Generate 50,000 SQL batch inserts for orders with 80/20 Pareto customer skew:
    .\.venv\Scripts\python.exe .github/skills/test-data-creator/scripts/generate-test-data.py --preset orders --count 50000 --format sql --table-name customer_orders --batch-size 1000 --skew pareto --output scratch/orders.sql

    # Generate custom schema data (streaming to stdout or file):
    .\.venv\Scripts\python.exe .github/skills/test-data-creator/scripts/generate-test-data.py --fields "id:int,name:name,email:email,status:choice[ACTIVE,PENDING,SUSPENDED],balance:float" --count 5000 --format csv --output scratch/accounts.csv
"""

import argparse
import csv
import datetime
import json
import math
import os
import random
import re
import sys
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

SAMPLES_DEFAULT_FILE = Path(__file__).parent / "samples.json"
SAFE_IDENTIFIER_REGEX = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

DIALECT_TRANSACTIONS = {
    "postgres": ("BEGIN TRANSACTION;\n\n", "COMMIT;\n"),
    "sqlite": ("BEGIN TRANSACTION;\n\n", "COMMIT;\n"),
    "sqlserver": ("BEGIN TRAN;\n\n", "COMMIT TRAN;\n"),
    "mysql": ("START TRANSACTION;\n\n", "COMMIT;\n"),
    "oracle": ("", "\nCOMMIT;\n"),
}


def validate_identifier(name: str, label: str = "identifier") -> str:
    """Validate that a SQL table or column name contains only safe alphanumeric characters."""
    if not SAFE_IDENTIFIER_REGEX.match(name):
        raise ValueError(
            f"Invalid SQL {label} '{name}'. Must match ^[a-zA-Z_][a-zA-Z0-9_]*$ to prevent injection."
        )
    return name


def quote_identifier(name: str, dialect: str = "postgres") -> str:
    """Quote SQL identifier safely according to the target database dialect."""
    validate_identifier(name)
    if dialect == "sqlserver":
        return f"[{name}]"
    elif dialect == "mysql":
        return f"`{name}`"
    else:
        # postgres, sqlite, oracle
        return f'"{name}"'


def load_samples(custom_path: Optional[str] = None) -> Dict[str, List[str]]:
    """Load vocabulary samples from external JSON file with resilient fallbacks or fast failure on custom paths."""
    if custom_path:
        target_file = Path(custom_path)
        if not target_file.exists():
            print(f"[!] Error: Custom samples file not found: '{custom_path}'", file=sys.stderr)
            sys.exit(1)
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] Error: Failed to parse custom samples file '{target_file}': {e}", file=sys.stderr)
            sys.exit(1)

    if SAMPLES_DEFAULT_FILE.exists():
        try:
            with open(SAMPLES_DEFAULT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] Warning: Failed to load default samples from '{SAMPLES_DEFAULT_FILE}': {e}", file=sys.stderr)

    return {
        "first_names": ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda"],
        "last_names": ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Wilson"],
        "domains": ["example.com", "testmail.org", "acme-corp.net"],
        "countries": ["US", "GB", "CA", "DE", "FR", "JP"],
        "order_statuses": ["PENDING", "PROCESSING", "SHIPPED", "DELIVERED", "CANCELED"],
        "payment_methods": ["CREDIT_CARD", "DEBIT_CARD", "PAYPAL", "WIRE_TRANSFER"],
        "currencies": ["USD", "EUR", "GBP", "JPY"],
        "device_names": ["sensor_alpha", "sensor_beta", "temp_probe_01", "gateway_hub"],
    }


def get_skewed_int(max_val: int, skew: str, rng: random.Random) -> int:
    """Generate an integer between 1 and max_val with optional skew (uniform, pareto/zipf, normal)."""
    if max_val <= 1:
        return 1
    if skew == "pareto":
        # 80/20 power law: roughly 80% of references hit top 20% of IDs
        alpha = 1.16
        u = rng.random()
        val = int(1.0 / math.pow(1.0 - u, 1.0 / alpha))
        return min(max_val, max(1, val))
    elif skew == "normal":
        # Centered bell curve
        mu = max_val / 2.0
        sigma = max_val / 6.0
        val = int(rng.gauss(mu, sigma))
        return min(max_val, max(1, val))
    else:
        # Uniform
        return rng.randint(1, max_val)


def generate_users(count: int, rng: random.Random, samples: Dict[str, List[str]], null_ratio: float = 0.0) -> Generator[Dict[str, Any], None, None]:
    """Generate synthetic user account records."""
    first_names = samples.get("first_names", ["James", "Mary", "John"])
    last_names = samples.get("last_names", ["Smith", "Johnson", "Williams"])
    domains = samples.get("domains", ["example.com", "testmail.org"])
    countries = samples.get("countries", ["US", "GB", "CA", "DE"])

    base_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=730)
    for i in range(1, count + 1):
        first = rng.choice(first_names)
        last = rng.choice(last_names)
        username = f"{first.lower()}.{last.lower()}_{i}"
        domain = rng.choice(domains)
        email = f"{username}@{domain}"
        created_delta = datetime.timedelta(
            days=rng.randint(0, 700),
            seconds=rng.randint(0, 86400)
        )
        created_at = (base_date + created_delta).isoformat()
        phone = None if (null_ratio > 0 and rng.random() < null_ratio) else f"+1-555-{rng.randint(100, 999):03d}-{rng.randint(1000, 9999):04d}"
        balance = round(rng.uniform(0.0, 15000.0), 2)
        role = rng.choices(["USER", "ADMIN", "SUPPORT", "MODERATOR"], weights=[85, 5, 5, 5])[0]
        status = rng.choices(["ACTIVE", "INACTIVE", "SUSPENDED"], weights=[90, 7, 3])[0]

        yield {
            "id": i,
            "uuid": str(uuid.UUID(int=rng.getrandbits(128), version=4)),
            "username": username,
            "full_name": f"{first} {last}",
            "email": email,
            "phone": phone,
            "role": role,
            "status": status,
            "balance": balance,
            "country": rng.choice(countries),
            "is_active": status == "ACTIVE",
            "created_at": created_at,
        }


def generate_orders(count: int, rng: random.Random, samples: Dict[str, List[str]], skew: str = "uniform", max_user_id: int = 10000, null_ratio: float = 0.0) -> Generator[Dict[str, Any], None, None]:
    """Generate synthetic customer order records with relational foreign key distribution."""
    order_statuses = samples.get("order_statuses", ["PENDING", "PROCESSING", "SHIPPED", "DELIVERED", "CANCELED"])
    currencies = samples.get("currencies", ["USD", "EUR", "GBP", "JPY"])
    payment_methods = samples.get("payment_methods", ["CREDIT_CARD", "DEBIT_CARD", "PAYPAL", "WIRE_TRANSFER"])

    base_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=365)
    for i in range(1, count + 1):
        user_id = get_skewed_int(max_user_id, skew, rng)
        order_no = f"ORD-{rng.randint(1000, 9999)}-{i:07d}"
        created_delta = datetime.timedelta(days=rng.randint(0, 360), seconds=rng.randint(0, 86400))
        created_at = (base_date + created_delta).isoformat()
        items_count = rng.randint(1, 12)
        total_amount = round(rng.uniform(5.0, 1200.0) * (items_count / 2.0), 2)
        status = rng.choice(order_statuses)
        tracking_no = None if (status in ["PENDING", "CANCELED"] or (null_ratio > 0 and rng.random() < null_ratio)) else f"TRK{rng.randint(10000000, 99999999)}"

        yield {
            "id": i,
            "order_number": order_no,
            "customer_id": user_id,
            "total_amount": total_amount,
            "currency": rng.choice(currencies),
            "payment_method": rng.choice(payment_methods),
            "status": status,
            "items_count": items_count,
            "tracking_number": tracking_no,
            "created_at": created_at,
        }


def generate_metrics(count: int, rng: random.Random, samples: Dict[str, List[str]]) -> Generator[Dict[str, Any], None, None]:
    """Generate high-frequency time-series / IoT sensor metric telemetry records."""
    device_names = samples.get("device_names", ["sensor_alpha", "gateway_hub", "temp_probe_01"])

    base_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=24)
    for i in range(1, count + 1):
        device = rng.choice(device_names)
        ts = (base_time + datetime.timedelta(milliseconds=i * 100)).isoformat()
        metric_type = rng.choice(["temperature_celsius", "pressure_psi", "cpu_load_percent", "memory_used_mb", "rpm"])
        if metric_type == "temperature_celsius":
            val = round(rng.gauss(65.0, 8.0), 2)
            unit = "C"
        elif metric_type == "pressure_psi":
            val = round(rng.uniform(30.0, 120.0), 2)
            unit = "psi"
        elif metric_type == "cpu_load_percent":
            val = round(rng.uniform(5.0, 99.5), 1)
            unit = "%"
        elif metric_type == "memory_used_mb":
            val = rng.randint(512, 16384)
            unit = "MB"
        else:
            val = rng.randint(1000, 6000)
            unit = "RPM"

        yield {
            "id": i,
            "device_id": device,
            "metric_name": metric_type,
            "metric_value": val,
            "unit": unit,
            "recorded_at": ts,
        }


def parse_custom_fields(fields_str: str) -> List[Tuple[str, str, Optional[List[str]]]]:
    """Parse field specification string: 'id:int,name:name,status:choice[A,B,C],val:float'."""
    parsed = []
    # Tokenize by comma while respecting brackets
    tokens: List[str] = []
    current: List[str] = []
    depth = 0
    for ch in fields_str:
        if ch == "[":
            depth += 1
            current.append(ch)
        elif ch == "]":
            depth = max(0, depth - 1)
            current.append(ch)
        elif ch == "," and depth == 0:
            tok = "".join(current).strip()
            if tok:
                tokens.append(tok)
            current.clear()
        else:
            current.append(ch)
    final_tok = "".join(current).strip()
    if final_tok:
        tokens.append(final_tok)

    for token in tokens:
        if ":" not in token:
            fname = validate_identifier(token, "field name")
            parsed.append((fname, "str", None))
            continue
        fname, ftype = token.split(":", 1)
        fname = validate_identifier(fname.strip(), "field name")
        ftype = ftype.strip()
        choices = None
        if ftype.startswith("choice[") and ftype.endswith("]"):
            inner = ftype[7:-1]
            delimiter = "|" if "|" in inner else ","
            choices = [c.strip() for c in inner.split(delimiter) if c.strip()]
            ftype = "choice"
        parsed.append((fname, ftype, choices))
    return parsed


def generate_custom(fields: List[Tuple[str, str, Optional[List[str]]]], count: int, rng: random.Random, samples: Dict[str, List[str]]) -> Generator[Dict[str, Any], None, None]:
    """Generate arbitrary synthetic data matching custom fields."""
    first_names = samples.get("first_names", ["James", "Mary", "John"])
    last_names = samples.get("last_names", ["Smith", "Johnson", "Williams"])
    domains = samples.get("domains", ["example.com", "testmail.org"])

    base_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=365)
    for i in range(1, count + 1):
        row: Dict[str, Any] = {}
        for fname, ftype, choices in fields:
            if ftype in ["int", "integer", "id"]:
                row[fname] = i if ftype == "id" else rng.randint(1, 100000)
            elif ftype in ["float", "decimal", "amount"]:
                row[fname] = round(rng.uniform(1.0, 5000.0), 2)
            elif ftype in ["uuid", "guid"]:
                row[fname] = str(uuid.UUID(int=rng.getrandbits(128), version=4))
            elif ftype in ["name", "full_name"]:
                row[fname] = f"{rng.choice(first_names)} {rng.choice(last_names)}"
            elif ftype in ["email"]:
                user = f"{rng.choice(first_names).lower()}.{rng.choice(last_names).lower()}_{i}"
                row[fname] = f"{user}@{rng.choice(domains)}"
            elif ftype in ["date", "timestamp", "datetime"]:
                dt = base_date + datetime.timedelta(days=rng.randint(0, 360), seconds=rng.randint(0, 86400))
                row[fname] = dt.isoformat()
            elif ftype in ["bool", "boolean"]:
                row[fname] = rng.random() > 0.5
            elif ftype == "choice" and choices:
                row[fname] = rng.choice(choices)
            else:
                row[fname] = f"val_{fname}_{i}"
        yield row


def escape_sql_val(val: Any) -> str:
    """Format Python values into valid SQL literal values."""
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "1" if val else "0"
    if isinstance(val, (int, float)):
        return str(val)
    # String / Timestamp / UUID: escape single quotes
    s_val = str(val).replace("'", "''")
    return f"'{s_val}'"


def write_sql_stream(
    out_fp,
    records: Generator[Dict[str, Any], None, None],
    table_name: str,
    batch_size: int,
    count: int,
    dialect: str = "postgres",
) -> int:
    """Stream records as chunked multi-row SQL INSERT statements with dialect-aware identifier escaping and transaction blocks."""
    quoted_table = quote_identifier(table_name, dialect=dialect)
    begin_stmt, commit_stmt = DIALECT_TRANSACTIONS.get(
        dialect, ("BEGIN TRANSACTION;\n\n", "COMMIT;\n")
    )

    out_fp.write(f"-- Generated {count} synthetic records for table [{table_name}] ({dialect})\n")
    if begin_stmt:
        out_fp.write(begin_stmt)

    batch: List[Dict[str, Any]] = []
    columns: Optional[List[str]] = None
    quoted_cols_str: str = ""
    written = 0

    for record in records:
        if columns is None:
            columns = list(record.keys())
            quoted_cols = [quote_identifier(c, dialect=dialect) for c in columns]
            quoted_cols_str = ", ".join(quoted_cols)
        batch.append(record)
        written += 1

        if len(batch) >= batch_size:
            out_fp.write(f"INSERT INTO {quoted_table} ({quoted_cols_str}) VALUES\n")
            value_rows = []
            for r in batch:
                row_vals = ", ".join([escape_sql_val(r[c]) for c in columns])
                value_rows.append(f"  ({row_vals})")
            out_fp.write(",\n".join(value_rows) + ";\n\n")
            batch.clear()

    # Flush remaining batch
    if batch and columns:
        out_fp.write(f"INSERT INTO {quoted_table} ({quoted_cols_str}) VALUES\n")
        value_rows = []
        for r in batch:
            row_vals = ", ".join([escape_sql_val(r[c]) for c in columns])
            value_rows.append(f"  ({row_vals})")
        out_fp.write(",\n".join(value_rows) + ";\n\n")
        batch.clear()

    if commit_stmt:
        out_fp.write(commit_stmt)
    return written


def write_json_stream(out_fp, records: Generator[Dict[str, Any], None, None], as_ndjson: bool) -> int:
    """Stream records in JSON array or NDJSON format with constant memory."""
    written = 0
    if as_ndjson:
        for r in records:
            out_fp.write(json.dumps(r) + "\n")
            written += 1
    else:
        out_fp.write("[\n")
        first = True
        for r in records:
            if not first:
                out_fp.write(",\n")
            else:
                first = False
            out_fp.write("  " + json.dumps(r))
            written += 1
        out_fp.write("\n]\n")
    return written


def write_csv_stream(out_fp, records: Generator[Dict[str, Any], None, None]) -> int:
    """Stream records as CSV with constant memory."""
    writer = None
    written = 0
    for r in records:
        if writer is None:
            writer = csv.DictWriter(out_fp, fieldnames=list(r.keys()))
            writer.writeheader()
        writer.writerow(r)
        written += 1
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Streaming Synthetic Test Data Generator")
    parser.add_argument("--preset", choices=["users", "orders", "metrics"], help="Built-in domain schema preset")
    parser.add_argument("--fields", help="Custom field spec (e.g. 'id:id,name:name,email:email,status:choice[A|B|C]')")
    parser.add_argument("--count", type=int, default=1000, help="Number of records to generate (default: 1000)")
    parser.add_argument("--format", choices=["json", "ndjson", "sql", "csv"], default="json", help="Output format (default: json)")
    parser.add_argument(
        "--dialect",
        choices=["postgres", "sqlite", "sqlserver", "mysql", "oracle"],
        default="postgres",
        help="SQL dialect for quoting and transaction semantics (default: postgres)",
    )
    parser.add_argument("--table-name", default="test_records", help="Target table name for SQL format")
    parser.add_argument("--batch-size", type=int, default=1000, help="Number of rows per SQL INSERT statement (default: 1000)")
    parser.add_argument("--skew", choices=["uniform", "pareto", "normal"], default="uniform", help="Distribution skew for foreign keys (default: uniform)")
    parser.add_argument("--null-ratio", type=float, default=0.0, help="Fraction of nullable fields set to null (0.0 to 1.0)")
    parser.add_argument("--seed", type=int, default=42, help="Pseudo-random generator seed for reproducible datasets")
    parser.add_argument("--samples-file", help="Path to custom JSON samples file (defaults to samples.json)")
    parser.add_argument("--output", help="Output file path (defaults to stdout)")

    args = parser.parse_args()

    if not args.preset and not args.fields:
        print("Error: Specify either --preset [users|orders|metrics] or --fields 'id:int,name:name,...'", file=sys.stderr)
        sys.exit(1)

    rng = random.Random(args.seed)
    samples = load_samples(args.samples_file)

    # Initialize generator stream
    if args.preset == "users":
        stream = generate_users(args.count, rng, samples, null_ratio=args.null_ratio)
    elif args.preset == "orders":
        stream = generate_orders(args.count, rng, samples, skew=args.skew, null_ratio=args.null_ratio)
    elif args.preset == "metrics":
        stream = generate_metrics(args.count, rng, samples)
    elif args.fields:
        parsed_fields = parse_custom_fields(args.fields)
        stream = generate_custom(parsed_fields, args.count, rng, samples)
    else:
        sys.exit(1)

    # Resolve output stream
    if args.output:
        out_dir = os.path.dirname(args.output)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)
        out_fp = open(args.output, "w", encoding="utf-8")
    else:
        out_fp = sys.stdout

    try:
        start_time = datetime.datetime.now()
        if args.format == "sql":
            count = write_sql_stream(
                out_fp,
                stream,
                args.table_name,
                args.batch_size,
                args.count,
                dialect=args.dialect,
            )
        elif args.format in ["json", "ndjson"]:
            count = write_json_stream(out_fp, stream, as_ndjson=(args.format == "ndjson"))
        elif args.format == "csv":
            count = write_csv_stream(out_fp, stream)
        else:
            count = 0

        elapsed = (datetime.datetime.now() - start_time).total_seconds()
        ops_sec = (count / elapsed) if elapsed > 0 else 0

        if args.output:
            print(f"Generated {count:,} records into '{args.output}' in {elapsed:.2f}s ({ops_sec:,.0f} records/sec).", file=sys.stderr)
    finally:
        if args.output and out_fp != sys.stdout:
            out_fp.close()


if __name__ == "__main__":
    main()

