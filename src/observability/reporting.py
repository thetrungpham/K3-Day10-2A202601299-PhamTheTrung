from __future__ import annotations

import json
from typing import Any


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """TODO(student): viet markdown report cho baseline phase.

    Pseudo-code:
    1. Gom source summary.
    2. In metrics retrieval/evaluation.
    3. In data quality va freshness.
    4. Ghi markdown vao report_path.
    """
    lines = [
        "# Phase 1: Baseline Report",
        "",
        "## 1. Source Summary",
        "```json",
        json.dumps(source_summary, indent=2) if source_summary else "{}",
        "```",
        "",
        "## 2. Evaluation Metrics",
        "```json",
        json.dumps(metrics, indent=2) if metrics else "{}",
        "```",
        "",
        "## 3. Data Quality",
        "```json",
        json.dumps(quality, indent=2) if quality else "{}",
        "```",
        "",
        "## 4. Freshness",
        "```json",
        json.dumps(freshness, indent=2) if freshness else "{}",
        "```",
        ""
    ]
    
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """TODO(student): viet markdown report so sanh baseline/corrupted/repaired."""
    lines = [
        "# Phase 2: Corruption and Repair Comparison",
        "",
        "## 1. Metrics Comparison",
        "### Baseline",
        "```json",
        json.dumps(baseline_metrics, indent=2) if baseline_metrics else "{}",
        "```",
        "### Corrupted",
        "```json",
        json.dumps(corrupted_metrics, indent=2) if corrupted_metrics else "{}",
        "```",
        "### Repaired",
        "```json",
        json.dumps(repaired_metrics, indent=2) if repaired_metrics else "{}",
        "```",
        "",
        "## 2. Quality Comparison",
        "### Corrupted",
        "```json",
        json.dumps(corrupted_quality, indent=2) if corrupted_quality else "{}",
        "```",
        "### Repaired",
        "```json",
        json.dumps(repaired_quality, indent=2) if repaired_quality else "{}",
        "```",
        "",
        "## 3. Freshness Comparison",
        "### Corrupted",
        "```json",
        json.dumps(corrupted_freshness, indent=2) if corrupted_freshness else "{}",
        "```",
        "### Repaired",
        "```json",
        json.dumps(repaired_freshness, indent=2) if repaired_freshness else "{}",
        "```",
        ""
    ]
    
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
