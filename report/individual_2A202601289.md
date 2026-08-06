# Member Role Report — Day 10: Data Pipeline & Data Observability

> **Trạng thái báo cáo:** Hoàn thành. Mọi số liệu trong Mục 8 đọc từ artifact thực tế do nhóm chạy ngày 2026-08-06 (`baseline` lúc 11:45, `corruption flow` lúc 12:16). Không có số phỏng đoán.

## 1. Thông tin cá nhân

| Thông tin           | Nội dung                                                                    |
| ------------------- | --------------------------------------------------------------------------- |
| Họ và tên           | Chu Phú Thành                                                               |
| MSSV                | 2A202601289                                                                 |
| Khóa/Lớp            | K3                                                                          |
| Tên nhóm            | A7                                                                          |
| Vai trò chính       | Thành viên 2 — Data Model & Evaluation Set Owner                             |
| Repository          | https://github.com/thetrungpham/K3-Day10-2A202601299-PhamTheTrung            |
| Ngày hoàn thành     | 2026-08-06                                                                  |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable       | File/hàm phụ trách                                                                       | Input nhận vào                                              | Output bàn giao                                                                              | Trạng thái   |
| ------------------------ | ---------------------------------------------------------------------------------------- | ----------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ------------ |
| Cleaning & data modeling | `src/ingestion/cleaning.py` — `build_clean_dataframe()`, `save_clean_dataset()`           | `list[PaperRecord]` từ `data/raw/crossref_records.json` (TV1) | `data/clean/papers_clean.json`, `papers_clean.csv`, `papers_clean_log.json` — schema 16 cột    | Hoàn thành   |
| Evaluation set           | `src/evaluation/testset.py` — `build_test_set()`                                          | Cleaned DataFrame                                            | `data/eval/test_set.json` — 16 sample (4 paper × 4 loại câu hỏi)                              | Hoàn thành   |

Commit tương ứng:

- `5804be4` — `day file clean` (cleaning.py + 3 clean artifacts)
- `4c4765f` — `Day testset.py va testset.json` (testset.py + test_set.json)

Tôi **không** nhận ownership cho `crossref.py` (TV1), `quality.py`/`reporting.py` (TV3), `corruption.py`/`phase1.py`/`corruption_flow.py` (TV4). Hai file có sẵn `metrics.py` và `qa.py` tôi chỉ đọc hiểu để thiết kế test set khớp contract, không sửa.

**Một điểm về thiết kế interface trong phạm vi của tôi:** `save_clean_dataset()` được viết với `csv_path`/`json_path` là tham số tùy chọn (mặc định trỏ về path baseline), thay vì gán cứng đường dẫn baseline. Chủ đích là để cùng một hàm ghi được cả corrupted và repaired dataset. Thiết kế này đã được dùng lại trong thực tế: TV4 gọi `save_clean_dataset()` hai lần trong `corruption_flow.py` — dòng 222 cho corrupted dataset và dòng 270 cho repaired dataset (`csv_path=paths.repaired_clean_csv`, `json_path=paths.repaired_clean_json`). Nhờ vậy `papers_clean_log.json`, `papers_corrupted_log.json` và `papers_clean_repaired_log.json` có cùng cấu trúc, so sánh được với nhau.

### Việc hỗ trợ ngoài phạm vi chính

**Không có.** Tôi chưa thực hiện hoạt động hỗ trợ nào ngoài hai file mình sở hữu — không debug hộ module của thành viên khác, không viết tài liệu chung, và **chưa gửi tài liệu bàn giao contract nào cho nhóm**.

Ghi chú trung thực về hệ quả: hai rủi ro tích hợp mà tôi nhận diện được trong lúc làm nhưng không truyền đạt cho nhóm là (1) `to_csv` phá cột list nên phải đọc lại bằng JSON, và (2) corrupt `title`/`summary`/`published` thì phải rebuild `text_for_embedding`. TV4 xử lý được **cả hai một cách độc lập** — `_load_clean_dataframe()` đọc `paths.clean_json` chứ không đọc CSV, và `corruption.py:259` rebuild `text_for_embedding` bằng hàm `_embedding_text` do TV4 tự viết. Nghĩa là hai rủi ro này không gây sự cố, nhưng đó là nhờ TV4 tự nhận ra, không phải nhờ tôi bàn giao. Đây là điểm tôi cần cải thiện về phối hợp.

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện                                    | File/hàm/artifact liên quan                       | Kết quả bàn giao                                                    | Cách xác minh                                                                          |
| -------------------------------------------------------- | ------------------------------------------------- | ------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Chuẩn hóa raw records thành clean schema 16 cột           | `cleaning.py::build_clean_dataframe`              | DataFrame `(24, 16)`, `paper_id` unique, sort `published` mới→cũ     | Chạy hàm trên `crossref_records.json`, in `df.shape` và `df.dtypes`                     |
| Strip markup XML/HTML, chuẩn hóa whitespace              | `cleaning.py::_strip_markup`                      | Không còn tag `<jats:p>`, không còn double space trong `title`        | `df['title'].str.contains('  ').any()` → `False`                                        |
| Parse ngày về `YYYY-MM-DD`, tính `age_days`               | `cleaning.py::_parse_dates`                       | `age_days` dtype `int64`, không NaN, không giá trị âm                | In `df[['published','updated','age_days']]` và đếm NaN/negative → `0`                   |
| Loại record xấu + dedupe, có log truy vết                 | `cleaning.py::_filter_rows`                       | `papers_clean_log.json`: `rows_in: 24 → rows_out: 24`, mọi lý do = 0 | Đọc `df.attrs['cleaning_log']`                                                          |
| Tạo `text_for_embedding` 5 field                          | `cleaning.py::_build_text_for_embedding`          | Không row nào rỗng, độ dài tối thiểu > 500 ký tự                     | `(df['text_for_embedding'].str.strip() == '').sum()` → `0`                               |
| Ghi 3 clean artifacts                                     | `cleaning.py::save_clean_dataset`                 | `papers_clean.json` (111 KB), `.csv` (96 KB), `_log.json`             | `ls data/clean` — 3 file tồn tại                                                        |
| Chọn 4 paper đại diện, loại paper không dùng được          | `testset.py::_is_usable`, `_select_papers`         | 23/24 paper dùng được; chọn 2 mới nhất + 2 cũ nhất                   | In `usable` count và 4 dòng `paper_id`/`published`                                      |
| Sinh 16 sample đúng schema `metrics.py`                   | `testset.py::_build_samples`, `_validate`          | `data/eval/test_set.json` — 16 sample, 6602 bytes                    | `samples: 16 \| file: True 6602 bytes`                                                  |
| Kiểm câu hỏi khớp pattern nhận diện của `qa.py`            | `testset.py::QUESTION_TEMPLATES`                  | Không câu nào sai trigger, không câu `summary` bị trigger nhầm        | Script kiểm trigger → `sai trigger: [] \| summary trigger nham: [] \| quoted title: True` |

Nêu một output cụ thể mà phần việc của tôi tạo ra hoặc giúp xác minh:

`data/clean/papers_clean_log.json` — không chỉ là dữ liệu mà là **bằng chứng truy vết**. Nó ghi `rows_in: 24`, `rows_out: 24`, và 5 lý do loại record đều bằng `0`, cùng `min_summary_chars: 100`. Nghĩa là với dữ liệu Crossref lấy được ngày 2026-08-06, mọi luật làm sạch đều được áp dụng nhưng không record nào bị loại — và điều này **kiểm chứng được**, chứ không phải khẳng định suông. Các con số trong log được tính sao cho tổng các lý do loại luôn bằng `rows_in - rows_out` (dùng mask loại trừ lẫn nhau), nên TV3 viết report không gặp số liệu vô lý.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Dữ liệu Crossref không có schema ổn định: abstract là JATS XML, `author` lồng trong dict (`given`/`family` hoặc `name` cho tổ chức), `subject` thường rỗng, ngày xuất bản là `date-parts` có thể chỉ có năm. Trong khi đó `LocalEmbeddingIndex` (code có sẵn) truy cập **9 cột theo tên cứng**, và ChromaDB chỉ nhận metadata kiểu `str/int/float/bool` — một `NaN` là vỡ cả bước index.

Phần thứ hai: evaluation cần một bộ câu hỏi có ground truth **kiểm chứng được**, dùng chung cho cả 3 trạng thái baseline/corrupted/repaired, và ground truth phải khớp với định dạng câu trả lời mà hệ thống thật sự sinh ra.

### Cách triển khai

**`cleaning.py` — 7 lớp xử lý tuần tự trong `build_clean_dataframe`:**

1. `asdict()` từng `PaperRecord` → DataFrame 11 cột.
2. `_normalize_text`: `paper_id` về lowercase (để dedupe không bỏ sót DOI khác hoa/thường); `_strip_markup` bỏ tag XML/HTML + `html.unescape` + gom whitespace cho 6 cột text; cột list (`authors`, `categories`) xử lý riêng qua `.map()` vì không dùng được accessor `.str` của pandas.
3. `_parse_dates`: `pd.to_datetime(..., utc=True, errors="coerce")` rồi format lại `%Y-%m-%d`; `age_days = (run_date - published).dt.days.clip(lower=0)`.
4. `_add_helper_columns`: `authors_joined`, `categories_joined` (dùng `compact_join` của project để format nhất quán với `crossref.py`), `summary_chars`.
5. `_filter_rows`: loại row thiếu `paper_id`/`title`/`published`, hoặc `summary_chars < 100`; dedupe theo `paper_id`; **mỗi lý do được đếm với mask loại trừ** (`mask & ~drop_mask`) nên các con số không đếm trùng.
6. `_build_text_for_embedding`: ghép `Title | Authors | Categories | Published | Summary`, bỏ field rỗng.
7. `_finalize`: sort theo timestamp rồi xóa cột tạm, ép `age_days`/`summary_chars` về `int`, `fillna("")` cho 9 cột metadata Chroma, và áp `CLEAN_COLUMN_ORDER` — biến schema thành hợp đồng tường minh, thiếu cột là `KeyError` ngay tại đây thay vì lỗi mơ hồ ở bước embedding của TV4.

**`testset.py` — sinh test set khớp contract của hai module có sẵn:**

Điểm cốt lõi là `qa.py::answer_question` **không phải LLM** mà là bộ trích xuất tất định: nó dò cụm từ trong câu hỏi rồi trả về **nguyên văn một field metadata**. Vì vậy:

- Mỗi template chứa đúng cụm trigger: `who authored` → `authors_joined`, `when was` → `published`, `what categories` → `categories_joined`; câu `summary` cố ý **không** chứa cụm nào để rơi vào nhánh mặc định `first_sentence(summary)`.
- `ground_truth` được sinh **từ chính cột tương ứng của cùng row đó**, và loại `summary` dùng lại hàm `first_sentence` của project — cùng một hàm mà `qa.py` gọi. Nhờ vậy khi retrieval đúng thì `ground_truth` và `answer` khớp nhau, `token_f1` đạt trần của thiết kế.
- Title đặt trong **dấu nháy đơn** để kích hoạt nhánh exact-lookup của `qa.py`. Kéo theo: paper có `'` trong title bị loại khỏi test set, vì dấu đó phá regex `r"'([^']+)'"`.
- Chọn 4 paper: 2 mới nhất + 2 cũ nhất. Có chủ đích — corruption "drop latest records" của TV4 phải đánh trúng test set mới đo được impact; 2 paper cũ làm nhóm đối chứng.
- Loại paper không dùng chữ Latin bằng cách đếm **tỉ lệ chữ cái ASCII ≥ 90%** thay vì chặn mọi ký tự non-ASCII — cách sau sẽ loại oan title tiếng Anh có gạch ngang `–` hoặc nháy cong `'`.

### Input, output và contract

| Thành phần                  | Mô tả                                                                                                                                                                                                                                              |
| --------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Input                       | `list[PaperRecord]` (11 field) + `run_date` tz-aware UTC → cho cleaning. Cleaned DataFrame → cho test set.                                                                                                                                          |
| Output                      | DataFrame 16 cột (`CLEAN_COLUMN_ORDER`) + `df.attrs["cleaning_log"]`; 3 file trong `data/clean/`; `list[dict]` 5 key + `data/eval/test_set.json`                                                                                                     |
| Module phụ thuộc            | `ingestion/crossref.py` (`PaperRecord`, `load_raw_records`), `core/utils.py` (`normalize_whitespace`, `compact_join`, `first_sentence`, `write_csv`, `write_json`), `core/config.py` (`Settings`, `Paths`)                                            |
| Module sử dụng output       | `retrieval/index.py` (đọc 9 cột metadata), `retrieval/qa.py` (đọc metadata để sinh answer), `evaluation/metrics.py` (đọc 5 key của test set), `observability/quality.py` (đọc `age_days`, `summary_chars`), `ingestion/corruption.py` (corrupt clean df) |
| Điều kiện lỗi cần xử lý     | (1) `run_date` tz-aware trừ `published` tz-naive → `TypeError`; (2) ngày không parse được → `NaT`; (3) `NaN` trong metadata → Chroma từ chối; (4) toàn bộ record bị lọc hết; (5) `paper_id` trùng; (6) `ground_truth` rỗng; (7) `ground_truth_doc_ids` trỏ tới `paper_id` không tồn tại |

### Cách xác minh

```bash
# 1. Clean pipeline + ghi artifacts
uv run python -c "from core.config import load_settings; from core.utils import now_utc; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe, save_clean_dataset; s = load_settings(); df = build_clean_dataframe(load_raw_records(s.paths.raw_records_json), now_utc()); log = save_clean_dataset(df, s); print('shape:', df.shape); print(df[['age_days','summary_chars']].dtypes.to_string()); print('published dau/cuoi:', df['published'].iloc[0], '->', df['published'].iloc[-1]); print('log rows_out:', log['rows_out'])"

# 2. Sinh test set (validate truoc khi ghi file)
uv run python -c "import importlib.util as u, pandas as pd; from pathlib import Path; s = u.spec_from_file_location('ts', 'src/evaluation/testset.py'); m = u.module_from_spec(s); s.loader.exec_module(m); df = pd.read_json('data/clean/papers_clean.json', convert_dates=False); out = Path('data/eval/test_set.json'); ts = m.build_test_set(df, out); print('samples:', len(ts), '| file:', out.exists(), out.stat().st_size, 'bytes')"

# 3. Kiem cau hoi co khop pattern nhan dien cua qa.py
uv run python -c "import json; ts = json.load(open('data/eval/test_set.json', encoding='utf-8')); trig = {'authors': 'who authored', 'date': 'when was', 'categories': 'what categories'}; bad = [x['id'] for x in ts if x['question_type'] in trig and trig[x['question_type']] not in x['question'].lower()]; leak = [x['id'] for x in ts if x['question_type'] == 'summary' and any(t in x['question'].lower() for t in trig.values())]; print('sai trigger:', bad, '| summary trigger nham:', leak, '| quoted title:', all(chr(39) in x['question'] for x in ts))"
```

- **Kết quả mong đợi:** clean DataFrame `(24, 16)`, `age_days`/`summary_chars` kiểu `int64`, `published` sắp mới→cũ, log `rows_out = 24`; test set 16 sample ghi ra file; không câu hỏi nào sai trigger.
- **Kết quả thực tế:**
  - Lệnh 1: `shape: (24, 16)`, `age_days int64`, `summary_chars int64`, `published dau/cuoi: 2026-08-01 -> 2026-02-12`, `log rows_out: 24`
  - Lệnh 2: `samples: 16 | file: True 6602 bytes`
  - Lệnh 3: `sai trigger: [] | summary trigger nham: [] | quoted title: True`
- **Artifact/log:** `data/clean/papers_clean.json`, `data/clean/papers_clean.csv`, `data/clean/papers_clean_log.json`, `data/eval/test_set.json`. Không chứa secret; `.env` nằm trong `.gitignore` và chưa từng được commit (kiểm bằng `git log --all -- .env` → rỗng).

**Xác minh ở mức tích hợp:** ba lệnh trên kiểm chứng ở mức từng hàm. Mức tích hợp đã được xác nhận sau khi TV4 chạy `run_phase1.py`:

- **ChromaDB nhận đủ 9 cột metadata** — `data/embeddings/papers_embeddings.json` được ghi ra với đủ 24 document, không lỗi ở bước `collection.add()`. Việc `fillna("")` cho `METADATA_TEXT_COLUMNS` đã làm đúng nhiệm vụ (nhiều record có `pdf_url` rỗng).
- **`ground_truth_doc_ids` khớp `paper_id` do retrieval trả về** — `baseline_metrics.json` cho `retrieval_hit_rate = 1.0` trên cả 16 sample. Nếu tôi dùng sai định danh (ví dụ `record_id` dạng `doi::index`) thì giá trị này sẽ là `0.0`.
- **Test set được TV4 dùng đúng như đã khóa** — `data/results/corruption_log.json` ghi `frozen_test_set.loaded: true` và `overlap_count: 4`, liệt kê đúng 4 `paper_id` tôi chọn. Xác nhận cả ba trạng thái đều đánh giá trên cùng một test set.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Đề bài mô tả `text_for_embedding` gồm 3 field theo dạng `Title: [title] | Authors: [authors] | Summary: [summary]`. Nhưng TV4 sẽ tạo corruption bằng cách làm cũ `published` date và làm nhiễu `categories`. Nếu 2 field đó không nằm trong text được embed thì các corruption ấy **hoàn toàn vô hình với retrieval**, và nhóm không chứng minh được impact ở Mục 8 của Rubric.
- **Các phương án đã cân nhắc:**
  1. Đúng đề bài, 3 field (`Title`, `Authors`, `Summary`), phân cách `" | "` — an toàn nhất nếu người chấm so khớp format theo chữ, nhưng mất khả năng đo 2 loại corruption.
  2. 5 field phân cách bằng ký tự xuống dòng — đọc dễ khi audit nhưng lệch dấu phân cách so với đề bài.
  3. 5 field (`Title`, `Authors`, `Categories`, `Published`, `Summary`) phân cách `" | "` — giữ đúng dấu phân cách của đề bài, đồng thời là tập cha của yêu cầu.
- **Phương án đã chọn:** Phương án 3.
- **Lý do:** Đề bài nêu mức tối thiểu, không cấm thêm field. Giữ `" | "` để khớp định dạng được yêu cầu; thêm `Categories` và `Published` để corruption của TV4 để lại dấu vết đo được. Đánh đổi là text dài hơn một chút — không đáng kể với MiniLM (`all-MiniLM-L6-v2`) trên 24 document, và bù lại giữ được năng lực đo lường của cả bài lab. Mỗi field vẫn có nhãn nên text đọc được bằng mắt khi cần audit.
- **Bằng chứng quyết định phù hợp — và giới hạn của nó:** `text_for_embedding` có độ dài tối thiểu > 500 ký tự, không row nào rỗng, chứa cả 5 nhãn, và ChromaDB nạp được toàn bộ 24 document.

  Tuy nhiên số liệu thực tế cho thấy **quyết định này chưa được chứng minh là cần thiết**. TV4 làm cũ ngày của `10.35314/3y9hy151` (paper p3) từ `2026-02-26` về `2000-01-01`. Corruption đó **có** bị phát hiện — `p3-date` tụt từ `token_f1 = 1.00` xuống `0.00` — nhưng phát hiện qua **giá trị metadata `published` mà `qa.py` trả về**, không phải qua embedding: `p3-date` vẫn `retrieval_hit = True`. Nói cách khác, câu hỏi loại `date` tự bắt được lỗi này mà không cần `Published` nằm trong `text_for_embedding`.

  Kết luận trung thực: việc thêm `Categories` và `Published` không gây hại và không làm sai lệch gì, nhưng trong lần chạy này nó **không tạo thêm năng lực phát hiện nào đo được**. Lý do sâu hơn nằm ở chỗ khác — xem phân tích shortcut exact-lookup ở Mục 8 và đề xuất ở Mục 9.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Không phải exception. Mỗi lần chạy lệnh kiểm tra `testset.py`, terminal treo khoảng 30 giây trước khi in kết quả — ban đầu tưởng máy chậm.
- **Lệnh hoặc bước tái hiện:**
  ```bash
  uv run python -c "from evaluation.testset import _is_usable, _select_papers; print('ok')"
  ```
- **Nguyên nhân gốc:** `src/evaluation/__init__.py` dòng 1 có `from .metrics import EvaluationBundle, JudgeVerdict, evaluate_pipeline`. Nên bất kỳ import nào dạng `from evaluation.testset import ...` cũng buộc Python nạp `metrics.py` trước, mà file đó import `datasets`, `retrieval.index` (→ `chromadb`), `retrieval.llm` (→ `langchain_*`) và `retrieval.embeddings` (→ `sentence-transformers`/`torch`). Trong khi `testset.py` chỉ cần `pandas`. Đây là vấn đề import chain của package, không phải hiệu năng máy.
- **Cách xử lý:** Không sửa `__init__.py` (file dùng chung, sửa sẽ ảnh hưởng TV4). Thay vào đó khi test cục bộ thì nạp thẳng module file, bỏ qua `__init__`:
  ```bash
  uv run python -c "import importlib.util as u; s = u.spec_from_file_location('ts', 'src/evaluation/testset.py'); m = u.module_from_spec(s); s.loader.exec_module(m); print('ok')"
  ```
- **Cách xác minh sau khi sửa:** Đo bằng `time` — bản nạp trực tiếp chạy **1.2 giây** so với khoảng 30 giây của bản import qua package. Kết quả in ra giống hệt nhau.
- **Điều học được:** `__init__.py` gom import cho tiện dùng nhưng biến mọi module trong package thành phụ thuộc nặng của nhau. Khi debug một module nhỏ, nạp trực tiếp file là cách tách phụ thuộc mà không phải sửa code dùng chung. Trong pipeline thật thì import nặng này vẫn xảy ra, nhưng chỉ một lần, nên không cần tối ưu.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

**1. Dữ liệu đi từ Crossref đến vector index như thế nào?**

Đầu tiên `crossref.py` gọi API Crossref lấy 24 bài báo, và lưu response gốc vào `data/raw/crossref_response.json` **trước khi** parse. Lúc đầu tôi không hiểu tại sao phải lưu bản thô đó, sau mới thấy nó chính là chỗ để repair ở cuối bài — muốn phục hồi thì phải có bản gốc để quay về.

Sau đó phần của tôi là `cleaning.py`: dọn text, đổi ngày về `YYYY-MM-DD`, tính `age_days`, và ghép cột `text_for_embedding`. Cuối cùng `index.py` lấy đúng cột `text_for_embedding` đó đưa qua model MiniLM để biến thành vector, còn các cột khác thì gắn làm metadata, rồi lưu vào ChromaDB.

Điều tôi thấy thú vị: model MiniLM chạy ngay trên máy, không gọi API. Nên bước embedding không tốn tiền và không cần mạng.

**2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**

Đây là hai thứ khác nhau mà lúc đầu tôi tưởng là một.

`ground_truth_doc_ids` dùng để đo **tìm có đúng bài không**. Hệ thống trả về danh sách `paper_id`, đem so với list này, trùng thì tính là hit. Chỗ này tôi phải cẩn thận: trong index còn có `record_id` dạng `doi::0`, nếu tôi ghi nhầm cái đó thì hit rate sẽ ra 0 dù tìm đúng bài.

`ground_truth` dùng để đo **trả lời có đúng không**, bằng `token_f1` (so số từ trùng nhau) và bằng LLM judge cho điểm 1–5.

Một điều tôi phát hiện khi đọc code và thấy khá bất ngờ: cái được đem đi chấm điểm **không phải agent LLM**. `metrics.py` gọi `qa.py`, mà `qa.py` chỉ dò từ khóa trong câu hỏi rồi trả về nguyên một field metadata, không hề gọi Gemini. Agent LLM thật chỉ chạy ở phần demo cuối. Vì vậy `ground_truth` của tôi phải khớp nguyên văn field đó — nếu tôi viết lại thành câu cho "khó hơn" thì F1 sẽ thấp, nhưng thấp vì ground truth lệch chứ không phải vì hệ thống sai.

**3. Quality checks khác freshness monitoring ở điểm nào?**

Quality checks hỏi "dữ liệu có **đúng** không": đủ số dòng không, `paper_id` có trùng không, `title` có rỗng không, `summary` có quá ngắn không. Những cái này hôm nay kiểm hay tháng sau kiểm cũng cho kết quả như nhau.

Freshness hỏi "dữ liệu có **còn mới** không", dựa vào `age_days` so với ngưỡng 180 ngày. Cái này phụ thuộc thời điểm chạy — cùng một file, hôm nay `is_fresh: true` nhưng vài tháng sau có thể thành `false` mà không ai sửa gì cả.

Số liệu của nhóm cho thấy rõ hai cái này bắt hai loại lỗi khác nhau: xóa trắng summary thì quality check bắt được (`summary_empty_or_null: 4`), còn làm cũ ngày xuất bản thì quality check không thấy gì — chỉ freshness thấy (`stale_rows: 0 → 5`). Nên phải có cả hai, thiếu một cái là bỏ sót lỗi.

**4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**

Vì nếu đổi cả dữ liệu lẫn câu hỏi thì khi hit rate tụt từ 1.0 xuống 0.75, tôi không biết là do dữ liệu bị hỏng hay do bộ câu hỏi mới khó hơn. Muốn kết luận được thì chỉ được thay đổi một thứ.

Đó là lý do tôi ghi test set ra file cố định và không sửa nữa sau khi TV4 chạy baseline. Trong `corruption_log.json` có ghi `frozen_test_set.loaded: true` và `overlap_count: 4`, nghĩa là cả ba lần chạy đều dùng đúng 16 câu hỏi đó.

**5. Repair được xem là thành công dựa trên artifact và metric nào?**

Theo tôi hiểu thì cần đủ ba lớp, chỉ một lớp thì chưa chắc:

- **Dữ liệu:** `papers_clean_repaired.json` phải được tạo bằng cách chạy lại cleaning từ file raw, không phải copy hay sửa tay.
- **Signal:** quality từ fail về pass, freshness từ stale về fresh.
- **Metric:** 4 chỉ số trong `repaired_metrics.json` quay về mức baseline, đo trên cùng test set.

Nhóm tôi đạt cả ba: dữ liệu về 24 dòng với `paper_id_is_unique: true`, quality `false → true`, freshness `false → true`, và 4 metric về đúng `1.0 / 1.0 / 1.0 / 5.0`.

Có một chỗ tôi kiểm thêm vì thấy hơi lo: `metrics.py` có đoạn nếu gọi LLM bị lỗi (ví dụ hết quota) thì nó tự động chấm bằng cách khác mà **không báo gì**, số vẫn trông bình thường. Tôi đếm chuỗi `Fallback heuristic` trong file answers thì được `0/16` ở cả ba trạng thái, nên điểm judge là điểm LLM thật. Nếu không kiểm chỗ này thì có thể báo cáo sai mà không biết.

## 8. Phân tích kết quả

Nguồn số liệu: `data/results/{baseline,corrupted,repaired}_metrics.json`, `data/quality/*.json`, `data/results/corruption_log.json`, và 48 sample answer trong `data/results/*_answers.json`. Cả ba trạng thái đánh giá trên cùng `data/eval/test_set.json` (16 sample).

### Metrics chính

| Metric/signal        | Baseline | Corrupted | Repaired | Nhận xét của cá nhân                                                                                            |
| -------------------- | -------: | --------: | -------: | --------------------------------------------------------------------------------------------------------------- |
| `retrieval_hit_rate` |    1.000 |     0.750 |    1.000 | Mất đúng 4/16 sample — toàn bộ 4 câu của p1, paper duy nhất bị xóa khỏi index                                     |
| `mean_token_f1`      |    1.000 |     0.625 |    1.000 | 6/16 sample về `0.00`: p1×4 (mất document), `p2-summary` (summary bị xóa), `p3-date` (ngày bị làm cũ)              |
| `judge_accuracy`     |    1.000 |     0.625 |    1.000 | Trùng khít 10/16 sample còn `token_f1 = 1.00` → LLM judge nhất quán với token F1, không có sample nào lệch hướng   |
| `mean_judge_score`   |    5.000 |     3.875 |    5.000 | Điểm của 6 sample xấu lần lượt là `3, 1, 2, 2, 3, 1`; 10 sample còn lại đều `5`                                    |
| Quality checks       |  `passed: true` | `passed: false` | `passed: true` | Corrupted vi phạm 3 điều kiện: `paper_id_is_unique: false`, `summary_empty_or_null: 4`, `stale_count: 5`; `row_count` 24 → 27 |
| Freshness status     |  `is_fresh: true` | `is_fresh: false` | `is_fresh: true` | `oldest_published` 2026-02-12 → **2000-01-01**, `stale_rows` 0 → 5, `latest_published` 2026-08-01 → 2026-07-13 |

**Judge là LLM thật, không phải fallback.** Kiểm bằng cách đếm chuỗi `Fallback heuristic` trong `judge.reasoning` của cả ba file answers: `0/16` ở cả baseline, corrupted và repaired. Nên `judge_accuracy` và `mean_judge_score` là điểm do Gemini chấm, không phải heuristic token F1 thay thế.

**Repaired trùng khớp baseline tuyệt đối** — cả 4 metric và cả 6 field trong quality/freshness report đều bằng đúng giá trị baseline. Đây là hồi phục hoàn toàn, không phải hồi phục một phần.

### Bằng chứng ở mức từng sample

Đây là phần liên quan trực tiếp tới phần việc của tôi, vì `id` của sample được tôi thiết kế theo dạng `p{n}-{loại}` chính là để đọc được bảng này:

| Sample          | Baseline hit / F1 | Corrupted hit / F1 | Judge | Corruption đã tác động            |
| --------------- | ----------------- | ------------------ | ----: | --------------------------------- |
| `p1-summary`    | ✅ / 1.00          | ❌ / 0.00           |     3 | `drop_frozen_document`            |
| `p1-authors`    | ✅ / 1.00          | ❌ / 0.00           |     1 | `drop_frozen_document`            |
| `p1-date`       | ✅ / 1.00          | ❌ / 0.00           |     2 | `drop_frozen_document`            |
| `p1-categories` | ✅ / 1.00          | ❌ / 0.00           |     2 | `drop_frozen_document`            |
| `p2-summary`    | ✅ / 1.00          | ✅ / **0.00**       |     3 | `blank_summary`                   |
| `p2-authors`    | ✅ / 1.00          | ✅ / 1.00           |     5 | —                                 |
| `p2-date`       | ✅ / 1.00          | ✅ / 1.00           |     5 | —                                 |
| `p2-categories` | ✅ / 1.00          | ✅ / 1.00           |     5 | —                                 |
| `p3-date`       | ✅ / 1.00          | ✅ / **0.00**       |     1 | `stale_date`                      |
| `p3-summary`    | ✅ / 1.00          | ✅ / 1.00           |     5 | —                                 |
| `p3-authors`    | ✅ / 1.00          | ✅ / 1.00           |     5 | —                                 |
| `p3-categories` | ✅ / 1.00          | ✅ / 1.00           |     5 | —                                 |
| `p4-*` (cả 4)   | ✅ / 1.00          | ✅ / 1.00           |     5 | `add_embedding_noise` + `duplicate_rows` — **không tác động** |

Điểm đáng chú ý: `p2-summary` và `p3-date` **vẫn hit** nhưng `token_f1` về `0.00`. Đó là hai loại corruption làm hỏng **nội dung** chứ không làm mất **document** — retrieval vẫn tìm đúng paper, nhưng câu trả lời lấy ra đã sai. Nếu chỉ nhìn `retrieval_hit_rate` thì hai lỗi này gần như vô hình (0.75 chỉ phản ánh p1); phải nhìn `mean_token_f1` mới thấy.

### Kết luận từ số liệu

1. **`drop_frozen_document` trên `10.2118/234689-pa`** (p1, paper mới nhất, `published: 2026-08-01`) → `row_count` giảm và `paper_id` biến mất khỏi collection → cả 4 sample của p1 chuyển `retrieval_hit: false` → **`retrieval_hit_rate` 1.000 → 0.750** và `mean_token_f1` mất 4/16 điểm.
2. **`repair` chạy lại cleaning từ `data/raw/crossref_records.json`** → `row_count` 27 → 24, `paper_id_is_unique` false → true, `summary_empty_or_null` 4 → 0, `stale_count` 5 → 0, `is_fresh` false → true → **cả 4 metric hồi phục về đúng 1.000 / 1.000 / 1.000 / 5.000**. Vì repair đọc lại từ raw snapshot chứ không sửa tay, dữ liệu phục hồi được kiểm chứng chứ không phải khôi phục thủ công.

Corruption nào ảnh hưởng rõ nhất và vì sao?

**`drop_frozen_document` — chỉ xóa 1 record trên 24 mà làm mất 25% hit rate.** Nguyên nhân là thiết kế test set: tôi chọn 2 trong 4 paper là 2 paper mới nhất, nên corruption nhắm vào "latest records" chắc chắn đánh trúng. Một record bị mất kéo theo 4 sample sai (25% của bộ 16). Đây là bằng chứng cho thấy độ nhạy của phép đo **phụ thuộc vào cách chọn paper cho test set**, không chỉ vào mức độ nghiêm trọng của lỗi dữ liệu.

Xếp theo mức tác động lên metric: `drop_frozen_document` (4 sample) > `blank_summary` (1 sample) = `stale_date` (1 sample) > `add_embedding_noise` (0) = `duplicate_rows` (0).

Kết quả nào khác với kỳ vọng ban đầu?

**Hai điều.**

*Thứ nhất — `add_embedding_noise` và `duplicate_rows` không để lại dấu vết nào trên metric.* Cả hai đều nhắm vào `10.20944/preprints202602.0996.v1` (p4) theo `corruption_log.json`, nhưng cả 4 sample của p4 vẫn `hit = true` và `token_f1 = 1.00`. Giải thích: `qa.py` trả lời loại `summary` bằng `first_sentence(summary)` — nếu noise được nối vào **sau** câu đầu thì câu trả lời không đổi; còn `duplicate_rows` không gây hại vì `index.lookup()` trả về bản khớp đầu tiên. Nghĩa là **2 trong 5 loại corruption của nhóm hiện không đo được**, dù chúng có làm quality check fail (`paper_id_is_unique: false`). Đây là khoảng trống thật của phép đo, không phải lỗi của TV4.

*Thứ hai — `retrieval_hit_rate` baseline bằng 1.000, nhưng không chứng minh được semantic search tốt.* Vì tôi đặt title trong dấu nháy đơn, `qa.py:33` kích hoạt `index.lookup()` tra cứu chính xác theo title và đẩy paper đúng lên đầu, **bỏ qua semantic search**. Bằng chứng gián tiếp nằm ngay trong bảng trên: `p2-summary` bị xóa sạch summary — tức embedding của nó đã bị hủy phần lớn nội dung — mà **vẫn hit**. Nếu retrieval phụ thuộc embedding thì sample đó phải miss.

Nói cách khác: `retrieval_hit_rate = 1.000` ở baseline đo đúng nhưng đo một thứ dễ hơn dự kiến. Cách kiểm định lượng (chưa chạy vì test set đã khóa sau khi TV4 chạy baseline): chạy lại cùng test set sau khi bỏ dấu nháy đơn khỏi câu hỏi và so chênh lệch hit rate. Đó là cơ sở cho đề xuất ở Mục 9.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về data pipeline:** schema là hợp đồng giữa người, không chỉ là cấu trúc dữ liệu. `index.py` truy cập 9 cột theo tên cứng, nên đặt sai một tên cột là chặn cả TV3 và TV4. Cách xử lý hiệu quả là biến hợp đồng thành mã tường minh (`CLEAN_COLUMN_ORDER`, `METADATA_TEXT_COLUMNS`) để lỗi nổ tại nơi gây ra nó, thay vì lan xuống module người khác. Đồng thời phát hiện `to_csv` phá cột list — `authors` đọc lại từ CSV thành chuỗi `"['A', 'B']"` — nên phải chỉ định rõ JSON là source of truth cho round-trip.
2. **Về data quality/observability:** loại record âm thầm là mất khả năng quan sát. Mọi filter và dedupe đều phải để lại count kèm lý do; và các count phải loại trừ lẫn nhau để tổng khớp `rows_in - rows_out`, nếu không report sẽ có số liệu tự mâu thuẫn. Quality và freshness là hai trục độc lập: pass hết quality check vẫn có thể là dữ liệu cũ.
3. **Về ảnh hưởng của data đến RAG agent:** độ nhạy của phép đo là thứ phải **thiết kế từ trước**, không tự nhiên mà có. Số liệu chứng minh cả hai chiều: việc tôi cố ý đưa 2 paper mới nhất vào test set khiến `drop_frozen_document` phát hiện được ngay (mất 25% hit rate chỉ vì 1 record); ngược lại, việc mọi câu hỏi đều chứa title trong nháy đơn khiến `add_embedding_noise` và `duplicate_rows` **không đo được gì cả**. Cùng một bộ metric, cùng một pipeline — khác nhau chỉ ở chỗ test set có được thiết kế để bắt loại lỗi đó hay không.

### Nếu có thêm thời gian

Thêm loại câu hỏi thứ năm — `semantic` — **không** đặt title trong dấu nháy đơn và không dùng nguyên văn title, mà dùng từ khóa đặc trưng của paper (ví dụ `"Which paper focuses on oil and gas safety report generation?"`). Lý do đã được số liệu xác nhận: cả 4 loại hiện tại đều kích hoạt exact-lookup ở `qa.py:33`, nên `p2-summary` bị **xóa sạch summary mà vẫn `retrieval_hit = true`** — semantic search của MiniLM gần như chưa được kiểm tra, và 2 trong 5 loại corruption của nhóm không tạo ra thay đổi metric nào.

Cách đo cải thiện: so `retrieval_hit_rate` của riêng loại `semantic` giữa baseline và corrupted. Nếu loại này giảm trong khi 4 loại kia giữ nguyên, chứng minh được test set mới bắt được kiểu corruption mà bản hiện tại bỏ sót — cụ thể là `blank_summary` và `add_embedding_noise`. Có thể kiểm nhanh mà **không tốn quota LLM**, vì `retrieval_hit_rate` và `mean_token_f1` đều tính bằng hàm thuần, chỉ `judge` mới cần API.

Chi phí: 16 → 20 sample, tức 48 → 60 lần gọi LLM judge cho cả 3 lần chạy. Điều kiện: phải làm **trước** khi chạy baseline, vì sau đó test set bị khóa — lần này tôi đã bỏ mất thời điểm đó, nên chỉ đề xuất chứ không thực hiện.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Chu Phú Thành
**Ngày xác nhận:** 2026-08-06
