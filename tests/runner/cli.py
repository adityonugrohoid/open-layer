"""Thin CLI wrapper around pytest for running conformance tests.

Usage:
    python -m tests.runner.cli                         # All providers, all tests
    python -m tests.runner.cli --provider groq         # Single provider
    python -m tests.runner.cli -m level1               # Only Level 1
    python -m tests.runner.cli --provider deepseek -m level2  # L2 against DeepSeek
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
