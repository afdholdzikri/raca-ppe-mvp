"""Windows-safe project-local pytest temporary directory selection."""
from __future__ import annotations

import os
import uuid
from pathlib import Path


def pytest_configure(config):
    """Avoid reusing an ACL-locked base directory between pytest processes."""
    configured = Path(config.option.basetemp or ".pytest_tmp")
    if configured.name == ".pytest_tmp":
        config.option.basetemp = str(
            configured.with_name(
                f".pytest_tmp-run-{os.getpid()}-{uuid.uuid4().hex[:8]}"
            )
        )
