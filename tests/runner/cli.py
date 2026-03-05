"""Thin CLI wrapper around pytest for running conformance tests.

Usage:
    python -m tests.runner.cli                         # Smoke subset (5 models)
    python -m tests.runner.cli --all                   # All 52 models
    python -m tests.runner.cli --model llama-3.3-70b   # Single model (substring)
    python -m tests.runner.cli --tag thinking           # Thinking models only
    python -m tests.runner.cli -m level1               # Only Level 1 tests
"""

from __future__ import annotations

import sys

import pytest


def main() -> None:
    args = ["tests/suite/", "-v", "--tb=short"]
    args.extend(sys.argv[1:])
    sys.exit(pytest.main(args))


if __name__ == "__main__":
    main()
