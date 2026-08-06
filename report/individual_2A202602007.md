# Báo cáo vai trò thành viên - Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin       | Nội dung                                                            |
| --------------- | ------------------------------------------------------------------- |
| Họ và tên       | Vũ Thành Dương                                                      |
| MSSV            | 2A202602007                                                         |
| Khóa/Lớp        | K3                                                                  |
| Tên nhóm        | Nhóm A7                                                             |
| Vai trò chính   | Corruption & Integration Owner                                      |
| Repository      | `https://github.com/thetrungpham/K3-Day10-2A202601299-PhamTheTrung` |
| Ngày hoàn thành | 2026-08-06                                                          |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable              | File/hàm phụ trách                                       | Input nhận vào                                    | Output bàn giao                                                              | Trạng thái                     |
| ------------------------------- | -------------------------------------------------------- | ------------------------------------------------- | ---------------------------------------------------------------------------- | ------------------------------ |
| Controlled corruption           | `src/ingestion/corruption.py`, `corrupt_clean_dataframe` | Clean dataframe và frozen test set                | Corrupted dataframe,`data/results/corruption_log.json`                       | Hoàn thành, đã chạy            |
| Corruption/repair orchestration | `src/pipelines/corruption_flow.py`, `main`               | Baseline artifacts, raw snapshot, frozen test set | Corrupted/repaired datasets, metrics, quality/freshness và comparison report | Hoàn thành, đã chạy end-to-end |

Tôi không nhận ownership `src/pipelines/phase1.py`, `src/observability/quality.py` hoặc `src/observability/reporting.py`. Các module này là dependency được sử dụng khi tích hợp.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                              | Thành viên/module được hỗ trợ       | Kết quả                                                                                                            |
| -------------------------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Kiểm tra baseline artifact trước pha 2 | Baseline pipeline                   | Xác nhận đủ raw snapshot, clean JSON, frozen test set, baseline metrics, quality và freshness trước khi corruption |
| Kiểm tra contract giữa các module      | Cleaning, evaluation, observability | Giữ nguyên test set; truyền đúng dataframe và artifact path cho index, evaluator, quality và reporting             |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện                   | File/hàm/artifact liên quan                    | Kết quả bàn giao                                                                           | Cách xác minh                                                                       |
| --------------------------------------- | ---------------------------------------------- | ------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------- |
| Tạo lỗi dữ liệu có kiểm soát            | `src/ingestion/corruption.py`                  | 5 operation: drop frozen document, blank summary, stale date, embedding noise và duplicate | `data/results/corruption_log.json`                                                  |
| Bảo đảm corruption đụng frozen test set | `corrupt_clean_dataframe`                      | Cả 4 unique ground-truth document IDs đều bị tác động;`overlap_count=4`                    | Trường`frozen_test_set` trong corruption log                                        |
| Chạy corrupted evaluation               | `src/pipelines/corruption_flow.py`             | Retrieval hit rate giảm từ`1.0` xuống `0.75`; quality và freshness chuyển sang FAIL        | `data/results/corrupted_metrics.json`, `data/quality/corrupted_quality_report.json` |
| Repair từ raw snapshot                  | `build_clean_dataframe(load_raw_records(...))` | Phục hồi 24 rows sạch, ID unique, không blank summary, không stale row                     | Repaired dataset và quality/freshness reports                                       |
| So sánh ba trạng thái                   | `data/reports/corruption_report.md`            | Bảng Baseline-Corrupted-Repaired cho RAG metrics và observability signals                  | Đọc bảng tại mục Checkpoint C4 trong report                                         |

Output tiêu biểu là `data/results/corruption_log.json`. Artifact này ghi input/output row count, random seed, frozen IDs, từng operation, record bị tác động, giá trị trước/sau và cờ `affects_frozen_test_set`. Vì vậy kết quả corruption có thể audit và tái hiện thay vì chỉ dựa vào thông báo trên terminal.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pha 2 phải chứng minh lỗi dữ liệu thực sự ảnh hưởng hệ thống RAG. Nếu corruption chỉ chọn ngẫu nhiên các paper không nằm trong frozen test set thì metrics có thể không đổi. Đồng thời repair phải dùng cùng nguồn và cùng test set để phép so sánh ba trạng thái có ý nghĩa.

### Cách triển khai

`corrupt_clean_dataframe` suy ra đường dẫn `data/eval/test_set.json` từ đường dẫn corruption log, đọc toàn bộ `ground_truth_doc_ids` và đối chiếu với `paper_id` của clean dataframe. Việc chọn record dùng seed `42` và ưu tiên frozen IDs khác nhau cho từng scenario:

1. Xóa một frozen document để tạo retrieval miss chắc chắn.
2. Đặt summary của bốn records thành rỗng.
3. Đưa published date của bốn records về `2000-01-01` và cập nhật `age_days`.
4. Chèn noise dài, không liên quan trực tiếp vào `text_for_embedding` của bốn records.
5. Nhân đôi bốn records và giữ nguyên `paper_id` để quality uniqueness check thất bại.

Sau corruption, flow lưu `data/clean/papers_corrupted.csv`, đọc lại chính CSV này, build collection `papers-corrupted` và evaluate trên frozen test set. Repair đọc `data/raw/crossref_records.json`, chạy lại `build_clean_dataframe`, build collection `papers-repaired` và evaluate lại trên đúng test set cũ.

### Input, output và contract

| Thành phần              | Mô tả                                                                                                                                                         |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Input                   | Baseline clean records có`paper_id`, `title`, `summary`, `published`, `text_for_embedding`; frozen test set; baseline metrics/quality/freshness; raw snapshot |
| Output                  | Corrupted/repaired dataset, corruption log, hai bộ metrics/answers, quality/freshness reports và comparison report                                            |
| Module phụ thuộc        | `ingestion.cleaning`, `ingestion.crossref`, `retrieval.index`, `evaluation.metrics`, `observability.quality`, `observability.reporting`                       |
| Module sử dụng output   | Chroma index, evaluator và báo cáo so sánh C4                                                                                                                 |
| Điều kiện lỗi cần xử lý | Thiếu baseline artifact; dataframe rỗng hoặc thiếu cột; frozen IDs không khớp clean data; corruption không overlap; corrupted quality không FAIL              |

### Cách xác minh

```bash
uv run python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** tạo corrupted dataset/log, corrupted quality FAIL, repaired quality PASS và report ba trạng thái.
- **Kết quả thực tế:** exit code `0`, thời gian khoảng 67 giây; retrieval `1.0 -> 0.75 -> 1.0`; quality/freshness `PASS -> FAIL -> PASS`.
- **Artifact/log:** `data/results/corruption_log.json`, `data/results/*_metrics.json`, `data/quality/*_report.json`, `data/reports/corruption_report.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Corruption ngẫu nhiên trên toàn bộ 24 papers không bảo đảm ảnh hưởng 4 papers của frozen test set.
- **Các phương án đã cân nhắc:** sample hoàn toàn ngẫu nhiên; hard-code một DOI cụ thể; hoặc đọc frozen test set và ưu tiên ground-truth IDs.
- **Phương án đã chọn:** frozen-aware deterministic selection với seed cố định và reserved IDs cho từng scenario.
- **Lý do:** không phụ thuộc nội dung dataset cụ thể, bảo đảm correctness của thí nghiệm, có thể tái hiện và vẫn giữ được một phần sample ngẫu nhiên.
- **Bằng chứng quyết định phù hợp:** corruption log ghi cả 4 frozen IDs trong `corrupted_overlap_doc_ids`; từng operation đều có `affects_frozen_test_set=true`; retrieval hit rate giảm còn `0.75`.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** lần chạy đầu, operation `add_embedding_noise` có `"affects_frozen_test_set": false` dù tổng corruption đã overlap test set.
- **Lệnh hoặc bước tái hiện:** chạy `uv run python script/run_corruption_flow.py`, sau đó đọc `data/results/corruption_log.json`.
- **Nguyên nhân gốc:** random filler của scenario blank summary đã chọn trước frozen document dự kiến dành cho noise; noise selection loại index đã dùng nên phải chọn paper ngoài test set.
- **Cách xử lý:** thêm `reserved_paper_ids` vào `_select_indices`, không cho random filler lấy frozen IDs đã dành cho scenario sau.
- **Cách xác minh sau khi sửa:** chạy lại flow; cả drop, blank, stale, noise và duplicate đều ghi `affects_frozen_test_set=true`; exit code `0`.
- **Điều học được:** kiểm tra tổng overlap là chưa đủ; log theo từng operation giúp phát hiện corruption scenario chưa thực sự tác động evaluation target.

## 7. Hiểu biết về luồng end-to-end

1. Crossref response được parse thành `PaperRecord` và lưu raw snapshot. Cleaning chuẩn hóa text/date, loại record lỗi và duplicate, tính `age_days`, `summary_chars`, đồng thời tạo `text_for_embedding`. MiniLM biến text thành vector và ChromaDB lưu vector cùng metadata để search.
2. Frozen evaluation set có 16 câu hỏi thuộc 4 loại summary, authors, date và categories. Mỗi câu chứa ground truth và `ground_truth_doc_ids`; evaluator so IDs retrieval được với danh sách này để tính hit rate, đồng thời so answer với ground truth bằng token F1 và judge.
3. Quality checks đo tính đầy đủ và nhất quán như ID null/duplicate, title, summary và stale count. Freshness monitoring tập trung vào tuổi dữ liệu, latest/oldest published date, số stale rows và trạng thái `is_fresh`.
4. Baseline, corrupted và repaired phải dùng cùng frozen test set vì thay câu hỏi hoặc ground truth sẽ tạo thêm biến số, làm thay đổi metrics không còn chỉ do corruption/repair.
5. Repair thành công khi dữ liệu được dựng lại từ raw snapshot, quality/freshness trở về PASS và metrics phục hồi. Trong lần chạy này, repaired có 24 rows sạch và toàn bộ bốn metrics RAG trở lại mức baseline.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal        | Baseline | Corrupted | Repaired | Nhận xét của cá nhân                                                           |
| -------------------- | -------: | --------: | -------: | ------------------------------------------------------------------------------ |
| `retrieval_hit_rate` |   1.0000 |    0.7500 |   1.0000 | Xóa một trong bốn frozen papers làm bốn câu hỏi mất ground-truth retrieval hit |
| `mean_token_f1`      |   1.0000 |    0.6250 |   1.0000 | Blank summary, stale date và missing document làm answer lệch ground truth     |
| `judge_accuracy`     |   1.0000 |    0.6250 |   1.0000 | Judge ghi nhận cùng xu hướng suy giảm như token F1                             |
| `mean_judge_score`   |   5.0000 |    3.8750 |   5.0000 | Chất lượng answer giảm rõ ràng nhưng phục hồi hoàn toàn                        |
| Quality checks       |     PASS |      FAIL |     PASS | Corrupted có duplicate IDs, 4 blank summaries và 5 stale rows                  |
| Freshness status     |     PASS |      FAIL |     PASS | Oldest date bị đưa về năm 2000; repair khôi phục ngày gốc                      |

### Kết luận từ số liệu

1. Drop frozen document, blank summary, stale date và duplicate ID làm quality/freshness chuyển `PASS -> FAIL`, đồng thời retrieval giảm `1.0 -> 0.75`, token F1 và judge accuracy giảm `1.0 -> 0.625`.
2. Reload raw snapshot và chạy cleaning chuẩn giúp uniqueness, completeness và freshness trở lại PASS; retrieval, token F1, judge accuracy và judge score đều phục hồi đúng mức baseline.

Corruption ảnh hưởng retrieval rõ nhất là `drop_frozen_document`. Khi paper ground truth không còn trong Chroma, semantic search hay exact lookup đều không thể trả lại đúng `paper_id`. Trong bốn scenario bắt buộc, embedding noise tác động trực tiếp tới vector ranking nhưng ảnh hưởng có thể bị che bởi exact-title lookup của QA.

Kết quả khác kỳ vọng ban đầu là embedding noise không tạo mức giảm retrieval riêng có thể quan sát trực tiếp trong metrics tổng hợp. Nguyên nhân là test question chứa exact title và QA ưu tiên lookup chính xác trước semantic search. Tôi kiểm tra bằng code path trong `retrieval/qa.py` và ghi giới hạn này vào comparison report. Ngoài ra, thí nghiệm hiện chạy đồng thời nhiều corruption nên chưa tách được contribution riêng của từng scenario.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Một data pipeline có thể chạy không lỗi nhưng thí nghiệm vẫn vô nghĩa nếu dữ liệu corruption không overlap evaluation target.
2. Quality và freshness signals giúp xác định nguyên nhân dữ liệu cụ thể, trong khi RAG metrics đo hậu quả ở tầng retrieval/answer; cần đọc cả hai nhóm tín hiệu.
3. Repair đúng nghĩa phải tái dựng từ raw snapshot ổn định. Fetch lại API sống có thể gây source drift và phá tính công bằng của phép so sánh.

### Nếu có thêm thời gian

Tôi sẽ chạy ablation riêng từng corruption scenario trên cùng frozen test set và thêm một nhóm câu hỏi semantic-only không dùng exact-title lookup. Cách cải thiện này cho phép đo delta của từng scenario, đặc biệt tách rõ ảnh hưởng của embedding noise đối với retrieval ranking. Ragas cũng có thể bật bằng `RUN_RAGAS=1` để bổ sung faithfulness và context metrics khi có đủ thời gian/API quota.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Vũ Thành Dương
**Ngày xác nhận:** 2026-08-06
