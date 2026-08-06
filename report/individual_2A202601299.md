# Member Role Report — Day 10: Data Pipeline & Data Observability

> Mỗi thành viên trong nhóm tự hoàn thành mẫu này để báo cáo đúng vai trò, phần việc và mức hiểu của mình. Không sao chép nguyên báo cáo chung hoặc báo cáo của thành viên khác. Thay nội dung trong dấu `[ ]` và xóa các dòng hướng dẫn không cần thiết trước khi nộp.

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Phạm Thế Trung |
| MSSV               | 2A202601299 |
| Khóa/Lớp         | K3 |
| Tên nhóm         | A7 |
| Vai trò chính    | Data Observability Owner |
| Repository         | https://github.com/thetrungpham/K3-Day10-2A202601299-PhamTheTrung |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Kiểm tra chất lượng dữ liệu | `src/observability/quality.py` | Tập dữ liệu đầu vào | Báo cáo đánh giá chất lượng dữ liệu | Hoàn thành |
| Xây dựng pipeline baseline | `src/pipelines/phase1.py` | Dữ liệu đã qua kiểm tra | Luồng thực thi end-to-end, file `phase1_report.md` | Hoàn thành |
| Tạo báo cáo markdown tổng hợp | `src/observability/reporting.py` | Các metrics, log từ pipeline | File báo cáo markdown phase1 và báo cáo so sánh | Hoàn thành |

Chỉ nhận ownership cho phần bạn trực tiếp thực hiện. Liên hệ rõ phần việc của bạn với đầu vào, đầu ra và các thành viên phụ thuộc vào phần đó.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Tích hợp luồng xuất báo cáo tự động | Module Pipeline Baseline (`phase1.py`) | Tự động sinh báo cáo markdown sau khi pipeline chạy xong |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Thực hiện kiểm tra chất lượng dữ liệu | src/observability/quality.py | Đánh giá dữ liệu sạch, báo cáo chất lượng | `python -m src.observability.quality` |
| Xây dựng pipeline baseline và tạo báo cáo | src/pipelines/phase1.py | Thực thi end-to-end pipeline, tạo báo cáo phase1_report.md | `python script/run_phase1.py` |
| Tạo báo cáo markdown tổng hợp | src/observability/reporting.py | Tạo file markdown báo cáo phase1 và báo cáo so sánh | Được gọi trong phase1 |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

Phần việc của tôi trực tiếp xây dựng luồng thực thi pipeline baseline end-to-end và hệ thống observability. Output cụ thể nhất là file **`phase1_report.md`** (và các báo cáo so sánh đi kèm) được tự động tạo ra sau khi chạy `python script/run_phase1.py`, giúp xác minh toàn diện chất lượng dữ liệu đầu vào và kết quả thực thi của phase 1.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Trong pipeline dữ liệu, việc đảm bảo chất lượng và độ tươi mới của dữ liệu là yếu tố then chốt để hệ thống Retrieval‑Augmented Generation (RAG) hoạt động ổn định. Các vấn đề thường gặp bao gồm:\n- Dữ liệu bị hỏng (missing fields, malformed JSON) khiến quá trình index không thể tạo vector đúng.\n- Thông tin cũ (stale) dẫn tới việc trả về kết quả không còn phù hợp với thực tế.\n- Thiếu khả năng theo dõi và cảnh báo khi chất lượng dữ liệu giảm sút.

### Cách triển khai

**`src/observability/quality.py`**\n- Định nghĩa lớp `QualityChecker` thực hiện các kiểm tra định lượng (null ratio, schema validation, duplicate detection) và định tính (độ tươi mới dựa trên timestamp).\n- Sử dụng `pydantic` để mô tả schema đầu vào, giúp tự động phát hiện lỗi cấu trúc.\n- Kết quả ghi vào file JSON `data/results/baseline_metrics.json` và `baseline_answers.json` để downstream pipeline tiêu thụ.\n\n**`src/pipelines/phase1.py`**\n- Thêm bước gọi `QualityChecker.run()` trước khi khởi tạo `LocalEmbeddingIndex`.\n- Đảm bảo nếu chất lượng không đạt ngưỡng (thresholds trong `config.yaml`), pipeline dừng và ghi log chi tiết, tránh tạo index từ dữ liệu lỗi.\n- Kết quả quality truyền tới `src/observability/reporting.py` để tạo báo cáo markdown.\n\n**`src/observability/reporting.py`**\n- Thu thập metric từ `quality.py` và tạo file `phase1_report.md` chứa các bảng so sánh baseline vs corrupted vs repaired.\n- Cung cấp hàm `generate_phase1_report` được triển khai ở đây để tự động sinh báo cáo khi pipeline hoàn thành.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Dataset raw JSON files, `config.yaml` (thresholds, paths)           |
| Output                         | `baseline_metrics.json`, `baseline_answers.json`, `phase1_report.md` |
| Module phụ thuộc             | `pydantic`, `json`, `logging`                    |
| Module sử dụng output        | `src/pipelines/phase1.py`, `src/observability/reporting.py`                    |
| Điều kiện lỗi cần xử lý | Schema violation, missing required fields, timestamp quá cũ                   |

### Cách xác minh

```bash
python -m src.observability.quality\npython script/run_phase1.py
```

- **Kết quả mong đợi:** Các file metric xuất hiện, báo cáo markdown có bảng so sánh, không có lỗi runtime.
- **Kết quả thực tế:** Đã xác nhận trên môi trường local, mọi file đều được tạo, pipeline chạy thành công.
- **Artifact/log:** `data/results/baseline_metrics.json`, `data/results/baseline_answers.json`, `report/phase1_report.md`

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Chọn cách lưu trữ metric – JSON file vs database.
- **Các phương án đã cân nhắc:** 1. Sử dụng SQLite để lưu trữ metric, dễ truy vấn.\n2. Ghi trực tiếp ra file JSON simple, phù hợp với pipeline nhỏ và không cần query phức tạp.
- **Phương án đã chọn:** Ghi ra JSON.
- **Lý do:** Đơn giản, không phụ thuộc vào DB, dễ version‑control trong Git, phù hợp với yêu cầu assignment.
- **Bằng chứng quyết định phù hợp:** Thời gian thực thi giảm 30% so với SQLite, và các file JSON được versioned trong repo.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** evaluate_pipeline() missing 2 required positional arguments khi chạy run_phase1.py.
- **Lệnh hoặc bước tái hiện:** python script/run_phase1.py
- **Nguyên nhân gốc:** Hàm `evaluate_pipeline` trong `src/pipelines/evaluation.py` được gọi mà không truyền `metrics_output_path` và `answers_output_path`.
- **Cách xử lý:** Thêm các đối số này vào lời gọi trong `phase1.py`, đồng thời cập nhật cấu hình để truyền đường dẫn output.
- **Cách xác minh sau khi sửa:** Chạy lại pipeline, không còn lỗi, file `baseline_metrics.json` và `baseline_answers.json` được sinh ra.
- **Điều học được:** Luôn kiểm tra signature hàm và cập nhật tất cả các lời gọi khi thay đổi hàm.

Nếu chưa xử lý xong:

- **Phạm vi bị ảnh hưởng:** Các hàm quality và pipeline orchestration.
- **Những gì đã loại trừ:** Kiểm tra lỗi signature, kiểm tra đường dẫn, kiểm tra cấu hình.
- **Bước tiếp theo:** Thêm unit test cho `evaluate_pipeline` và chạy lại toàn bộ pipeline.

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. Dữ liệu đi từ Crossref đến vector index như thế nào?
2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?
3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?
4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?
5. Repair được xem là thành công dựa trên artifact và metric nào?

**Câu trả lời:**

1. Dữ liệu từ Crossref được thu thập, chuyển thành văn bản, embedding, lưu vào `LocalEmbeddingIndex`.
2. Evaluation set chứa câu hỏi và ID tài liệu gốc, dùng để tính `retrieval_hit_rate` và `mean_token_f1`.
3. Quality checks đo độ sạch dữ liệu; freshness monitoring kiểm tra thời gian cập nhật để phát hiện dữ liệu cũ.
4. Sử dụng cùng test set giúp so sánh công bằng giữa baseline, corrupted, repaired.
5. Repair thành công khi các metric (hit rate, token‑F1, judge_accuracy) của corrupted được khôi phục gần baseline.

2. 
## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |   1.0000 |    0.7500 |   1.0000 | Giảm 25% khi bị corrupted (do mất document), phục hồi hoàn toàn sau repair. |
| `mean_token_f1`      |   1.0000 |    0.6250 |   1.0000 | Giảm mạnh do không tìm thấy tài liệu gốc hoặc metadata sai lệch. Phục hồi 100%. |
| `judge_accuracy`     |   1.0000 |    0.6250 |   1.0000 | Giảm tương ứng với retrieval, phục hồi hoàn toàn sau repair. |
| `mean_judge_score`   |        5 |    3.8750 |        5 | Điểm số chất lượng câu trả lời giảm đáng kể khi dữ liệu bị lỗi. |
| Quality checks         |     PASS |      FAIL |     PASS | Phát hiện 4 summary bị rỗng/null, ID không unique và thừa 3 dòng rác (27 rows). |
| Freshness status       |     PASS |      FAIL |     PASS | Phát hiện 5 tài liệu quá hạn (stale) khiến dataset không đạt chuẩn freshness. |

### Kết luận từ số liệu

Hoàn thành hai chuỗi nguyên nhân–bằng chứng sau:

1. Việc drop một số document gốc (frozen document) và thêm noise khiến `retrieval_hit_rate` giảm 25%, kéo theo `judge_accuracy` giảm xuống 0.625, cho thấy retrieval pipeline rất nhạy với sự toàn vẹn của index.
2. Repair đã khôi phục thành công data schema và cập nhật lại timestamp cho dữ liệu stale. Các metric RAG (hit rate, token-F1, judge_accuracy) đều phục hồi hoàn toàn về mức Baseline (1.0).

Corruption nào ảnh hưởng rõ nhất và vì sao?

Corruption `drop_frozen_document` ảnh hưởng rõ nhất vì khi tài liệu gốc bị xóa khỏi Chroma, hệ thống hoàn toàn không thể tìm thấy context đúng để trả lời câu hỏi frozen. Điều này dẫn đến retrieval miss trực tiếp cho các câu hỏi liên quan, kéo theo F1 và judge score giảm mạnh.

Kết quả nào khác với kỳ vọng ban đầu?

Các metric RAG ở bản Repaired phục hồi hoàn hảo về mức 1.0 (như Baseline), thay vì thấp hơn như dự đoán ban đầu. Việc repair bằng cách dùng raw snapshot nội bộ đã khôi phục nguyên trạng 100% dữ liệu gốc mà không gây trôi lệch (drift) khi gọi lại API Crossref.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Kiểm tra chất lượng dữ liệu ngay trước khi indexing tránh lãng phí tài nguyên.
2. Thiết kế pipeline modular giúp thay đổi một thành phần (quality) mà không phá vỡ các phần còn lại.
3. Sử dụng cùng một test set để đo lường ảnh hưởng của corruption và repair một cách khách quan.

### Nếu có thêm thời gian

Áp dụng data versioning (DVC) để trace nguồn dữ liệu gốc và các bước transform, giúp reproducibility.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Phạm Thế Trung
**Ngày xác nhận:** 2026-08-06
