from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
import html
import os
import re
import time
from typing import Any, Iterable

import requests

from core.config import Settings
from core.utils import compact_join, normalize_whitespace, now_utc, read_json, write_json

CROSSREF_API_URL = "https://api.crossref.org/works"
REQUEST_TIMEOUT_SECONDS = 30
MAX_ATTEMPTS = 5
BACKOFF_BASE_SECONDS = 1.5
MAX_BACKOFF_SECONDS = 30.0
RETRY_STATUS_CODES = frozenset({429, 500, 502, 503, 504})

# Crossref khong bao dam field nao cung ton tai: thu lan luot theo do tin cay.
PUBLISHED_DATE_FIELDS = ("issued", "published", "published-online", "published-print", "created")
UPDATED_DATE_FIELDS = ("deposited", "indexed", "created")

_JATS_TITLE_RE = re.compile(r"<jats:title>.*?</jats:title>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_LEADING_ABSTRACT_RE = re.compile(r"^abstract[:\s]*", re.IGNORECASE)
_LIST_FIELDS = ("authors", "categories")


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _clean_text(value: Any) -> str:
    """Bo tag markup, unescape entity va gom whitespace."""
    if value is None:
        return ""
    return normalize_whitespace(html.unescape(_TAG_RE.sub(" ", str(value))))


def _first_text(values: Any) -> str:
    """Nhieu field Crossref (title, container-title, subtitle) la list."""
    if isinstance(values, list):
        for value in values:
            text = _clean_text(value)
            if text:
                return text
        return ""
    return _clean_text(values)


def _clean_abstract(value: Any) -> str:
    """Abstract Crossref la JATS XML: bo heading <jats:title> roi strip tag."""
    if not value:
        return ""
    text = _clean_text(_JATS_TITLE_RE.sub(" ", str(value)))
    return _LEADING_ABSTRACT_RE.sub("", text).strip()


def _iso_date(container: Any) -> str:
    """`date-parts` co the chi co [year] hoac [year, month] -> pad ve ISO date."""
    if not isinstance(container, dict):
        return ""
    parts = container.get("date-parts") or []
    if not parts or not isinstance(parts[0], list):
        return ""
    numbers = [int(part) for part in parts[0] if isinstance(part, int)]
    if not numbers:
        return ""
    year = numbers[0]
    month = numbers[1] if len(numbers) > 1 else 1
    day = numbers[2] if len(numbers) > 2 else 1
    for candidate in ((year, month, day), (year, month, 1), (year, 1, 1)):
        try:
            return date(*candidate).isoformat()
        except ValueError:
            continue
    return ""


def _first_available_date(item: dict, fields: Iterable[str]) -> str:
    for field in fields:
        value = _iso_date(item.get(field))
        if value:
            return value
    return ""


def _parse_authors(raw_authors: Any) -> list[str]:
    """Author co the la nguoi (given/family) hoac to chuc (name)."""
    names: list[str] = []
    for author in raw_authors or []:
        if not isinstance(author, dict):
            continue
        full_name = compact_join([_clean_text(author.get("given")), _clean_text(author.get("family"))], " ")
        if not full_name:
            full_name = _clean_text(author.get("name"))
        if full_name and full_name not in names:
            names.append(full_name)
    return names


def _parse_categories(item: dict) -> list[str]:
    """`subject` thuong rong: fallback container-title roi type de field khong bi trong."""
    subjects = [_clean_text(subject) for subject in (item.get("subject") or [])]
    categories = [subject for subject in dict.fromkeys(subjects) if subject]
    if categories:
        return categories
    fallback = _first_text(item.get("container-title")) or _clean_text(item.get("type"))
    return [fallback] if fallback else []


def _pdf_url(item: dict) -> str:
    links = [link for link in (item.get("link") or []) if isinstance(link, dict)]
    for link in links:
        if str(link.get("content-type") or "").lower() == "application/pdf":
            return _clean_text(link.get("URL"))
    for link in links:
        if str(link.get("URL") or "").lower().endswith(".pdf"):
            return _clean_text(link.get("URL"))
    return ""


def _to_record(item: dict) -> PaperRecord | None:
    """Map mot Crossref item thanh PaperRecord; tra None neu thieu DOI hoac title."""
    doi = _clean_text(item.get("DOI")).lower()
    title = _first_text(item.get("title"))
    if not doi or not title:
        return None

    categories = _parse_categories(item)
    return PaperRecord(
        paper_id=doi,
        title=title,
        summary=_clean_abstract(item.get("abstract")),
        authors=_parse_authors(item.get("author")),
        categories=categories,
        primary_category=categories[0] if categories else "",
        published=_first_available_date(item, PUBLISHED_DATE_FIELDS),
        updated=_first_available_date(item, UPDATED_DATE_FIELDS),
        abs_url=_clean_text(item.get("URL")) or f"https://doi.org/{doi}",
        pdf_url=_pdf_url(item),
        comment=_first_text(item.get("subtitle")) or _first_text(item.get("container-title")),
    )


def _parse_items(items: Any) -> tuple[list[PaperRecord], dict[str, Any]]:
    """Parse items va tra ve them stats de ghi log thu thap (khong drop record am tham)."""
    records: list[PaperRecord] = []
    seen_ids: set[str] = set()
    stats = {
        "items_received": 0,
        "skipped_invalid_item": 0,
        "skipped_missing_doi_or_title": 0,
        "records_missing_abstract": 0,
        "records_missing_subject": 0,
        "records_missing_published": 0,
        "records_published_in_future": 0,
        "duplicate_doi": 0,
    }
    today = now_utc().date().isoformat()

    for item in items or []:
        stats["items_received"] += 1
        if not isinstance(item, dict):
            stats["skipped_invalid_item"] += 1
            continue

        record = _to_record(item)
        if record is None:
            stats["skipped_missing_doi_or_title"] += 1
            continue

        if not record.summary:
            stats["records_missing_abstract"] += 1
        if not item.get("subject"):
            stats["records_missing_subject"] += 1
        if not record.published:
            stats["records_missing_published"] += 1
        elif record.published > today:
            # Crossref co ban ghi da len lich xuat ban: bao cho cleaning biet, khong tu sua.
            stats["records_published_in_future"] += 1
        if record.paper_id in seen_ids:
            # Giu lai record trung DOI: dedupe la buoc cua cleaning, o day chi dem.
            stats["duplicate_doi"] += 1
        seen_ids.add(record.paper_id)
        records.append(record)

    stats["records_parsed"] = len(records)
    stats["unique_paper_ids"] = len(seen_ids)
    return records, stats


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload thanh list PaperRecord."""
    message = payload.get("message") if isinstance(payload, dict) else None
    items = message.get("items") if isinstance(message, dict) else None
    records, _ = _parse_items(items)
    return records


def _contact_email() -> str:
    return os.getenv("CROSSREF_MAILTO", "").strip()


def _user_agent() -> str:
    """Co contact info thi Crossref cho vao polite pool, it bi throttle hon."""
    base = "day10-data-observability-lab/0.1 (+https://api.crossref.org)"
    email = _contact_email()
    return f"{base} mailto:{email}" if email else base


def _build_params(settings: Settings) -> dict[str, Any]:
    params: dict[str, Any] = {
        "query.bibliographic": settings.source_query,
        "rows": settings.max_results,
        # Sort theo relevance: sort=issued keo ve so bao da len lich (ngay tuong lai)
        # va lech chu de so voi settings.source_query. Freshness da duoc bao bang filter.
        "sort": "relevance",
        "order": "desc",
    }
    if settings.source_filter:
        params["filter"] = settings.source_filter
    email = _contact_email()
    if email:
        params["mailto"] = email
    return params


def _retry_delay(response: requests.Response | None, attempt: int) -> float:
    if response is not None:
        try:
            return min(float(response.headers.get("Retry-After", "")), MAX_BACKOFF_SECONDS)
        except (TypeError, ValueError):
            pass
    return min(BACKOFF_BASE_SECONDS**attempt, MAX_BACKOFF_SECONDS)


def _fetch_payload(params: dict[str, Any]) -> dict[str, Any]:
    """Goi Crossref voi retry/backoff cho 429 va 5xx; loi khac thi fail nhanh."""
    headers = {"User-Agent": _user_agent(), "Accept": "application/json"}
    last_error: Exception | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        response: requests.Response | None = None
        try:
            response = requests.get(
                CROSSREF_API_URL,
                params=params,
                headers=headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            last_error = exc
        else:
            if response.status_code == 200:
                try:
                    return response.json()
                except ValueError as exc:
                    last_error = exc
            elif response.status_code in RETRY_STATUS_CODES:
                last_error = requests.HTTPError(f"Crossref returned HTTP {response.status_code}")
            else:
                response.raise_for_status()

        if attempt < MAX_ATTEMPTS:
            time.sleep(_retry_delay(response, attempt))

    raise RuntimeError(f"Crossref request failed after {MAX_ATTEMPTS} attempts: {last_error}") from last_error


def _relative_path(path: Path, settings: Settings) -> str:
    """Ghi path tuong doi vao artifact de khong lo duong dan may ca nhan."""
    try:
        return path.resolve().relative_to(settings.paths.project_dir).as_posix()
    except ValueError:
        return path.name


def _write_records(path: Path, records: list[PaperRecord], lineage: dict[str, Any]) -> None:
    write_json(path, {**lineage, "count": len(records), "records": [asdict(record) for record in records]})


def _write_ingest_log(settings: Settings, lineage: dict[str, Any], stats: dict[str, Any]) -> Path:
    log_path = settings.paths.raw_records_json.parent / "ingest_log.json"
    write_json(
        log_path,
        {
            **lineage,
            **stats,
            "artifacts": {
                "raw_api_response": _relative_path(settings.paths.raw_api_response, settings),
                "raw_records_json": _relative_path(settings.paths.raw_records_json, settings),
            },
        },
    )
    return log_path


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Goi Crossref, luu raw response, parse thanh records va ghi log thu thap."""
    params = _build_params(settings)
    fetched_at = now_utc().isoformat()
    payload = _fetch_payload(params)

    # Luu raw response truoc khi parse: day la diem khoi phuc cho buoc repair.
    write_json(settings.paths.raw_api_response, payload)

    message = payload.get("message") if isinstance(payload, dict) else None
    message = message if isinstance(message, dict) else {}
    records, stats = _parse_items(message.get("items"))

    lineage = {
        "fetched_at": fetched_at,
        "source": settings.source_api,
        "api_url": CROSSREF_API_URL,
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows_requested": settings.max_results,
        "total_results_reported": message.get("total-results"),
    }
    _write_records(settings.paths.raw_records_json, records, lineage)
    _write_ingest_log(settings, lineage, stats)
    return records


def _record_from_dict(item: dict) -> PaperRecord:
    values: dict[str, Any] = {}
    for field in PaperRecord.__dataclass_fields__:
        value = item.get(field)
        if field in _LIST_FIELDS:
            values[field] = [str(entry) for entry in (value or []) if str(entry).strip()]
        else:
            values[field] = str(value or "")
    return PaperRecord(**values)


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc raw snapshot va map lai thanh PaperRecord (dung cho baseline va repair)."""
    payload = read_json(path)
    if isinstance(payload, dict):
        raw_records = payload.get("records") or []
    else:
        raw_records = payload or []
    return [_record_from_dict(item) for item in raw_records if isinstance(item, dict)]
