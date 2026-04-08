import os
import sys
import time
import json
from datetime import datetime

from scholarly import scholarly


def fetch_author_with_retries(scholar_id: str,
                              max_tries: int = 10,
                              wait_seconds: int = 60):
    """
    Try to fetch Google Scholar author data multiple times.

    Raises the last exception if all attempts fail.
    """
    last_exc = None
    for attempt in range(1, max_tries + 1):
        try:
            print(f"[INFO] Fetching Google Scholar data (attempt: {attempt}/{max_tries})",
                  file=sys.stderr)
            author = scholarly.search_author_id(scholar_id)
            scholarly.fill(author, sections=["basics", "indices", "counts"])
            return author
        except Exception as e:
            last_exc = e
            print(f"[WARN] Attempt {attempt} failed: {e}", file=sys.stderr)
            if attempt < max_tries:
                print(f"[INFO] Waiting {wait_seconds} seconds before retry...",
                      file=sys.stderr)
                time.sleep(wait_seconds)

    # All attempts failed
    raise last_exc


def main() -> None:
    scholar_id = os.environ.get("GOOGLE_SCHOLAR_ID")
    if not scholar_id:
        # This is a configuration error; it's reasonable to fail hard here.
        raise RuntimeError("Environment variable GOOGLE_SCHOLAR_ID is not set.")

    try:
        author = fetch_author_with_retries(scholar_id)
        author["updated"] = datetime.utcnow().isoformat()
        citedby = author.get("citedby", 0)
    except Exception as e:
        # IMPORTANT: soft-fail path. We don't crash the CI, just log and
        # create a fallback JSON. If you prefer to fail the workflow,
        # just `raise` here instead.
        print("[ERROR] Could not fetch Google Scholar data:", e, file=sys.stderr)

        author = {
            "name": "UNKNOWN",
            "citedby": 0,
            "error": str(e),
            "updated": datetime.utcnow().isoformat(),
        }
        citedby = 0

    # Ensure results directory exists
    os.makedirs("results", exist_ok=True)

    # Save full author data
    with open("results/gs_data.json", "w", encoding="utf-8") as outfile:
        json.dump(author, outfile, ensure_ascii=False, indent=2)

    # Prepare Shields.io data
    shieldio_data = {
        "schemaVersion": 1,
        "label": "Google Scholar w/ citation:",
        "message": str(citedby),
    }
    with open("results/gs_data_shieldsio.json", "w", encoding="utf-8") as outfile:
        json.dump(shieldio_data, outfile, ensure_ascii=False)



main()
