from __future__ import annotations

import json
from typing import Any

import pandas as pd

from core.config import Settings


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """TODO(student): tao bo data quality checks.

    Pseudo-code:
    1. Check row count.
    2. Check `paper_id` not null va unique.
    3. Check `title` not null.
    4. Check do dai `summary`.
    5. Check freshness bang `age_days`.
    6. Ghi ket qua vao `data/quality/`.
    """
    row_count = len(df)
    
    paper_id_nulls = int(df['paper_id'].isnull().sum()) if 'paper_id' in df.columns else row_count
    paper_id_unique = df['paper_id'].is_unique if 'paper_id' in df.columns else False
    
    title_nulls = int(df['title'].isnull().sum()) if 'title' in df.columns else row_count
    
    summary_empty_or_null = 0
    if 'summary' in df.columns:
        summary_empty_or_null = int((df['summary'].isnull() | (df['summary'].str.len() == 0)).sum())
        
    stale_count = 0
    if 'age_days' in df.columns:
        stale_count = int((df['age_days'] > settings.freshness_threshold_days).sum())
        
    report = {
        "row_count": row_count,
        "paper_id_nulls": paper_id_nulls,
        "paper_id_is_unique": bool(paper_id_unique),
        "title_nulls": title_nulls,
        "summary_empty_or_null": summary_empty_or_null,
        "stale_count": stale_count,
        "passed": (paper_id_nulls == 0) and bool(paper_id_unique) and (title_nulls == 0)
    }
    
    quality_dir = settings.paths.quality_dir
    quality_dir.mkdir(parents=True, exist_ok=True)
    report_path = quality_dir / report_name
    
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """TODO(student): tong hop freshness report.

    Pseudo-code:
    1. Tim latest va oldest published date.
    2. Dem so dong stale.
    3. Tao payload:
       - latest_published
       - oldest_published
       - stale_rows
       - total_rows
       - is_fresh
    4. Ghi JSON report.
    """
    if df.empty:
        report = {
            "latest_published": None,
            "oldest_published": None,
            "stale_rows": 0,
            "total_rows": 0,
            "is_fresh": True
        }
    else:
        latest_published = df['published'].max() if 'published' in df.columns else None
        oldest_published = df['published'].min() if 'published' in df.columns else None
        
        stale_rows = 0
        if 'age_days' in df.columns:
            stale_rows = int((df['age_days'] > settings.freshness_threshold_days).sum())
            
        total_rows = len(df)
        is_fresh = stale_rows == 0
        
        report = {
            "latest_published": str(latest_published) if latest_published else None,
            "oldest_published": str(oldest_published) if oldest_published else None,
            "stale_rows": stale_rows,
            "total_rows": total_rows,
            "is_fresh": bool(is_fresh)
        }
    
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        
    return report
