#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from scholarly import scholarly


RESULTS_DIR = Path("results")
GS_DATA_PATH = RESULTS_DIR / "gs_data.json"
SHIELDSIO_PATH = RESULTS_DIR / "gs_data_shieldsio.json"

DEFAULT_MAX_TRIES = 10
DEFAULT_WAIT_SECONDS = 60

SCHOLAR_SECTIONS = ["basics", "indices", "counts"]


def utc_now_iso() -> str:
    """Return current UTC time in ISO format."""
    return datetime.utcnow().isoformat()


def log_info(message: str) -> None:
    """Print an info message to stderr."""
    print(f"[INFO] {message}", file=sys.stderr)


def log_warn(message: str) -> None:
    """Print a warning message to stderr."""
    print(f"[WARN] {message}", file=sys.stderr)


def log_error(message: str) -> None:
    """Print an error message to stderr."""
    print(f"[ERROR] {message}", file=sys.stderr)


def fetch_author_once(scholar_id: str) -> Dict[str, Any]:
    """
    Fetch Google Scholar author data once.

    Parameters
    ----------
    scholar_id:
        Google Scholar author ID.

    Returns
    -------
    dict
        Filled author dictionary from scholarly.
    """
    author = scholarly.search_author_id(scholar_id)
    scholarly.fill(author, sections=SCHOLAR_SECTIONS)
    return author


def fetch_author_with_retries(
    scholar_id: str,
    max_tries: int = DEFAULT_MAX_TRIES,
    wait_seconds: int = DEFAULT_WAIT_SECONDS,
) -> Dict[str, Any]:
    """
    Fetch Google Scholar author data with retry logic.

    Raises
    ------
    Exception
        Re-raises the last exception if all attempts fail.
    """
    last_exc: Optional[Exception] = None

    for attempt in range(1, max_tries + 1):
        try:
            log_info(
                f"Fetching Google Scholar data "
                f"(attempt: {attempt}/{max_tries})"
            )
            return fetch_author_once(scholar_id)

        except Exception as exc:
            last_exc = exc
            log_warn(f"Attempt {attempt} failed: {exc}")

            if attempt < max_tries:
                log_info(f"Waiting {wait_seconds} seconds before retry...")
                time.sleep(wait_seconds)

    if last_exc is not None:
        raise last_exc

    raise RuntimeError("Failed to fetch Google Scholar data for unknown reason.")


def build_fallback_author(error: Exception) -> Dict[str, Any]:
    """
    Build fallback author data when Google Scholar fetching fails.

    This preserves the original soft-fail behavior.
    """
    return {
        "name": "UNKNOWN",
        "citedby": 0,
        "error": str(error),
        "updated": utc_now_iso(),
    }


def build_shieldsio_data(citedby: int) -> Dict[str, Any]:
    """
    Build Shields.io-compatible JSON data.
    """
    return {
        "schemaVersion": 1,
        "label": "Google Scholar w/ citation:",
        "message": str(citedby),
    }


def write_json(path: Path, data: Dict[str, Any], *, indent: Optional[int] = None) -> None:
    """
    Write dictionary data to a JSON file.
    """
    with path.open("w", encoding="utf-8") as outfile:
        json.dump(data, outfile, ensure_ascii=False, indent=indent)


def get_scholar_id_from_env() -> str:
    """
    Read Google Scholar ID from environment variable.

    Raises
    ------
    RuntimeError
        If GOOGLE_SCHOLAR_ID is not set.
    """
    scholar_id = os.environ.get("GOOGLE_SCHOLAR_ID")

    if not scholar_id:
        raise RuntimeError("Environment variable GOOGLE_SCHOLAR_ID is not set.")

    return scholar_id


def prepare_author_data(scholar_id: str) -> Dict[str, Any]:
    """
    Fetch and post-process author data.

    On success, adds an `updated` timestamp.
    """
    author = fetch_author_with_retries(scholar_id)
    author["updated"] = utc_now_iso()
    return author


def main() -> None:
    scholar_id = get_scholar_id_from_env()

    try:
        author = prepare_author_data(scholar_id)
        citedby = author.get("citedby", 0)

    except Exception as exc:
        # Soft-fail path: do not crash CI.
        log_error(f"Could not fetch Google Scholar data: {exc}")

        author = build_fallback_author(exc)
        citedby = 0

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    write_json(GS_DATA_PATH, author, indent=2)
    write_json(SHIELDSIO_PATH, build_shieldsio_data(citedby))


if __name__ == "__main__":
    main()
