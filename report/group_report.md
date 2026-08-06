# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K3                         |
| Tên nhóm         | A7                         |
| Repository         | https://github.com/thetrungpham/K3-Day10-2A202601299-PhamTheTrung |
| Ngày hoàn thành | 2026-08-06                 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Lê Thành Nam | 2A202601397 | Source Ingestion Owner | `src/ingestion/crossref.py`, `crossref_records.json` |
| 2 | Chu Phú Thành | 2A202601289 | Data Model & Evaluation Set Owner | `src/ingestion/cleaning.py`, `src/evaluation/testset.py`, `test_set.json` |
| 3 | Phạm Thế Trung | 2A202601299 | Data Observability Owner | `src/observability/quality.py`, `src/pipelines/phase1.py`, `phase1_report.md` |
| 4 | Vũ Thành Dương | 2A202602007 | Corruption & Integration Owner | `src/ingestion/corruption.py`, `src/pipelines/phase1.py`, `script/run_corruption_flow.py` |

## 2. Tóm tắt kết quả

- Nhóm đã hoàn thành toàn bộ baseline pipeline từ khâu ingestion (lấy dữ liệu thô từ Crossref API), cleaning (chuẩn hóa text và date, lược bỏ markup JATS XML), embedding, evaluation, kiểm tra data quality/freshness, cho đến việc tạo kịch bản corruption và thực hiện repair từ snapshot.
- Baseline pipeline đã tạo ra các artifacts: `crossref_response.json`, `crossref_records.json`, `papers_clean.csv`, `papers_clean.json`, `test_set.json`, file nhúng `papers_embeddings.json`, cùng các file metrics đánh giá baseline và log như `ingest_log.json`, `papers_clean_log.json`.
- Corruption `drop_frozen_document` ảnh hưởng rõ nhất đến RAG agent: do tài liệu gốc bị xóa khỏi index, `retrieval_hit_rate` giảm từ 100% xuống 75%, kéo theo F1 và điểm số của LLM giảm mạnh (mất dữ liệu cho 4/16 câu hỏi).
- Repair (bằng cách nạp lại dữ liệu từ file dữ liệu thô chưa lỗi `crossref_response.json`) đã phục hồi 100% các chỉ số (hit rate 1.0, token F1 1.0, quality và freshness pass).
- Blocker/giới hạn quan trọng nhất: Test set được thiết kế dùng "exact-lookup" (đặt tựa đề trong dấu nháy đơn) khiến nó dễ dàng bỏ qua phần semantic search của vector DB, dẫn tới việc một số corruption như `add_embedding_noise` không thể được đo lường hay phát hiện thông qua metrics của agent.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API
    -> raw response/raw records (ingestion, retry, _fetch_payload)
    -> cleaning và data modeling (strip XML tag, normalize date, dedupe)
    -> embedding + ChromaDB index (text_for_embedding 5 fields)
    -> evaluation baseline (frozen test set 16 questions)
    -> quality/freshness reports (null check, freshness > 180 days)
    -> corruption (drop document, blank summary, stale date)
    -> re-index và re-evaluate
    -> repair từ dữ liệu nguồn (raw snapshot)
    -> comparison report
```

### Trách nhiệm của từng khối

| Khối             | Input          | Xử lý chính             | Output/artifact          | Owner          |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion         | Query từ config| Fetch API, retry backoff, parse   | `data/raw/crossref_records.json` | Lê Thành Nam |
| Cleaning          | Raw records    | Strip XML/HTML, parse dates, dedupe  | `data/clean/papers_clean.json` | Chu Phú Thành |
| Embedding/index   | Clean records  | Ghép 5 field, tạo index MiniLM  | `data/embeddings/papers_embeddings.json` | Lê Thành Nam |
| Evaluation        | Clean records  | Sinh 16 samples test set | `data/eval/test_set.json` | Chu Phú Thành |
| Observability     | Clean records  | Check schema, null, stale_date | `data/results/baseline_metrics.json` | Phạm Thế Trung |
| Corruption/repair | Clean/Raw data | Thêm nhiễu, drop document, repair | `data/results/repaired_metrics.json` | Vũ Thành Dương |
| Orchestration     | Toàn hệ thống  | Run theo thứ tự Pipeline | `report/phase1_report.md` | Phạm Thế Trung |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER`             | openai            |
| `LLM_MODEL`                | gpt-4o-mini  |
| Embedding model              | `all-MiniLM-L6-v2`|
| Số lượng Crossref records | 24                |
| Retrieval `top_k`           | Mặc định          |
| Freshness threshold          | 180 ngày          |

### Lệnh cài đặt

```bash
uv sync
```

### Lệnh chạy

Baseline:

```bash
uv run python script/run_phase1.py
```

Corruption flow:

```bash
uv run python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh             | Trạng thái                                    | Thời điểm chạy gần nhất | Bằng chứng                         |
| ----------------- | ----------------------------------------------- | ----------------------------- | ------------------------------------ |
| Baseline pipeline | Thành công                              | 2026-08-06 11:45              | `phase1_report.md`, `baseline_metrics.json` |
| Corruption flow   | Thành công                              | 2026-08-06 12:16              | `corrupted_metrics.json`, `corruption_log.json` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị                             |
| --------------------------- | ------------------------------------- |
| Source                      | Crossref API (JSON endpoint)          |
| Số record nhận được    | 24                                  |
| Cơ chế retry/backoff      | Đọc `Retry-After` header và dùng Exponential Backoff. Truyền `User-Agent` hợp lệ. |

### Raw và clean schema

| Trường        | Kiểu dữ liệu | Bắt buộc?  | Ý nghĩa   | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| `paper_id`    | string         | Có         | DOI hoặc mã bài báo | Loại bỏ record |
| `title`       | string         | Có         | Tiêu đề | Strip XML `<jats:title>`, bỏ whitespace, rỗng -> loại |
| `published`   | date           | Có         | Ngày phát hành | Fallback tuple padding (thêm ngày 1, tháng 1 nếu thiếu) |
| `summary`     | string         | Không      | Tóm tắt | Giữ lại, filter nếu độ dài < 100 char |

### Quy tắc cleaning

| Quy tắc                                 | Quality dimension liên quan | Cách xác minh      |
| ---------------------------------------- | ---------------------------- | -------------------- |
| Loại bỏ HTML/XML `<jats:p>` | Validity  | Kiểm tra chuỗi sạch sau hàm `_strip_markup` |
| Bỏ record thiếu title, published | Completeness | Xem count trong `papers_clean_log.json` |
| Đưa ngày về YYYY-MM-DD | Consistency | Khẳng định Type int64 cho `age_days` |

**Giải thích cách tạo `text_for_embedding`, document ID và `age_days`**:
- `text_for_embedding`: Ghép 5 trường: `Title | Authors | Categories | Published | Summary`. (Nhằm đo được sự thay đổi của categories và published do các hành vi gây nhiễu).
- Document ID (`paper_id`): Chuyển thành chữ thường để dedupe không phân biệt hoa/thường.
- `age_days`: Tính bằng cách lấy `run_date` trừ đi ngày `published` (đã quy đổi về tz-aware), clip lower bound ở 0.

## 6. Evaluation setup

| Thành phần                             | Cấu hình thực tế          |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi                            | 16 (4 papers x 4 types)     |
| Các `question_type`                    | authors, date, categories, summary |
| Ground-truth document ID                 | `paper_id` của bản ghi clean  |
| Embedding model                          | `all-MiniLM-L6-v2`            |
| LLM provider/model                       | gemini                        |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json`     |

**Giải thích vì sao test set được giữ nguyên khi đánh giá baseline, corrupted và repaired:**
Để tuân thủ nguyên lý kiểm thử (A/B Testing), chỉ được thay đổi dữ liệu bên dưới index và giữ nguyên bộ câu hỏi. Nếu thay đổi cả câu hỏi, hệ thống sẽ không đo lường được là F1 giảm đi do chất lượng câu hỏi bị thay đổi hay do chất lượng document.

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                | Trạng thái | Ghi chú   |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records     | `data/raw/`                          | Có         | Gồm `crossref_response.json`, `crossref_records.json` |
| Cleaned dataset          | `data/clean/`                        | Có         | Gồm `.csv`, `.json`, `_log.json` |
| Embedding manifest/index | `data/embeddings/`                   | Có         | Sinh bởi LocalEmbeddingIndex |
| Evaluation set           | `data/eval/test_set.json`            | Có         | 16 samples, 4 papers |
| Baseline metrics         | `data/results/baseline_metrics.json` | Có         | |
| Quality/freshness        | `data/results/baseline_answers.json` | Có         | Metric quality check pass hoàn toàn |
| Baseline report          | `report/phase1_report.md`            | Có         | Tự động tạo bằng python |

### Baseline metrics

| Metric                 |       Giá trị | Diễn giải                             |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` |     1.0000 | Tỉ lệ retrieval lấy đúng document chứa thông tin gốc. Đạt tuyệt đối do sử dụng query có title exact-match. |
| `mean_token_f1`      |     1.0000 | Tỉ lệ trùng lặp token giữa câu trả lời và field ground truth. |
| `judge_accuracy`     |     1.0000 | Tỉ lệ mà câu trả lời nhận được đánh giá cao bởi LLM Judge. |
| `mean_judge_score`   |     5.0000 | Điểm judge trung bình trên tập test set (tối đa là 5). |

## 8. Data quality và freshness

### Quality checks

| Check        | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline      | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| Unique Paper ID | Uniqueness | True | Pass (True) | `quality.py` report |
| Không rỗng Summary | Completeness | 0 | Pass (0 empty) | `baseline_metrics.json` |

### Freshness

| Thuộc tính               | Giá trị                           |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | `published` field (tính theo `age_days`) |
| Ngưỡng freshness         | 180 ngày                          |
| Trạng thái baseline      | Fresh                             |
| Lý do                     | Các bài báo trong clean corpus đều có date xuất bản không quá 180 ngày tính đến thời điểm crawl (2026-08). |

## 9. Corruption scenarios và repair

| Corruption         | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair   |
| ------------------ | ---------- | ---------------------: | ------------------------ | --------------------- | -------------- |
| `drop_frozen_document` | Loại bỏ record | 1 | Giảm hit rate | `retrieval_hit_rate` tụt xuống 0.75 | Load raw records từ `data/raw/` |
| `blank_summary`    | Xóa nội dung summary | 4 | Fail Completeness | token F1 giảm xuống 0 ở sample p2-summary | Dùng source data cũ |
| `stale_date`       | Chỉnh lùi năm xuất bản về 2000 | 5 | Fail Freshness | Freshness báo Fail (5 stale rows) | Parse lại ngày gốc |

**Giải thích cách repair:**
Quá trình repair được đảm bảo độ tin cậy do không phải dùng các bản chỉnh tay để lấp liếm lỗi, mà quy trình sẽ reload lại dữ liệu thô (`crossref_response.json`) ban đầu từ module ingestion rồi sau đó chạy lại luồng cleaning tiêu chuẩn, tái thiết lập hoàn toàn lại index một cách chính xác nhất.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: |
| `retrieval_hit_rate`   |      1.0 |      0.75 |      1.0 |                     Giảm 25% |             100% |
| `mean_token_f1`        |      1.0 |     0.625 |      1.0 |                   Giảm 37.5% |             100% |
| `judge_accuracy`       |      1.0 |     0.625 |      1.0 |                   Giảm 37.5% |             100% |
| `mean_judge_score`     |      5.0 |     3.875 |      5.0 |                   Giảm 1.125 |             100% |
| Quality checks pass/fail |     Pass |      Fail |     Pass |                Thành Fail |             100% |
| Freshness status         |     Pass |      Fail |     Pass |                Thành Fail |             100% |

**Kết luận có quan hệ nhân quả:**
1. Khi cố tình drop một frozen document khỏi index, `retrieval_hit_rate` của RAG giảm mạnh dẫn đến `mean_judge_score` giảm tương ứng, minh chứng rằng RAG mất khả năng đưa ra câu trả lời chính xác nếu không lấy được bối cảnh (context miss).
2. Việc repair (bằng cách lấy dữ liệu sạch lại từ pipeline) giúp quality check và freshness báo Pass trở lại, và `mean_token_f1` + `judge_accuracy` khôi phục đúng mức gốc 1.0 (phục hồi hoàn toàn agent metric) - khẳng định tính đúng đắn của pipeline từ đầu đến cuối.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Khi chạy module clean, việc export ra `.csv` làm hỏng cấu trúc các mảng (List) thành một đoạn string (ví dụ: `authors` từ dạng mảng chuyển thành chuỗi `"['A', 'B']"`).
- **Nguyên nhân:** Format `.csv` không lưu trữ được native list.
- **Cách xử lý:** TV4 đã phải nạp lại dataset qua file json (`papers_clean.json`) làm nguồn sự thật (source of truth), để giữ nguyên format mảng cho các module sau.
- **Cách xác minh:** Inspect kết quả đầu vào ở phần index, xác nhận mảng category và author được giữ nguyên là Python list khi đọc từ json.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng   | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| Câu hỏi Test Set kích hoạt tính năng tra cứu chính xác (exact-match lookup) do chứa dấu nháy đơn | Che lấp hiệu suất yếu của thuật toán Semantic Search, dẫn đến việc corruption `add_embedding_noise` không để lại ảnh hưởng gì lên metric. | Bổ sung câu hỏi dạng semantic (từ khóa đặc trưng) và không trích nguyên title vào test set để kiểm tra chính xác Embedding. |
| Chỉ lấy 1 page dữ liệu (24 bài) từ Crossref | Dữ liệu quá nhỏ cho hệ thống tìm kiếm mạnh, không đại diện đủ mức độ phong phú (drift, edge-cases). | Hỗ trợ Pagination thông qua token cursor của Crossref để nâng scale lên >= 100 bản ghi. |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
