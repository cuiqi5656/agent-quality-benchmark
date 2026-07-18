from __future__ import annotations

from pathlib import Path

import yaml

from .models import BenchmarkSuite


def load_suite(path: str | Path) -> BenchmarkSuite:
    with Path(path).open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    return BenchmarkSuite.model_validate(payload)
