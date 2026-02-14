from __future__ import annotations

import argparse
import json
from pathlib import Path

from .agent import DoctrineInsightsAgent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="story-agent",
        description=(
            "Generate LDS doctrine/current-events insight story cards with citations, "
            "quote verification, and non-AI image sourcing."
        ),
    )
    parser.add_argument(
        "--config",
        default="config/sources.example.yaml",
        help="Path to source config YAML.",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory where JSON, Markdown, and Instagram export outputs are written.",
    )
    parser.add_argument(
        "--max-insights",
        type=int,
        default=5,
        help="Maximum number of insight cards to emit.",
    )
    parser.add_argument(
        "--no-images",
        action="store_true",
        help="Skip image lookup step.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    agent = DoctrineInsightsAgent()
    try:
        result = agent.run(
            config_path=Path(args.config),
            output_dir=Path(args.output_dir),
            max_insights=args.max_insights,
            attach_images=not args.no_images,
        )
    finally:
        agent.close()

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
