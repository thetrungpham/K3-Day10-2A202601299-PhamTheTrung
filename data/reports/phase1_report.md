# Phase 1: Baseline Report

## 1. Source Summary
```json
{
  "api": "Crossref REST API",
  "query": "agentic retrieval augmented generation large language model",
  "filter": "from-pub-date:2026-02-07,has-abstract:true",
  "max_results": 24
}
```

## 2. Evaluation Metrics
```json
{
  "samples": 16,
  "retrieval_hit_rate": 1.0,
  "mean_token_f1": 1.0,
  "judge_accuracy": 1.0,
  "mean_judge_score": 5,
  "ragas": {
    "skipped": "Set RUN_RAGAS=1 to enable the slower Ragas pass."
  }
}
```

## 3. Data Quality
```json
{
  "row_count": 24,
  "paper_id_nulls": 0,
  "paper_id_is_unique": true,
  "title_nulls": 0,
  "summary_empty_or_null": 0,
  "stale_count": 0,
  "passed": true
}
```

## 4. Freshness
```json
{
  "latest_published": "2026-08-01",
  "oldest_published": "2026-02-12",
  "stale_rows": 0,
  "total_rows": 24,
  "is_fresh": true
}
```
