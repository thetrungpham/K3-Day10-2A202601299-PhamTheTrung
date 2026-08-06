# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                                         |
| ------------------ | ----------------------------------------------------------------- |
| Họ và tên       | Lê Thành Nam                                                    |
| MSSV               | 2A202601397                                                       |
| Khóa/Lớp         | K3                                                                |
| Tên nhóm         | A7                                                                |
| Vai trò chính    | Thành viên 1 (Source Ingestion Owner)                           |
| Repository         | https://github.com/thetrungpham/K3-Day10-2A202601299-PhamTheTrung |
| Ngày hoàn thành | 2026-08-06                                                        |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách                                                                                                 | Input nhận vào                                  | Output bàn giao                                                                     | Trạng thái |
| ------------------ | --------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- | ------------------------------------------------------------------------------------ | ------------ |
| Source Ingestion   | `src/ingestion/crossref.py` (các hàm: `parse_crossref_payload`, `fetch_source_records`, `load_raw_records`) | Query parameters (`settings`) từ `config.py` | Artifacts:`crossref_response.json`, `crossref_records.json`, `ingest_log.json` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ------------ | ------------------------------------ | --------- |
| Chưa có    |                                      |           |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện                                                                                                                    | File/hàm/artifact liên quan                                                                                          | Kết quả bàn giao                                                                                 | Cách xác minh                                                                                                                                                                  |
| ---------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Crawl dữ liệu thô từ Crossref API, bóc tách các trường thông tin thành đối tượng`PaperRecord` và lưu log quá trình chạy. | `src/ingestion/crossref.pydata/raw/crossref_response.json``data/raw/crossref_records.jsondata/raw/ingest_log.json` | Đã crawl thành công 24 bản ghi theo query. Log được số lượng bản ghi rỗng/trùng/lỗi. | Chạy lệnh`python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; fetch_source_records(load_settings())"` và kiểm tra file. |

**Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:**

Output cụ thể là file `data/raw/crossref_records.json` chứa 24 bài báo khoa học sạch sẽ, các trường dữ liệu như title, abstract đã được strip thẻ HTML/XML, ngày xuất bản đã được parse sang ISO `YYYY-MM-DD`. File này là input đầu vào quan trọng nhất cho phần làm sạch (Cleaning) của Thành viên 2.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Lấy dữ liệu từ external API (Crossref) thường gặp rủi ro về Rate Limiting (mã lỗi 429), Server Error (5xx), và dữ liệu trả về không nhất quán (thiếu ngày, abstract bị dính thẻ JATS XML). Phần của tôi giải quyết việc tải dữ liệu an toàn, xử lý backoff, và bóc tách dữ liệu một cách linh hoạt không bị crash pipeline.

### Cách triển khai

1. **Gọi API & Retry**: Xây dựng hàm `_fetch_payload` sử dụng `requests`. Đọc header `Retry-After` nếu bị 429, hoặc dùng `Exponential Backoff` để retry. Truyền `User-Agent` kèm mail để được đưa vào polite pool.
2. **Robust Parsing**:
   - Khai báo Regular Expressions (`_JATS_TITLE_RE`, `_TAG_RE`) để làm sạch toàn bộ thẻ HTML và `<jats:title>` trong nội dung summary.
   - Hàm `_iso_date` fallback 3 cấp (year-month-day -> year-month-1 -> year-1-1) để parse ngày chuẩn ISO.
3. **Data Observability sớm**: Tạo file `ingest_log.json` để track xem có bao nhiêu bản ghi bị thiếu abstract, thiếu published date, hoặc duplicate DOI, giúp phát hiện sớm vấn đề chất lượng ngay từ khâu raw ingestion.

### Input, output và contract

| Thành phần                   | Mô tả                                                                                                                              |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| Input                          | Parameter cấu hình (`source_query`, `source_filter`, `max_results`) từ `Settings`                                         |
| Output                         | Danh sách đối tượng`PaperRecord` và 3 artifacts trong `data/raw/`                                                          |
| Module phụ thuộc             | `core.config.Settings`, `requests`                                                                                               |
| Module sử dụng output        | `src/ingestion/cleaning.py` (của Thành viên 2)                                                                                  |
| Điều kiện lỗi cần xử lý | Server trả 429, 500, 502, 503, 504. Các trường`title`, `DOI`, `abstract` bị null. `date-parts` bị thiếu tháng/ngày. |

### Cách xác minh

```bash
python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; fetch_source_records(load_settings())"
```

- **Kết quả mong đợi:** Gọi thành công API mà không bị chặn, lưu được 3 file JSON vào thư mục `data/raw/` mà không bị crash hay báo lỗi parse.
- **Kết quả thực tế:** Code in ra và trả về đúng 24 bản ghi, log ghi nhận đủ số bài thiếu/đủ dữ liệu.
- **Artifact/log:** `data/raw/crossref_records.json`, `data/raw/ingest_log.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Khi parse trường ngày xuất bản (`published`) từ Crossref, API trả về cấu trúc `date-parts` dạng mảng `[[year, month, day]]`, nhưng đôi khi mảng chỉ có `[[year, month]]` hoặc `[[year]]`.
- **Các phương án đã cân nhắc:**
  1. Dùng `datetime.strptime` và throw Exception nếu thiếu tháng/ngày. (Dễ code nhưng sẽ rớt bản ghi).
  2. Bỏ qua bản ghi nếu thiếu ngày/tháng. (Gây hụt số lượng dữ liệu).
  3. Dùng try-except fallback pad thêm số "1" vào tháng/ngày bị thiếu.
- **Phương án đã chọn:** Phương án 3 (vòng lặp fallback tuple).
- **Lý do:** Trade-off ở đây là Data Quality vs Yield (Độ phủ). Việc pad thêm ngày 1, tháng 1 cho các bản ghi thiếu thông tin giúp giữ lại bài báo quý giá cho RAG, và không làm crash pipeline, trong khi độ sai số về thời gian không đáng kể so với ngưỡng freshness 180 ngày.
- **Bằng chứng quyết định phù hợp:** `ingest_log.json` ghi nhận không có bản ghi nào bị drop do parse ngày bị lỗi (crash).

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Abstract của một số bài báo trả về từ Crossref bị dính chuỗi ký tự lạ `<jats:title>Abstract</jats:title>` và các thẻ JATS markup `<jats:p>`.
- **Lệnh hoặc bước tái hiện:** Chạy fetch data và quan sát trường `summary` trong file JSON xuất ra.
- **Nguyên nhân gốc:** Crossref cung cấp chuẩn JATS XML tích hợp bên trong trường string của JSON.
- **Cách xử lý:** Thêm thư viện `re` và `html` vào file `crossref.py`. Tạo regex `_JATS_TITLE_RE = re.compile(r"<jats:title>.*?</jats:title>", re.IGNORECASE | re.DOTALL)` và `_TAG_RE` để strip hoàn toàn mọi thẻ markup và unescape HTML entities.
- **Cách xác minh sau khi sửa:** Check lại field `summary` trong `crossref_records.json` thấy văn bản đã thành plain text gọn gàng.
- **Điều học được:** Không bao giờ tin tưởng hoàn toàn dữ liệu thô từ third-party API, luôn cần một bước sanitize (làm sạch) ngay lúc thu thập để tránh gãy cấu trúc lúc embed.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   Dữ liệu raw (JSON) được tải qua REST API -> bóc tách ra `PaperRecord` -> đưa vào `cleaning.py` lọc lỗi, chuẩn hóa chữ, tính `age_days` -> xuất ra CSV/JSON -> chạy qua `sentence-transformers` biến văn bản thành vector embeddings -> nạp vào `ChromaDB` (Vector Index).
2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   Được trích xuất từ dữ liệu sạch, mỗi câu hỏi trong Test Set đi kèm với 1 ground-truth context ID. Khi RAG truy vấn, ta kiểm tra context ID mà hệ thống truy xuất có khớp với ground-truth ID không để tính `retrieval_hit_rate` và dùng LLM-as-a-judge để đo độ chính xác câu trả lời so với ground_truth answer.
3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   - Quality checks: Kiểm tra tính đúng đắn/toàn vẹn cấu trúc tĩnh (như thiếu giá trị null, rỗng summary, trùng lặp DOI).
   - Freshness monitoring: Kiểm tra tính "tươi mới" theo thời gian thực tế (vd bài báo phải nhỏ hơn ngưỡng 180 ngày).
4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Để duy trì tính công bằng (A/B testing concept). Cùng một tập câu hỏi, ta mới thấy rõ việc thêm noise/corruption vào dữ liệu sẽ làm kết quả trả lời giảm sút ra sao, và khi repair lại thì có phục hồi được chất lượng cũ hay không.
5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   Thành công khi các bảng metric `repaired_metrics.json` có số điểm hit_rate và accuracy ngang bằng (hoặc gần sát) với `baseline_metrics.json`, và report freshness báo "Pass" trở lại.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân                                                        |
| ---------------------- | -------: | --------: | -------: | -------------------------------------------------------------------------------- |
| `retrieval_hit_rate` |      1.0 |      0.75 |      1.0 | Corrupted làm giảm khả năng truy xuất đúng context (từ 100% xuống 75%). |
| `mean_token_f1`      |      1.0 |     0.625 |      1.0 | Câu trả lời bị sai lệch/hallucination nhiều hơn khi dữ liệu bị lỗi.   |
| `judge_accuracy`     |      1.0 |     0.625 |      1.0 | LLM Judge đánh giá độ chính xác giảm mạnh do thiếu context đúng.     |
| `mean_judge_score`   |      5.0 |     3.875 |      5.0 | Điểm chất lượng trung bình giảm rõ rệt.                                 |
| Quality checks         |     Pass |      Fail |     Pass | Corrupted tạo ra 4 bản ghi rỗng summary và làm trùng lặp DOI.             |
| Freshness status       |     Pass |      Fail |     Pass | Corrupted sửa ngày khiến 5 bản ghi bị stale (cũ hơn 180 ngày).           |

### Kết luận từ số liệu

Hoàn thành hai chuỗi nguyên nhân–bằng chứng sau:

1. Dữ liệu lỗi (mất summary, cũ, trùng lặp) → Quality và Freshness signals chuyển sang Fail → Agent metrics (`retrieval_hit_rate` giảm còn 0.75, `mean_judge_score` giảm còn 3.875).
2. Tự động phục hồi (Repair) dữ liệu từ `crossref_response.json` (bản raw) → Quality/Freshness signals phục hồi thành Pass → Agent metrics phục hồi hoàn toàn 100% như Baseline.

**Corruption nào ảnh hưởng rõ nhất và vì sao?**

Việc làm rỗng (blank) summary và cắt ngắn title ảnh hưởng rõ nhất đến `retrieval_hit_rate`. Vì cơ chế RAG dựa vào semantic search (embedding), khi văn bản bị mất nội dung, vector bị nhiễu, khiến retriever không thể tìm thấy context đúng cho câu hỏi, dẫn đến LLM trả lời sai (hallucinate).

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về data pipeline:** Lỗi mạng hoặc giới hạn API (rate limit) là điều luôn xảy ra, nên retry mechanism và backoff phải luôn nằm trong pipeline chuẩn. Không bao giờ lưu đè dữ liệu raw gốc mà phải tạo version/lineage rõ ràng (`ingest_log.json`).
2. **Về data quality/observability:** Quá trình theo dõi chất lượng (observability) không chỉ ở bước cuối mà ngay từ lúc lấy dữ liệu thô (Ingestion) phải thống kê được có bao nhiêu bản ghi bị null, bị lỗi, bị rác.
3. **Về ảnh hưởng của data đến RAG agent:** RAG agent chỉ là phần ngọn, data là phần gốc. Nếu Ingestion lấy phải text chứa toàn JATS XML hay noise thì RAG sẽ trả lời sai lệch (Hallucination).

### Nếu có thêm thời gian

Tôi sẽ xây dựng cơ chế Pagination (lấy dữ liệu nhiều trang) dựa vào `cursor` của Crossref API thay vì chỉ lấy 1 trang với giới hạn 24 dòng (`max_results`), giúp mở rộng quy mô dữ liệu corpus của agent lớn hơn.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [X] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [X] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [X] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [X] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [X] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [X] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Lê Thành Nam
**Ngày xác nhận:** 2026-08-06
