thonimport argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Ensure project root is on sys.path so imports work when running `python src/main.py`
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from extractors.search_engine_utils import (  # type: ignore  # noqa: E402
    SearchResult,
    build_search_query,
    search_company_results,
)
from extractors.linkedin_url_parser import (  # type: ignore  # noqa: E402
    select_best_linkedin_company_url,
)
from outputs.data_exporter import (  # type: ignore  # noqa: E402
    export_data,
)

DEFAULT_SETTINGS_PATH = PROJECT_ROOT / "src" / "config" / "settings.example.json"

def setup_logging(verbosity: int) -> None:
    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

def load_settings(path: Path) -> Dict[str, Any]:
    if not path.exists():
        logging.warning("Settings file not found at %s. Using built-in defaults.", path)
        return {
            "search_engine": "duckduckgo",
            "results_per_query": 10,
            "request_timeout": 10,
            "user_agent": "LinkedInCompanyFinder/1.0",
            "delay_between_requests": 1.0,
        }

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        logging.info("Loaded settings from %s", path)
        return data
    except json.JSONDecodeError as exc:
        logging.error("Invalid JSON in settings file %s: %s", path, exc)
        raise
    except OSError as exc:
        logging.error("Could not read settings file %s: %s", path, exc)
        raise

def read_companies(input_path: Path) -> List[str]:
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    companies: List[str] = []
    with input_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            companies.append(line)

    if not companies:
        logging.warning("No companies found in %s", input_path)
    else:
        logging.info("Loaded %d companies from %s", len(companies), input_path)

    return companies

def build_record(
    company_name: str,
    search_query: str,
    best_result: SearchResult | None,
    linkedin_url: str | None,
) -> Dict[str, Any]:
    timestamp = datetime.now(timezone.utc).isoformat()

    return {
        "companyName": company_name,
        "searchQuery": search_query,
        "resultTitle": best_result.title if best_result else None,
        "linkedinUrl": linkedin_url,
        "timestamp": timestamp,
    }

def process_companies(
    companies: List[str],
    settings: Dict[str, Any],
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

    delay = float(settings.get("delay_between_requests", 1.0))
    for idx, company in enumerate(companies, start=1):
        logger = logging.getLogger("processor")
        logger.info("Processing (%d/%d): %s", idx, len(companies), company)

        search_query = build_search_query(company)
        search_results = search_company_results(company, settings)

        best_url, best_result = select_best_linkedin_company_url(
            search_results, company
        )

        if best_url:
            logger.info("Found LinkedIn URL for %s: %s", company, best_url)
        else:
            logger.warning("No LinkedIn URL found for %s", company)

        record = build_record(company, search_query, best_result, best_url)
        results.append(record)

        if idx != len(companies):
            time.sleep(delay)

    return results

def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="LinkedIn Company URL - Mass Profile Finder",
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default=str(PROJECT_ROOT / "data" / "companies_input.txt"),
        help="Path to the input text file containing company names (one per line).",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=str(PROJECT_ROOT / "data" / "sample_output.json"),
        help="Path to the output file that will contain scraped results.",
    )
    parser.add_argument(
        "--format",
        "-f",
        dest="output_format",
        type=str,
        default="json",
        choices=["json", "csv", "excel", "xml", "rss"],
        help="Output format for the results.",
    )
    parser.add_argument(
        "--settings",
        "-s",
        type=str,
        default=str(DEFAULT_SETTINGS_PATH),
        help="Path to settings JSON file.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Increase logging verbosity (-v, -vv).",
    )
    return parser.parse_args(argv)

def main(argv: List[str] | None = None) -> None:
    args = parse_args(argv)
    setup_logging(args.verbose)

    try:
        settings = load_settings(Path(args.settings))
        companies = read_companies(Path(args.input))
        if not companies:
            logging.error("No companies to process. Exiting.")
            return

        records = process_companies(companies, settings)
        if not records:
            logging.error("No records were produced. Exiting.")
            return

        output_path = Path(args.output)
        export_data(records, output_path, args.output_format)
        logging.info(
            "Successfully exported %d records to %s (%s)",
            len(records),
            output_path,
            args.output_format,
        )
    except Exception as exc:  # pylint: disable=broad-except
        logging.getLogger("main").exception("Fatal error: %s", exc)
        raise SystemExit(1) from exc

if __name__ == "__main__":
    main()