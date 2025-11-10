thonimport csv
import json
import logging
from pathlib import Path
from typing import Iterable, List, Mapping

import openpyxl
from openpyxl.workbook import Workbook
from xml.etree.ElementTree import Element, SubElement, ElementTree

logger = logging.getLogger(__name__)

Record = Mapping[str, object]

def _ensure_parent_dir(path: Path) -> None:
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

def _to_list(records: Iterable[Record]) -> List[Record]:
    return list(records)

def export_json(records: Iterable[Record], output_path: Path) -> None:
    data = _to_list(records)
    _ensure_parent_dir(output_path)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info("Exported %d records to JSON at %s", len(data), output_path)

def export_csv(records: Iterable[Record], output_path: Path) -> None:
    data = _to_list(records)
    if not data:
        logger.warning("No records to export to CSV.")
        return

    fieldnames = list({k for rec in data for k in rec.keys()})

    _ensure_parent_dir(output_path)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rec in data:
            writer.writerow({k: rec.get(k, "") for k in fieldnames})

    logger.info("Exported %d records to CSV at %s", len(data), output_path)

def export_excel(records: Iterable[Record], output_path: Path) -> None:
    data = _to_list(records)
    if not data:
        logger.warning("No records to export to Excel.")
        return

    fieldnames = list({k for rec in data for k in rec.keys()})
    wb: Workbook = openpyxl.Workbook()
    ws = wb.active
    ws.title = "LinkedIn Companies"

    # Header
    ws.append(fieldnames)

    # Rows
    for rec in data:
        ws.append([rec.get(k, "") for k in fieldnames])

    _ensure_parent_dir(output_path)
    wb.save(output_path)
    logger.info("Exported %d records to Excel at %s", len(data), output_path)

def export_xml(records: Iterable[Record], output_path: Path) -> None:
    data = _to_list(records)
    root = Element("companies")

    for rec in data:
        company_el = SubElement(root, "company")
        for key, value in rec.items():
            child = SubElement(company_el, key)
            child.text = "" if value is None else str(value)

    tree = ElementTree(root)
    _ensure_parent_dir(output_path)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    logger.info("Exported %d records to XML at %s", len(data), output_path)

def export_rss(records: Iterable[Record], output_path: Path) -> None:
    data = _to_list(records)

    rss = Element("rss")
    rss.set("version", "2.0")
    channel = SubElement(rss, "channel")

    title_el = SubElement(channel, "title")
    title_el.text = "LinkedIn Company URL Feed"

    link_el = SubElement(channel, "link")
    link_el.text = "https://www.linkedin.com/"

    description_el = SubElement(channel, "description")
    description_el.text = "Feed of LinkedIn company URLs discovered by the scraper."

    for rec in data:
        item = SubElement(channel, "item")

        item_title = SubElement(item, "title")
        item_title.text = str(rec.get("companyName", ""))

        link = SubElement(item, "link")
        link.text = str(rec.get("linkedinUrl", ""))

        desc = SubElement(item, "description")
        desc.text = str(rec.get("resultTitle", ""))

        pub_date = SubElement(item, "pubDate")
        pub_date.text = str(rec.get("timestamp", ""))

    tree = ElementTree(rss)
    _ensure_parent_dir(output_path)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    logger.info("Exported %d records to RSS at %s", len(data), output_path)

def export_data(
    records: Iterable[Record],
    output_path: Path,
    output_format: str,
) -> None:
    fmt = output_format.lower()
    if fmt == "json":
        export_json(records, output_path)
    elif fmt == "csv":
        export_csv(records, output_path)
    elif fmt == "excel":
        export_excel(records, output_path)
    elif fmt == "xml":
        export_xml(records, output_path)
    elif fmt == "rss":
        export_rss(records, output_path)
    else:
        raise ValueError(f"Unsupported output format: {output_format}")