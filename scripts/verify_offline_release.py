from __future__ import annotations

import argparse
import json
from typing import Sequence

from serenity_alpha_lab.release_gate import (
    build_release_check_plan,
    run_release_check,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Serenity's offline, no-secret application release gate."
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        help="Print the machine-readable release plan without running checks.",
    )
    parser.add_argument(
        "--skip-browser-smoke",
        action="store_true",
        help="Explicitly skip the environment-dependent browser smoke check.",
    )
    parser.add_argument(
        "--skip-docker-smoke",
        action="store_true",
        help="Explicitly skip the environment-dependent Docker smoke check.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.plan:
        print(json.dumps(build_release_check_plan(), ensure_ascii=False, indent=2))
        return 0

    result = run_release_check(
        include_browser_smoke=not args.skip_browser_smoke,
        include_docker_smoke=not args.skip_docker_smoke,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
