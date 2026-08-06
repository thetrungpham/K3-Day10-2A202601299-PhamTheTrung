from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_text
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe, save_clean_dataset
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


RAG_METRICS = (
    "samples",
    "retrieval_hit_rate",
    "mean_token_f1",
    "judge_accuracy",
    "mean_judge_score",
)


def _require_artifacts(required_paths: list[Path]) -> None:
    missing_paths = [path for path in required_paths if not path.exists()]
    if missing_paths:
        formatted_paths = "\n".join(f"- {path}" for path in missing_paths)
        raise FileNotFoundError(
            "Corruption flow requires a completed baseline run. "
            f"Missing artifacts:\n{formatted_paths}"
        )


def _load_clean_dataframe(path: Path) -> pd.DataFrame:
    payload = read_json(path)
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"Expected a non-empty JSON record list at {path}.")
    dataframe = pd.DataFrame(payload)
    if dataframe.empty:
        raise ValueError(f"Clean dataset is empty: {path}.")
    return dataframe


def _read_corrupted_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Corrupted CSV was not created: {path}")
    dataframe = pd.read_csv(path, keep_default_na=False)
    if dataframe.empty:
        raise ValueError(f"Corrupted CSV is empty: {path}")
    return dataframe


def _report_value(value: Any) -> str:
    if isinstance(value, bool):
        return "PASS" if value else "FAIL"
    if isinstance(value, float):
        return f"{value:.4f}"
    if value is None:
        return "N/A"
    return str(value)


def _comparison_table(
    heading: str,
    rows: list[tuple[str, Any, Any, Any]],
) -> list[str]:
    lines = [
        f"### {heading}",
        "",
        "| Metric / Signal | Baseline | Corrupted | Repaired |",
        "| --- | ---: | ---: | ---: |",
    ]
    lines.extend(
        f"| {name} | {_report_value(baseline)} | {_report_value(corrupted)} | {_report_value(repaired)} |"
        for name, baseline, corrupted, repaired in rows
    )
    return lines


def _append_checkpoint_evidence(
    report_path: Path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    baseline_quality: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    baseline_freshness: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
    corruption_log: dict[str, Any],
) -> None:
    metric_rows = [
        (
            metric,
            baseline_metrics.get(metric),
            corrupted_metrics.get(metric),
            repaired_metrics.get(metric),
        )
        for metric in RAG_METRICS
    ]
    quality_rows = [
        (
            "quality_passed",
            baseline_quality.get("passed"),
            corrupted_quality.get("passed"),
            repaired_quality.get("passed"),
        ),
        (
            "row_count",
            baseline_quality.get("row_count"),
            corrupted_quality.get("row_count"),
            repaired_quality.get("row_count"),
        ),
        (
            "paper_id_is_unique",
            baseline_quality.get("paper_id_is_unique"),
            corrupted_quality.get("paper_id_is_unique"),
            repaired_quality.get("paper_id_is_unique"),
        ),
        (
            "summary_empty_or_null",
            baseline_quality.get("summary_empty_or_null"),
            corrupted_quality.get("summary_empty_or_null"),
            repaired_quality.get("summary_empty_or_null"),
        ),
        (
            "stale_count",
            baseline_quality.get("stale_count"),
            corrupted_quality.get("stale_count"),
            repaired_quality.get("stale_count"),
        ),
        (
            "freshness_is_fresh",
            baseline_freshness.get("is_fresh"),
            corrupted_freshness.get("is_fresh"),
            repaired_freshness.get("is_fresh"),
        ),
        (
            "freshness_stale_rows",
            baseline_freshness.get("stale_rows"),
            corrupted_freshness.get("stale_rows"),
            repaired_freshness.get("stale_rows"),
        ),
    ]

    overlap_ids = corruption_log.get("frozen_test_set", {}).get("corrupted_overlap_doc_ids", [])
    evidence_lines = [
        "",
        "## 4. Checkpoint C4 - Three-State Comparison",
        "",
        *_comparison_table("RAG Metrics", metric_rows),
        "",
        *_comparison_table("Observability Signals", quality_rows),
        "",
        "## 5. Interpretation",
        "",
        (
            "- Frozen-test overlap: "
            f"{len(overlap_ids)} document(s): {', '.join(overlap_ids) if overlap_ids else 'none'}."
        ),
        (
            "- The most severe retrieval corruption is `drop_frozen_document`: the ground-truth "
            "paper is absent from Chroma, so none of its frozen questions can produce a retrieval hit."
        ),
        (
            "- Among the required scenarios, `add_embedding_noise` directly distorts the vector "
            "representation and can lower semantic-search ranking. Exact-title lookup may partially mask this effect."
        ),
        (
            "- Repair must rebuild from the saved raw snapshot instead of fetching Crossref again. "
            "The live API can change between runs; a new fetch would introduce source drift and make the "
            "baseline/corrupted/repaired comparison irreproducible."
        ),
        "",
    ]
    current_report = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
    write_text(report_path, current_report.rstrip() + "\n" + "\n".join(evidence_lines))


def main() -> None:
    """Run controlled corruption, raw-snapshot repair, and three-state comparison."""
    settings = load_settings()
    paths = settings.paths

    corrupted_csv_path = paths.clean_csv.with_name("papers_corrupted.csv")
    corrupted_json_path = paths.clean_json.with_name("papers_corrupted.json")
    baseline_quality_path = paths.quality_dir / "quality_report.json"
    corrupted_quality_path = paths.quality_dir / "corrupted_quality_report.json"
    repaired_quality_path = paths.quality_dir / "repaired_quality_report.json"
    corrupted_freshness_path = paths.quality_dir / "corrupted_freshness_report.json"
    repaired_freshness_path = paths.quality_dir / "repaired_freshness_report.json"

    _require_artifacts(
        [
            paths.raw_records_json,
            paths.clean_json,
            paths.eval_testset,
            paths.baseline_metrics,
            baseline_quality_path,
            paths.freshness_report,
        ]
    )

    print("1. Loading frozen baseline artifacts...")
    baseline_df = _load_clean_dataframe(paths.clean_json)
    baseline_metrics = read_json(paths.baseline_metrics)
    baseline_quality = read_json(baseline_quality_path)
    baseline_freshness = read_json(paths.freshness_report)
    test_set = read_json(paths.eval_testset)
    if not isinstance(baseline_metrics, dict) or not baseline_metrics:
        raise ValueError(f"Baseline metrics are empty or invalid: {paths.baseline_metrics}")
    if not isinstance(test_set, list) or not test_set:
        raise ValueError(f"Frozen test set is empty or invalid: {paths.eval_testset}")

    print("2. Creating controlled corruptions with frozen-test overlap...")
    corrupted_df = corrupt_clean_dataframe(baseline_df, paths.corruption_log)
    save_clean_dataset(
        corrupted_df,
        settings,
        csv_path=corrupted_csv_path,
        json_path=corrupted_json_path,
    )
    corruption_log = read_json(paths.corruption_log)
    overlap_count = corruption_log.get("frozen_test_set", {}).get("overlap_count", 0)
    if overlap_count < 1:
        raise RuntimeError("C4 failed: corruption did not overlap a frozen test document.")
    print(f"Corrupted CSV saved at {corrupted_csv_path}")

    print("3. Reading papers_corrupted.csv and rebuilding the corrupted index...")
    corrupted_eval_df = _read_corrupted_csv(corrupted_csv_path)
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_eval_df,
        settings=settings,
        embeddings_output_path=paths.corrupted_embeddings_json,
    )

    print("4. Evaluating corrupted state on the frozen test set...")
    corrupted_evaluation = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.corrupted_metrics,
        answers_output_path=paths.corrupted_answers,
    )
    corrupted_quality = run_data_quality_checks(
        corrupted_eval_df,
        settings=settings,
        report_name=corrupted_quality_path.name,
    )
    corrupted_freshness = build_freshness_report(
        corrupted_eval_df,
        settings=settings,
        report_path=corrupted_freshness_path,
    )
    if corrupted_quality.get("passed") is not False:
        raise RuntimeError("C4 failed: corrupted quality report did not record FAIL.")

    print("5. Repairing from data/raw/crossref_records.json...")
    raw_records = load_raw_records(paths.raw_records_json)
    if not raw_records:
        raise RuntimeError("Repair cannot continue because the raw snapshot is empty.")
    repaired_df = build_clean_dataframe(raw_records, run_date=now_utc())
    if repaired_df.empty:
        raise RuntimeError("Repair cannot continue because cleaning produced an empty dataset.")
    save_clean_dataset(
        repaired_df,
        settings,
        csv_path=paths.repaired_clean_csv,
        json_path=paths.repaired_clean_json,
    )

    print("6. Rebuilding and evaluating the repaired index on the same frozen test set...")
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df,
        settings=settings,
        embeddings_output_path=paths.repaired_embeddings_json,
    )
    repaired_evaluation = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.repaired_metrics,
        answers_output_path=paths.repaired_answers,
    )
    repaired_quality = run_data_quality_checks(
        repaired_df,
        settings=settings,
        report_name=repaired_quality_path.name,
    )
    repaired_freshness = build_freshness_report(
        repaired_df,
        settings=settings,
        report_path=repaired_freshness_path,
    )

    print("7. Generating Baseline - Corrupted - Repaired comparison report...")
    generate_corruption_report(
        report_path=paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_evaluation.summary,
        repaired_metrics=repaired_evaluation.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
    _append_checkpoint_evidence(
        report_path=paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_evaluation.summary,
        repaired_metrics=repaired_evaluation.summary,
        baseline_quality=baseline_quality,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        baseline_freshness=baseline_freshness,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
        corruption_log=corruption_log,
    )
    print(f"Comparison report generated at {paths.comparison_report}")


if __name__ == "__main__":
    main()
