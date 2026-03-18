"""CLI entry point for pipeline runner.

Usage:
    poetry run pipeline ci
    poetry run pipeline test
    poetry run pipeline security
    poetry run pipeline --list
"""

from __future__ import annotations

import argparse
import json
import sys

from tools.pipeline_runner.pipelines import REGISTRY


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run project pipelines",
        prog="pipeline",
    )
    parser.add_argument(
        "pipeline",
        nargs="?",
        help=f"Pipeline to run. Available: {', '.join(REGISTRY.keys())}",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available pipelines",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    if args.list:
        for name, factory in REGISTRY.items():
            p = factory()
            print(f"  {name:15s} - {len(p._steps)} steps")
        return

    if not args.pipeline:
        parser.print_help()
        sys.exit(1)

    if args.pipeline not in REGISTRY:
        print(f"Unknown pipeline: {args.pipeline}")
        print(f"Available: {', '.join(REGISTRY.keys())}")
        sys.exit(1)

    pipeline = REGISTRY[args.pipeline]()
    result = pipeline.run()

    if args.json_output:
        output = {
            "pipeline": result.name,
            "passed": result.passed,
            "duration_s": result.duration_s,
            "steps": [
                {
                    "name": s.name,
                    "status": s.status.value,
                    "duration_s": s.duration_s,
                    "message": s.message,
                }
                for s in result.steps
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        print()
        for s in result.steps:
            icon = {"passed": "✓", "failed": "✗", "skipped": "○"}[s.status.value]
            suffix = f" - {s.message}" if s.message else ""
            print(f"  {icon} {s.name} ({s.duration_s:.2f}s){suffix}")
        print()
        print(result.summary)

    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
