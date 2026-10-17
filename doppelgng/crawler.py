"""Load the user's crawler in place, preserving its source and module behavior."""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys


def load_crawler(directory: str | Path):
    directory = Path(directory).resolve()
    source = directory / "webcrawler.py"
    signatures = directory / "signatures.py"
    if not source.is_file() or not signatures.is_file():
        raise ValueError(f"Expected webcrawler.py and signatures.py in {directory}")
    # Isolate the signature import from any other installed 'signatures' module.
    original = sys.modules.pop("signatures", None)
    sys.path.insert(0, str(directory))
    name = "_doppelgng_existing_crawler"
    try:
        spec = importlib.util.spec_from_file_location(name, source)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
        sys.modules.pop("signatures", None)
        if original is not None:
            sys.modules["signatures"] = original
    required = ("_normalize_url", "_extract_links", "_can_fetch", "crawl")
    if not all(hasattr(module.WebCrawler, name) for name in required):
        raise ValueError("The configured crawler does not expose the inspected WebCrawler API")
    return module


def crawler_identity(directory: str | Path) -> dict:
    directory = Path(directory).resolve()
    return {
        "directory": str(directory),
        "files": {
            name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
            for name in ("webcrawler.py", "signatures.py")
        },
    }
