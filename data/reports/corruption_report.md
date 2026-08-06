# Phase 2: Corruption and Repair Comparison

## 1. Metrics Comparison
### Baseline
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
### Corrupted
```json
{
  "samples": 16,
  "retrieval_hit_rate": 0.75,
  "mean_token_f1": 0.625,
  "judge_accuracy": 0.625,
  "mean_judge_score": 3.875,
  "ragas": {
    "skipped": "Set RUN_RAGAS=1 to enable the slower Ragas pass."
  }
}
```
### Repaired
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

## 2. Quality Comparison
### Corrupted
```json
{
  "row_count": 27,
  "paper_id_nulls": 0,
  "paper_id_is_unique": false,
  "title_nulls": 0,
  "summary_empty_or_null": 4,
  "stale_count": 5,
  "passed": false
}
```
### Repaired
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

## 3. Freshness Comparison
### Corrupted
```json
{
  "latest_published": "2026-07-13",
  "oldest_published": "2000-01-01",
  "stale_rows": 5,
  "total_rows": 27,
  "is_fresh": false
}
```
### Repaired
```json
{
  "latest_published": "2026-08-01",
  "oldest_published": "2026-02-12",
  "stale_rows": 0,
  "total_rows": 24,
  "is_fresh": true
}
```

## 4. Checkpoint C4 - Three-State Comparison

### RAG Metrics

| Metric / Signal | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| samples | 16 | 16 | 16 |
| retrieval_hit_rate | 1.0000 | 0.7500 | 1.0000 |
| mean_token_f1 | 1.0000 | 0.6250 | 1.0000 |
| judge_accuracy | 1.0000 | 0.6250 | 1.0000 |
| mean_judge_score | 5 | 3.8750 | 5 |

### Observability Signals

| Metric / Signal | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| quality_passed | PASS | FAIL | PASS |
| row_count | 24 | 27 | 24 |
| paper_id_is_unique | PASS | FAIL | PASS |
| summary_empty_or_null | 0 | 4 | 0 |
| stale_count | 0 | 5 | 0 |
| freshness_is_fresh | PASS | FAIL | PASS |
| freshness_stale_rows | 0 | 5 | 0 |

## 5. Interpretation

- Frozen-test overlap: 4 document(s): 10.1007/s10278-026-02086-9, 10.20944/preprints202602.0996.v1, 10.2118/234689-pa, 10.35314/3y9hy151.
- The most severe retrieval corruption is `drop_frozen_document`: the ground-truth paper is absent from Chroma, so none of its frozen questions can produce a retrieval hit.
- Among the required scenarios, `add_embedding_noise` directly distorts the vector representation and can lower semantic-search ranking. Exact-title lookup may partially mask this effect.
- Repair must rebuild from the saved raw snapshot instead of fetching Crossref again. The live API can change between runs; a new fetch would introduce source drift and make the baseline/corrupted/repaired comparison irreproducible.
