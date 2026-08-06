from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any
import html
import re

import pandas as pd

from core.config import Settings
from core.utils import compact_join, normalize_whitespace, now_utc, write_csv, write_json
from ingestion.crossref import PaperRecord

TEXT_COLUMNS = ("title", "summary", "primary_category", "abs_url", "pdf_url", "comment")
LIST_COLUMNS = ("authors", "categories")
EMBEDDING_FIELDS = (
    ("Title", "title"),
    ("Authors", "authors_joined"),
    ("Categories", "categories_joined"),
    ("Published", "published"),
    ("Summary", "summary"),
)
MIN_SUMMARY_CHARS = 100

# Chroma metadata chi nhan str/int/float/bool: cac cot nay khong duoc chua NaN.
METADATA_TEXT_COLUMNS = (
    "paper_id",
    "title",
    "summary",
    "published",
    "abs_url",
    "pdf_url",
    "authors_joined",
    "categories_joined",
    "text_for_embedding",
)
CLEAN_COLUMN_ORDER = (
    "paper_id",
    "title",
    "summary",
    "authors",
    "categories",
    "primary_category",
    "published",
    "updated",
    "age_days",
    "abs_url",
    "pdf_url",
    "comment",
    "authors_joined",
    "categories_joined",
    "summary_chars",
    "text_for_embedding",
)

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_markup(value: str) -> str:
    """Bo the XML/HTML (<jats:p>, <b>) va unescape entity truoc khi gom whitespace."""
    return normalize_whitespace(_TAG_RE.sub(" ", html.unescape(str(value))))


def _normalize_text(df: pd.DataFrame) -> pd.DataFrame:
    df["paper_id"] = df["paper_id"].fillna("").astype(str).str.strip().str.lower()

    for column in TEXT_COLUMNS:
        df[column] = df[column].fillna("").map(_strip_markup)

    for column in LIST_COLUMNS:
        df[column] = df[column].map(
            lambda items: [_strip_markup(item) for item in (items or []) if str(item).strip()]
        )
    return df


def _parse_dates(df: pd.DataFrame, run_date: datetime) -> pd.DataFrame:
    run_timestamp = pd.Timestamp(run_date)
    if run_timestamp.tz is None:
        run_timestamp = run_timestamp.tz_localize("UTC")

    published = pd.to_datetime(df["published"], utc=True, errors="coerce")
    updated = pd.to_datetime(df["updated"], utc=True, errors="coerce")

    df["published"] = published.dt.strftime("%Y-%m-%d").fillna("")
    df["updated"] = updated.dt.strftime("%Y-%m-%d").fillna("")
    df["published_ts"] = published
    df["age_days"] = (run_timestamp - published).dt.days.clip(lower=0)
    return df


def _add_helper_columns(df: pd.DataFrame) -> pd.DataFrame:
    df["authors_joined"] = df["authors"].map(compact_join)
    df["categories_joined"] = df["categories"].map(compact_join)
    df["summary_chars"] = df["summary"].str.len()
    return df


def _filter_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    log: dict[str, int] = {"rows_in": len(df)}

    reasons = {
        "dropped_missing_paper_id": df["paper_id"] == "",
        "dropped_missing_title": df["title"] == "",
        "dropped_missing_published": df["published"] == "",
        "dropped_summary_too_short": df["summary_chars"] < MIN_SUMMARY_CHARS,
    }

    drop_mask = pd.Series(False, index=df.index)
    for reason, mask in reasons.items():
        log[reason] = int((mask & ~drop_mask).sum())
        drop_mask = drop_mask | mask

    kept = df.loc[~drop_mask].copy()

    before_dedupe = len(kept)
    kept = kept.drop_duplicates(subset="paper_id", keep="first")
    log["dropped_duplicate_paper_id"] = before_dedupe - len(kept)
    log["rows_out"] = len(kept)
    return kept, log


def _build_text_for_embedding(df: pd.DataFrame) -> pd.DataFrame:
    def compose(row: pd.Series) -> str:
        return " | ".join(f"{label}: {row[column]}" for label, column in EMBEDDING_FIELDS if row[column])

    df["text_for_embedding"] = df.apply(compose, axis=1)
    return df


def _finalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("published_ts", ascending=False, kind="stable")
    df = df.drop(columns=["published_ts"])

    df["age_days"] = df["age_days"].fillna(0).astype(int)
    df["summary_chars"] = df["summary_chars"].fillna(0).astype(int)
    for column in METADATA_TEXT_COLUMNS:
        df[column] = df[column].fillna("").astype(str)

    return df[list(CLEAN_COLUMN_ORDER)].reset_index(drop=True)


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    if not records:
        raise ValueError("No raw records to clean.")

    df = pd.DataFrame([asdict(record) for record in records])
    df = _normalize_text(df)
    df = _parse_dates(df, run_date)
    df = _add_helper_columns(df)
    df, log = _filter_rows(df)

    if df.empty:
        raise ValueError(f"All records were filtered out during cleaning: {log}")

    df = _build_text_for_embedding(df)
    df = _finalize(df)
    df.attrs["cleaning_log"] = log
    return df


def save_clean_dataset(
    df: pd.DataFrame,
    settings: Settings,
    csv_path: Path | None = None,
    json_path: Path | None = None,
) -> dict[str, Any]:
    """Ghi clean CSV/JSON va cleaning log. Path mac dinh la baseline, TV4 truyen path khac
    khi luu corrupted/repaired dataset."""
    csv_path = csv_path or settings.paths.clean_csv
    json_path = json_path or settings.paths.clean_json
    log_path = json_path.with_name(f"{json_path.stem}_log.json")

    write_csv(df, csv_path)
    write_json(json_path, df.to_dict(orient="records"))

    def relative(path: Path) -> str:
        try:
            return path.resolve().relative_to(settings.paths.project_dir).as_posix()
        except ValueError:
            return path.name

    log = {
        "cleaned_at": now_utc().isoformat(),
        **df.attrs.get("cleaning_log", {}),
        "min_summary_chars": MIN_SUMMARY_CHARS,
        "columns": list(df.columns),
        "artifacts": {
            "clean_csv": relative(csv_path),
            "clean_json": relative(json_path),
        },
    }
    write_json(log_path, log)
    return log
 