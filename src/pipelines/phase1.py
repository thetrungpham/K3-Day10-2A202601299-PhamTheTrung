from __future__ import annotations

import json
from datetime import datetime, timezone

from core.config import load_settings, require_llm_credentials
from core.utils import read_json, write_json
from ingestion import build_clean_dataframe, fetch_source_records, load_raw_records
from retrieval import LocalEmbeddingIndex, run_agent_question, build_agent
from evaluation import build_test_set, evaluate_pipeline
from observability.quality import run_data_quality_checks, build_freshness_report
from observability.reporting import generate_phase1_report


def main() -> None:
    """Xay dung baseline pipeline end-to-end."""
    print("1. Loading settings...")
    settings = load_settings()
    
    # Kiem tra credentials (chi can thiet neu LLM hoac Embedding doi hoi)
    try:
        require_llm_credentials(settings)
    except RuntimeError as e:
        print(f"Warning: {e}")
        print("Continuing without LLM credentials, some parts (eval, agent) may fail.")

    print("2. Loading or fetching raw records...")
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        print("Fetching from API...")
        records = fetch_source_records(settings)
    else:
        print(f"Loading cached records from {settings.paths.raw_records_json}")
        records = load_raw_records(settings.paths.raw_records_json)
        
    print(f"Loaded {len(records)} raw records.")
    
    print("3. Cleaning data...")
    run_date = datetime.now(timezone.utc)
    df_clean = build_clean_dataframe(records, run_date)
    
    print("4. Saving clean CSV/JSON...")
    settings.paths.clean_csv.parent.mkdir(parents=True, exist_ok=True)
    df_clean.to_csv(settings.paths.clean_csv, index=False)
    
    clean_records = df_clean.to_dict(orient="records")
    write_json(settings.paths.clean_json, clean_records)
    
    print("5. Building Chroma index...")
    index = LocalEmbeddingIndex.build(df_clean, settings, settings.paths.embeddings_json)
    
    print("6. Creating or loading evaluation set...")
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        print("Generating test set...")
        test_set = build_test_set(df_clean, settings.paths.eval_testset)
    else:
        print("Loading test set from cache...")
        test_set = read_json(settings.paths.eval_testset)
        
    print("7. Evaluating pipeline...")
    eval_bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    
    print("8. Running quality checks and freshness report...")
    quality_report = run_data_quality_checks(df_clean, settings, "quality_report.json")
    freshness_report = build_freshness_report(df_clean, settings, settings.paths.freshness_report)
    
    print("9. Generating Markdown report...")
    source_summary = {
        "api": settings.source_api,
        "query": settings.source_query,
        "filter": settings.source_filter,
        "max_results": settings.max_results
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=eval_bundle.summary,
        quality=quality_report,
        freshness=freshness_report
    )
    print(f"Report generated at {settings.paths.baseline_report}")
    
    print("10. Demo agent...")
    try:
        agent = build_agent(settings=settings, index=index)
        sample_question = "What are the latest advancements in agentic RAG?"
        print(f"\nQuestion: {sample_question}")
        answer = run_agent_question(agent, sample_question)
        print(f"Answer: {answer.answer}")
    except Exception as e:
        print(f"Skipping demo agent due to: {e}")

if __name__ == "__main__":
    main()
