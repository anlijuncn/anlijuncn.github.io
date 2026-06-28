#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup


BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "results"
GS_DATA_PATH = RESULTS_DIR / "gs_data.json"
SHIELDSIO_PATH = RESULTS_DIR / "gs_data_shieldsio.json"

DEFAULT_MAX_TRIES = 3
DEFAULT_WAIT_SECONDS = 10
DEFAULT_MAX_PUBLICATION_PAGES = 5
REQUEST_TIMEOUT_SECONDS = 20

SCHOLAR_PROFILE_URL = "https://scholar.google.com/citations"
SCHOLAR_SECTIONS = ["basics", "indices", "counts", "publications"]

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def utc_now_iso() -> str:
    """Return current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def log_info(message: str) -> None:
    """Print an info message to stderr."""
    print(f"[INFO] {message}", file=sys.stderr)


def log_warn(message: str) -> None:
    """Print a warning message to stderr."""
    print(f"[WARN] {message}", file=sys.stderr)


def log_error(message: str) -> None:
    """Print an error message to stderr."""
    print(f"[ERROR] {message}", file=sys.stderr)


def clean_text(text: str) -> str:
    """Normalize Scholar text by removing bidi marks and extra whitespace."""
    text = re.sub(r"[\u200e\u200f\u202a-\u202e]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_int(text: str) -> int:
    """Parse an integer from Scholar text such as '1,234' or an empty cell."""
    cleaned = re.sub(r"[^\d]", "", text or "")
    return int(cleaned) if cleaned else 0


def build_profile_url(scholar_id: str, *, cstart: int = 0) -> str:
    """Build a Google Scholar author profile URL."""
    params = {
        "user": scholar_id,
        "hl": "en",
        "view_op": "list_works",
        "sortby": "pubdate",
        "pagesize": "100",
    }

    if cstart:
        params["cstart"] = str(cstart)

    return f"{SCHOLAR_PROFILE_URL}?{urlencode(params)}"


def is_antibot_response(text: str) -> bool:
    """Return whether Google Scholar appears to have returned a challenge page."""
    lowered = text.lower()
    return (
        "unusual traffic" in lowered
        or "detected unusual traffic" in lowered
        or "sorry" in lowered and "google" in lowered and "captcha" in lowered
    )


def fetch_profile_page(
    client: httpx.Client,
    scholar_id: str,
    *,
    cstart: int = 0,
) -> BeautifulSoup:
    """Fetch one Google Scholar author profile page."""
    url = build_profile_url(scholar_id, cstart=cstart)
    response = client.get(url)
    response.raise_for_status()

    if is_antibot_response(response.text):
        raise RuntimeError("Google Scholar returned an anti-bot challenge.")

    soup = BeautifulSoup(response.text, "html.parser")

    if not soup.select_one("#gsc_prf_in"):
        raise RuntimeError("Could not find Google Scholar profile content.")

    return soup


def parse_author_profile(soup: BeautifulSoup) -> Dict[str, Any]:
    """Parse author metadata and metrics from the first Scholar profile page."""
    name_node = soup.select_one("#gsc_prf_in")

    if not name_node:
        raise RuntimeError("Could not parse author profile from Google Scholar response.")

    profile_lines = [
        clean_text(node.get_text(" ", strip=True))
        for node in soup.select("#gsc_prf_i .gsc_prf_il")
    ]
    interests = [
        clean_text(node.get_text(" ", strip=True))
        for node in soup.select("#gsc_prf_int a")
    ]
    profile_links = [
        {
            "text": clean_text(node.get_text(" ", strip=True)),
            "url": urljoin(SCHOLAR_PROFILE_URL, node.get("href", "")),
        }
        for node in soup.select("#gsc_prf_i a[href]")
    ]

    author: Dict[str, Any] = {
        "container_type": "Author",
        "filled": SCHOLAR_SECTIONS,
        "source": "google_scholar_html",
        "name": clean_text(name_node.get_text(" ", strip=True)),
        "affiliation": profile_lines[0] if profile_lines else "",
        "email_domain": "",
        "interests": interests,
        "profile_links": profile_links,
    }

    for line in profile_lines:
        lowered = line.lower()
        if "verified email at" in lowered:
            author["email_domain"] = clean_text(
                re.sub(r"(?i).*verified email at\s+", "", line)
            )

    stats_map = {
        "citations": ("citedby", "citedby5y"),
        "h-index": ("hindex", "hindex5y"),
        "i10-index": ("i10index", "i10index5y"),
    }

    for row in soup.select("#gsc_rsb_st tbody tr"):
        label_node = row.select_one(".gsc_rsb_sc1")
        value_nodes = row.select(".gsc_rsb_std")

        if not label_node or len(value_nodes) < 2:
            continue

        label = clean_text(label_node.get_text(" ", strip=True)).lower()
        keys = stats_map.get(label)

        if not keys:
            continue

        author[keys[0]] = parse_int(value_nodes[0].get_text(" ", strip=True))
        author[keys[1]] = parse_int(value_nodes[1].get_text(" ", strip=True))

    years = [
        clean_text(node.get_text(" ", strip=True))
        for node in soup.select(".gsc_g_t")
    ]
    counts = [
        parse_int(node.get_text(" ", strip=True))
        for node in soup.select(".gsc_g_al")
    ]

    author["cites_per_year"] = {
        year: count for year, count in zip(years, counts) if year
    }

    for key in ["citedby", "citedby5y", "hindex", "hindex5y", "i10index", "i10index5y"]:
        author.setdefault(key, 0)

    return author


def extract_publication_id(href: str) -> Optional[str]:
    """Extract Scholar's citation_for_view id from a publication URL."""
    query = parse_qs(urlparse(href).query)
    values = query.get("citation_for_view")
    return values[0] if values else None


def parse_publications(soup: BeautifulSoup) -> Dict[str, Dict[str, Any]]:
    """Parse publication citation counts from a Scholar profile page."""
    publications: Dict[str, Dict[str, Any]] = {}

    for row in soup.select("tr.gsc_a_tr"):
        title_node = row.select_one(".gsc_a_at[href]")

        if not title_node:
            continue

        publication_id = extract_publication_id(title_node["href"])

        if not publication_id:
            continue

        gray_nodes = row.select(".gs_gray")
        citation_node = row.select_one(".gsc_a_ac")
        year_node = row.select_one(".gsc_a_y .gsc_a_h")
        title = clean_text(title_node.get_text(" ", strip=True))

        publication: Dict[str, Any] = {
            "author_pub_id": publication_id,
            "num_citations": parse_int(
                citation_node.get_text(" ", strip=True) if citation_node else ""
            ),
            "bib": {
                "title": title,
                "author": clean_text(gray_nodes[0].get_text(" ", strip=True))
                if len(gray_nodes) >= 1
                else "",
                "venue": clean_text(gray_nodes[1].get_text(" ", strip=True))
                if len(gray_nodes) >= 2
                else "",
                "pub_year": clean_text(year_node.get_text(" ", strip=True))
                if year_node
                else "",
            },
            "filled": False,
            "source": urljoin(SCHOLAR_PROFILE_URL, title_node["href"]),
        }

        publications[publication_id] = publication

    return publications


def has_more_publications(soup: BeautifulSoup) -> bool:
    """Return whether the Scholar profile exposes a next publication page."""
    button = soup.select_one("#gsc_bpf_more")

    if not button:
        return False

    classes = button.get("class", [])
    return not button.has_attr("disabled") and "gs_dis" not in classes


def fetch_author_once(
    scholar_id: str,
    *,
    max_publication_pages: int = DEFAULT_MAX_PUBLICATION_PAGES,
) -> Dict[str, Any]:
    """
    Fetch Google Scholar author data once.

    Parameters
    ----------
    scholar_id:
        Google Scholar author ID.

    Returns
    -------
    dict
        Parsed author dictionary from the Google Scholar profile page.
    """
    with httpx.Client(
        headers=REQUEST_HEADERS,
        follow_redirects=True,
        timeout=REQUEST_TIMEOUT_SECONDS,
    ) as client:
        soup = fetch_profile_page(client, scholar_id)
        author = parse_author_profile(soup)
        publications = parse_publications(soup)

        for page_index in range(1, max_publication_pages):
            if not has_more_publications(soup):
                break

            cstart = page_index * 100
            log_info(f"Fetching publication page {page_index + 1}")

            try:
                soup = fetch_profile_page(client, scholar_id, cstart=cstart)
            except Exception as exc:
                log_warn(f"Could not fetch publication page {page_index + 1}: {exc}")
                break

            page_publications = parse_publications(soup)

            if not page_publications:
                break

            publications.update(page_publications)

    author["publications"] = publications
    return author


def fetch_author_with_retries(
    scholar_id: str,
    max_tries: int = DEFAULT_MAX_TRIES,
    wait_seconds: int = DEFAULT_WAIT_SECONDS,
    max_publication_pages: int = DEFAULT_MAX_PUBLICATION_PAGES,
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
            return fetch_author_once(
                scholar_id,
                max_publication_pages=max_publication_pages,
            )

        except Exception as exc:
            last_exc = exc
            log_warn(f"Attempt {attempt} failed: {exc}")

            if attempt < max_tries:
                log_info(f"Waiting {wait_seconds} seconds before retry...")
                time.sleep(wait_seconds)

    if last_exc is not None:
        raise last_exc

    raise RuntimeError("Failed to fetch Google Scholar data for unknown reason.")


def read_json(path: Path) -> Optional[Dict[str, Any]]:
    """Read a JSON file if it exists and is valid."""
    if not path.exists():
        return None

    try:
        with path.open("r", encoding="utf-8") as infile:
            data = json.load(infile)
    except (OSError, json.JSONDecodeError) as exc:
        log_warn(f"Could not read previous JSON data from {path}: {exc}")
        return None

    return data if isinstance(data, dict) else None


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


def get_int_env(name: str, default: int) -> int:
    """Read a positive integer from the environment."""
    raw_value = os.environ.get(name)

    if not raw_value:
        return default

    try:
        value = int(raw_value)
    except ValueError:
        log_warn(f"Ignoring invalid {name}={raw_value!r}; using {default}.")
        return default

    return value if value > 0 else default


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
    author = fetch_author_with_retries(
        scholar_id,
        max_tries=get_int_env("GOOGLE_SCHOLAR_MAX_TRIES", DEFAULT_MAX_TRIES),
        wait_seconds=get_int_env("GOOGLE_SCHOLAR_WAIT_SECONDS", DEFAULT_WAIT_SECONDS),
        max_publication_pages=get_int_env(
            "GOOGLE_SCHOLAR_MAX_PUBLICATION_PAGES",
            DEFAULT_MAX_PUBLICATION_PAGES,
        ),
    )
    author["updated"] = utc_now_iso()
    return author


def main() -> None:
    scholar_id = get_scholar_id_from_env()

    try:
        author = prepare_author_data(scholar_id)
        citedby = parse_int(str(author.get("citedby", 0)))

    except Exception as exc:
        log_error(f"Could not fetch Google Scholar data: {exc}")
        previous_author = read_json(GS_DATA_PATH)

        if not previous_author:
            raise SystemExit(1) from exc

        log_warn("Using previous Google Scholar JSON data instead.")
        previous_author["stale"] = True
        previous_author["stale_reason"] = str(exc)
        previous_author["stale_updated"] = utc_now_iso()
        author = previous_author
        citedby = parse_int(str(author.get("citedby", 0)))

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    write_json(GS_DATA_PATH, author, indent=2)
    write_json(SHIELDSIO_PATH, build_shieldsio_data(citedby))


if __name__ == "__main__":
    main()
