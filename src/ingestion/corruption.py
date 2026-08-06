from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import normalize_whitespace, read_json, write_json


CORRUPTION_FRACTION = 0.15
RANDOM_SEED = 42
STALE_DATE = "2000-01-01"
NOISE_TEXT = " ".join(
    [
        "ZXQV_CORRUPTED irrelevant random tokens malformed placeholder content",
        "unrelated football weather cooking cryptocurrency advertisement noise",
    ]
    * 12
)


def _as_text(value: Any) -> str:
    try:
        if value is None or pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value)


def _operation_size(row_count: int) -> int:
    return min(row_count, max(1, round(row_count * CORRUPTION_FRACTION)))


def _embedding_text(row: pd.Series) -> str:
    fields = (
        ("Title", "title"),
        ("Authors", "authors_joined"),
        ("Categories", "categories_joined"),
        ("Published", "published"),
        ("Summary", "summary"),
    )
    parts = [f"{label}: {_as_text(row.get(column))}" for label, column in fields if _as_text(row.get(column))]
    return normalize_whitespace(" | ".join(parts))


def _load_frozen_doc_ids(output_log_path: Path) -> tuple[Path, list[str]]:
    data_dir = output_log_path.parent.parent
    test_set_path = data_dir / "eval" / "test_set.json"
    if not test_set_path.exists():
        return test_set_path, []

    payload = read_json(test_set_path)
    if not isinstance(payload, list):
        raise ValueError(f"Frozen test set must be a list: {test_set_path}")

    frozen_ids: list[str] = []
    for sample in payload:
        if not isinstance(sample, dict):
            continue
        for paper_id in sample.get("ground_truth_doc_ids", []):
            normalized_id = _as_text(paper_id).strip().lower()
            if normalized_id and normalized_id not in frozen_ids:
                frozen_ids.append(normalized_id)
    return test_set_path, frozen_ids


def _matching_frozen_ids(df: pd.DataFrame, frozen_ids: list[str]) -> list[str]:
    available = set(df["paper_id"].map(_as_text).str.strip().str.lower())
    return [paper_id for paper_id in frozen_ids if paper_id in available]


def _select_indices(
    df: pd.DataFrame,
    count: int,
    seed_offset: int,
    excluded: set[int],
    priority_paper_id: str | None = None,
    reserved_paper_ids: set[str] | None = None,
) -> list[int]:
    normalized_ids = df["paper_id"].map(_as_text).str.strip().str.lower()
    reserved = reserved_paper_ids or set()
    candidates = [
        int(index)
        for index in df.index
        if int(index) not in excluded
        and (
            normalized_ids.at[index] not in reserved
            or normalized_ids.at[index] == priority_paper_id
        )
    ]
    selected: list[int] = []

    if priority_paper_id:
        priority_indices = [
            int(index)
            for index in df.index[normalized_ids == priority_paper_id].tolist()
            if int(index) in candidates
        ]
        if priority_indices:
            selected.append(priority_indices[0])

    remaining = [index for index in candidates if index not in selected]
    sample_size = min(max(0, count - len(selected)), len(remaining))
    if sample_size:
        sampled = (
            pd.Series(remaining)
            .sample(n=sample_size, random_state=RANDOM_SEED + seed_offset)
            .astype(int)
            .tolist()
        )
        selected.extend(sampled)
    return selected


def _operation_log(
    operation_type: str,
    records: list[dict[str, Any]],
    frozen_ids: set[str],
    parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    affected_ids = {
        _as_text(record.get("paper_id")).strip().lower()
        for record in records
        if record.get("paper_id")
    }
    frozen_overlap = sorted(affected_ids & frozen_ids)
    payload: dict[str, Any] = {
        "type": operation_type,
        "count": len(records),
        "affects_frozen_test_set": bool(frozen_overlap),
        "frozen_paper_ids": frozen_overlap,
        "records": records,
    }
    if parameters:
        payload["parameters"] = parameters
    return payload


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Create deterministic corruptions that overlap the frozen evaluation set."""
    required_columns = {"paper_id", "title", "summary", "published", "text_for_embedding"}
    missing_columns = sorted(required_columns - set(df.columns))
    if missing_columns:
        raise ValueError(f"Cannot corrupt dataframe; missing columns: {', '.join(missing_columns)}")
    if df.empty:
        raise ValueError("Cannot corrupt an empty dataframe.")

    log_path = Path(output_log_path)
    test_set_path, frozen_doc_ids = _load_frozen_doc_ids(log_path)
    matched_frozen_ids = _matching_frozen_ids(df, frozen_doc_ids)
    if test_set_path.exists() and not matched_frozen_ids:
        raise ValueError(
            "No frozen test document exists in the clean dataframe; "
            "controlled corruption cannot satisfy the C4 overlap requirement."
        )

    corrupted = df.copy(deep=True).reset_index(drop=True)
    for column in ("paper_id", "title", "summary", "published", "text_for_embedding"):
        corrupted[column] = corrupted[column].map(_as_text)

    input_rows = len(corrupted)
    operation_count = _operation_size(input_rows)
    frozen_id_set = set(frozen_doc_ids)
    operations: list[dict[str, Any]] = []

    # Removing one frozen document guarantees a measurable retrieval miss.
    drop_target_id = (
        matched_frozen_ids[0]
        if matched_frozen_ids
        else _as_text(corrupted.iloc[0]["paper_id"]).strip().lower()
    )
    normalized_ids = corrupted["paper_id"].str.strip().str.lower()
    drop_index = int(corrupted.index[normalized_ids == drop_target_id][0])
    dropped_row = corrupted.loc[drop_index]
    drop_records = [
        {
            "paper_id": _as_text(dropped_row["paper_id"]),
            "title": _as_text(dropped_row["title"]),
            "published": _as_text(dropped_row["published"]),
        }
    ]
    operations.append(
        _operation_log(
            "drop_frozen_document",
            drop_records,
            frozen_id_set,
            {"reason": "force a retrieval miss on the frozen evaluation set"},
        )
    )
    corrupted = corrupted.drop(index=drop_index).reset_index(drop=True)

    remaining_frozen_ids = _matching_frozen_ids(corrupted, frozen_doc_ids)
    used_indices: set[int] = set()

    blank_priority = remaining_frozen_ids[0] if remaining_frozen_ids else None
    blank_indices = _select_indices(
        corrupted,
        operation_count,
        seed_offset=1,
        excluded=used_indices,
        priority_paper_id=blank_priority,
        reserved_paper_ids=set(remaining_frozen_ids[1:]),
    )
    blank_records: list[dict[str, Any]] = []
    for index in blank_indices:
        original_summary = _as_text(corrupted.at[index, "summary"])
        blank_records.append(
            {
                "paper_id": _as_text(corrupted.at[index, "paper_id"]),
                "before_summary_chars": len(original_summary),
                "after_summary_chars": 0,
            }
        )
        corrupted.at[index, "summary"] = ""
    used_indices.update(blank_indices)
    operations.append(_operation_log("blank_summary", blank_records, frozen_id_set))

    stale_priority = remaining_frozen_ids[1] if len(remaining_frozen_ids) > 1 else blank_priority
    stale_indices = _select_indices(
        corrupted,
        operation_count,
        seed_offset=2,
        excluded=used_indices,
        priority_paper_id=stale_priority,
        reserved_paper_ids=set(remaining_frozen_ids[2:]),
    )
    stale_records: list[dict[str, Any]] = []
    stale_timestamp = pd.Timestamp(STALE_DATE)
    for index in stale_indices:
        original_value = _as_text(corrupted.at[index, "published"])
        original_date = pd.to_datetime(original_value, errors="coerce")
        corrupted.at[index, "published"] = STALE_DATE
        if "age_days" in corrupted.columns:
            original_age = pd.to_numeric(corrupted.at[index, "age_days"], errors="coerce")
            if not pd.isna(original_age) and not pd.isna(original_date):
                additional_days = (original_date.normalize() - stale_timestamp).days
                corrupted.at[index, "age_days"] = max(0, int(original_age) + additional_days)
        stale_records.append(
            {
                "paper_id": _as_text(corrupted.at[index, "paper_id"]),
                "before_published": original_value,
                "after_published": STALE_DATE,
            }
        )
    used_indices.update(stale_indices)
    operations.append(
        _operation_log(
            "stale_date",
            stale_records,
            frozen_id_set,
            {"forced_date": STALE_DATE},
        )
    )

    if "summary_chars" in corrupted.columns:
        corrupted["summary_chars"] = corrupted["summary"].str.len()
    corrupted["text_for_embedding"] = corrupted.apply(_embedding_text, axis=1)

    noise_priority = remaining_frozen_ids[2] if len(remaining_frozen_ids) > 2 else blank_priority
    noise_indices = _select_indices(
        corrupted,
        operation_count,
        seed_offset=3,
        excluded=used_indices,
        priority_paper_id=noise_priority,
    )
    noise_records: list[dict[str, Any]] = []
    for index in noise_indices:
        original_text = _as_text(corrupted.at[index, "text_for_embedding"])
        corrupted.at[index, "text_for_embedding"] = f"{NOISE_TEXT} | {original_text}"
        noise_records.append(
            {
                "paper_id": _as_text(corrupted.at[index, "paper_id"]),
                "before_text_chars": len(original_text),
                "after_text_chars": len(_as_text(corrupted.at[index, "text_for_embedding"])),
            }
        )
    operations.append(
        _operation_log(
            "add_embedding_noise",
            noise_records,
            frozen_id_set,
            {"noise_prefix": NOISE_TEXT},
        )
    )

    duplicate_priority = remaining_frozen_ids[-1] if remaining_frozen_ids else None
    duplicate_indices = _select_indices(
        corrupted,
        operation_count,
        seed_offset=4,
        excluded=set(),
        priority_paper_id=duplicate_priority,
    )
    duplicate_rows = corrupted.loc[duplicate_indices].copy(deep=True)
    duplicate_records = [
        {
            "paper_id": _as_text(row["paper_id"]),
            "title": _as_text(row["title"]),
            "id_preserved": True,
        }
        for _, row in duplicate_rows.iterrows()
    ]
    operations.append(_operation_log("duplicate_rows", duplicate_records, frozen_id_set))
    corrupted = pd.concat([corrupted, duplicate_rows], ignore_index=True)

    affected_frozen_ids = sorted(
        {
            paper_id
            for operation in operations
            for paper_id in operation["frozen_paper_ids"]
        }
    )
    if frozen_doc_ids and not affected_frozen_ids:
        raise RuntimeError("Corruption did not overlap any frozen test document.")

    log_payload = {
        "input_rows": input_rows,
        "output_rows": len(corrupted),
        "net_row_change": len(corrupted) - input_rows,
        "random_seed": RANDOM_SEED,
        "corruption_fraction": CORRUPTION_FRACTION,
        "frozen_test_set": {
            "path": test_set_path.as_posix(),
            "loaded": test_set_path.exists(),
            "ground_truth_doc_ids": frozen_doc_ids,
            "matched_clean_doc_ids": matched_frozen_ids,
            "corrupted_overlap_doc_ids": affected_frozen_ids,
            "overlap_count": len(affected_frozen_ids),
        },
        "operations": operations,
    }
    write_json(log_path, log_payload)
    return corrupted
