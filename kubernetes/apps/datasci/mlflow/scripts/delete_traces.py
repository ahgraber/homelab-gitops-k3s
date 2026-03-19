#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "mlflow",
# ]
# ///
"""Delete MLflow traces by age or explicit trace IDs.

Usage examples:
  ./scripts/mlflow/delete_traces.py older-than-days \
    --experiment-id 1 --days 7

  ./scripts/mlflow/delete_traces.py trace-ids \
    --experiment-id 1 --trace-ids trace_id_1,trace_id_2

  uv run scripts/mlflow/delete_traces.py older-than-days \
    --experiment-id 1 --days 7
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from mlflow import MlflowClient


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Delete MLflow traces")
    subparsers = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--experiment-id", required=True, help="MLflow experiment ID")
    common.add_argument("--tracking-uri", help="MLflow tracking URI")
    common.add_argument(
        "--yes",
        action="store_true",
        help="Skip interactive confirmation",
    )

    older = subparsers.add_parser("older-than-days", parents=[common])
    older.add_argument("--days", type=int, required=True, help="Delete traces older than this many days")

    trace_ids = subparsers.add_parser("trace-ids", parents=[common])
    trace_ids.add_argument(
        "--trace-ids",
        help="Comma-separated trace IDs",
    )
    trace_ids.add_argument(
        "--trace-ids-file",
        help="Path to file with one trace ID per line",
    )

    return parser.parse_args()


def confirm(prompt: str) -> None:
    """Require explicit user confirmation."""
    answer = input(f"{prompt} [y/N]: ").strip().lower()
    if answer not in {"y", "yes"}:
        raise SystemExit("Cancelled")


def load_trace_ids(csv_trace_ids: str | None, ids_file: str | None) -> list[str]:
    """Load, normalize, and deduplicate trace IDs from CSV and/or file."""
    ids: list[str] = []

    if csv_trace_ids:
        ids.extend(part.strip() for part in csv_trace_ids.split(",") if part.strip())

    if ids_file:
        ids.extend(
            line.strip()
            for line in Path(ids_file).read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        )

    deduped: list[str] = []
    seen: set[str] = set()
    for trace_id in ids:
        if trace_id in seen:
            continue
        seen.add(trace_id)
        deduped.append(trace_id)

    return deduped


def main() -> None:
    """Run the CLI entrypoint."""
    args = parse_args()

    client = MlflowClient(tracking_uri=args.tracking_uri)

    if args.command == "older-than-days":
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=args.days)
        cutoff_ms = int(cutoff.timestamp() * 1000)

        if not args.yes:
            confirm(
                "Delete traces for experiment "
                f"{args.experiment_id} older than {args.days} days "
                f"(<= {cutoff.isoformat()})?"
            )

        deleted_count = client.delete_traces(
            experiment_id=args.experiment_id,
            max_timestamp_millis=cutoff_ms,
        )
        print(
            f"Deleted {deleted_count} traces from experiment {args.experiment_id} "
            f"older than {args.days} days"
        )
        return

    trace_ids = load_trace_ids(args.trace_ids, args.trace_ids_file)
    if not trace_ids:
        raise SystemExit("No trace IDs provided. Use --trace-ids and/or --trace-ids-file")

    if not args.yes:
        confirm(
            f"Delete {len(trace_ids)} traces from experiment {args.experiment_id}?"
        )

    deleted_count = client.delete_traces(
        experiment_id=args.experiment_id,
        trace_ids=trace_ids,
    )
    print(
        f"Deleted {deleted_count} traces from experiment {args.experiment_id} "
        f"using {len(trace_ids)} trace IDs"
    )


if __name__ == "__main__":
    main()
