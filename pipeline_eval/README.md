# Đánh giá Đường ống Viết lại Truy vấn (Query Rewriter Pipeline Evaluation)

Thư mục này chứa môi trường và mã nguồn dùng để **đánh giá tự động (Automated Evaluation)** cho *State-Centric Query Rewriting Pipeline* sử dụng bộ dữ liệu **LoCoMo** (Long-Context Multi-Turn RAG).

Bản chất của quá trình đánh giá này là **chạy toàn bộ đường ống thông qua mô hình ngôn ngữ lớn (LLM)** để xử lý, khôi phục ngữ cảnh và viết lại các câu hỏi mơ hồ (Ambiguous Queries) thành câu hỏi độc lập (Standalone Queries) rõ nghĩa. **Hệ thống chạy hoàn toàn tự động thông qua LLM, không sử dụng các bộ từ điển tra cứu tĩnh hay các memo được thêm cứng (hardcoded) thủ công.**

---

## 1. Quy trình Đánh giá 4 Giai đoạn (4-Phase Evaluation Strategy)

Quá trình đánh giá trên mỗi Conversation trong LoCoMo diễn ra qua 4 giai đoạn chính (được thực thi bởi [evaluate_locomo.py](file:///d:/school/Các%20vấn%20đề/retrieval-multiturn-rag/pipeline_eval/evaluate_locomo.py)):

### Giai đoạn 1: Nạp Ký ức Tự động (Memo Injection & Corpus Building)
- **Nạp ký ức tự động**: Đọc trực tiếp tóm tắt phiên chat (`event_summary`) và quan sát (`observation`) từ tệp dữ liệu gốc `locomo10.json` để tự động khởi tạo cơ sở dữ liệu ký ức dài hạn in-memory (`SESSION_MEMOS`). Không có bất kỳ memo nào được thêm cứng thủ công.
- **Xây dựng Corpus BM25**: Gom toàn bộ các lượt hội thoại từ tất cả các phiên chat để tạo cơ sở dữ liệu tài liệu tìm kiếm hạ nguồn (Downstream Knowledge Base).

### Giai đoạn 2: Tải Câu hỏi Mơ hồ (Load Ambiguous Queries)
- Để đảm bảo tính nhất quán và công bằng giữa các lần đánh giá, hệ thống **tải trực tiếp** các câu hỏi mơ hồ đã được chuẩn bị sẵn trước đó từ tệp cấu hình:
  `pipeline_eval/data/ambiguous_queries.json`
- Tìm kiếm đúng các câu hỏi tương ứng với Conversation đang được đánh giá (ví dụ khóa `"2"`, `"3"`,...).
- Tệp này chứa các câu hỏi mơ hồ đã được chuẩn hóa ngữ cảnh (ví dụ: thay thế tên thực thể bằng đại từ tương ứng theo ngữ cảnh).

### Giai đoạn 3: Chạy Pipeline LLM (LLM Pipeline Execution)
Đây là giai đoạn cốt lõi sử dụng Mô hình Ngôn ngữ Lớn (LLM - mặc định là `Qwen 2.5 3B` qua Ollama hoặc API cấu hình) để thực hiện đường ống viết lại câu hỏi:
1. **Phát hiện Vùng biên (HingeMem)**: Heuristic kiểm tra xem câu hỏi có tiếp nối chủ đề cũ hay không dựa trên độ dài hội thoại, đại từ và độ dời thực thể/ngữ nghĩa.
2. **Theo dõi Trạng thái (State Tracker & Checker)**: LLM cập nhật trạng thái hội thoại. Nếu thực thể bị trống (`entities` = `{}`), hệ thống phát hiện mất ngữ cảnh và kích hoạt cờ `need_retrieval = True`.
3. **Truy xuất & Hợp nhất (Retrieval & Fusion)**: Tìm kiếm các Memo liên quan trong cơ sở dữ liệu in-memory và tự động thực hiện **Safe Merge** để hợp nhất thực thể bị thiếu vào State hiện tại.
4. **Viết lại có kiểm soát (Controlled Rewrite)**: LLM sử dụng State đã được khôi phục đầy đủ thông tin để viết lại câu hỏi mơ hồ thành câu hỏi độc lập rõ nghĩa (`Q_final`).

### Giai đoạn 4: Tính điểm & Đánh giá (Scoring)
- So sánh câu viết lại (`Q_final`) với câu hỏi gốc (`Original Question`) và bằng chứng tìm kiếm (`Evidence`) để tính toán các chỉ số chất lượng.

---

## 2. Các Chỉ số Đánh giá Cần Quan tâm

Khi chạy đánh giá, kết quả sẽ được lưu vào thư mục `pipeline_eval/eval_results/eval_conv_<index>.json`. Để đánh giá chất lượng của đường ống viết lại, bạn cần đặc biệt quan tâm đến các chỉ số sau:

### Chỉ số Tìm kiếm (Section Recall)
Đo lường khả năng tìm kiếm thông tin của câu viết lại (`Q_final`) thông qua công cụ tìm kiếm BM25 trên Corpus.
- **Recall@1**: Tỷ lệ phần trăm các câu hỏi mà kết quả tìm kiếm BM25 đầu tiên (Top-1) khớp chính xác với phiên chat chứa bằng chứng (Gold Section, ví dụ: `D2`).
- **Recall@3**: Tỷ lệ bằng chứng nằm trong Top-3 kết quả tìm kiếm.
- **Recall@5**: Tỷ lệ bằng chứng nằm trong Top-5 kết quả tìm kiếm.
- **Ý nghĩa**: Chỉ số Recall (đặc biệt là Recall@1 và Recall@3) càng cao chứng tỏ câu hỏi viết lại chứa các từ khóa vô cùng chính xác, sắc bén và sát với ngữ cảnh thực tế của bằng chứng gốc.

### Chỉ số Ngữ nghĩa (LLM Judge Pass Rate)
Đo lường mức độ bảo toàn ngữ nghĩa của câu viết lại so với câu hỏi gốc.
- **llm_judge_pass (Đạt/Không đạt)**: Sử dụng một LLM độc lập (đóng vai trò trọng tài - Judge) so sánh câu viết lại `Q_final` với câu hỏi gốc `Original Question`.
  - **PASS (True/1)**: Hai câu hỏi có cùng ý nghĩa và mục đích hỏi (đã khôi phục đúng tên nhân vật bị ẩn).
  - **FAIL (False/0)**: Câu viết lại bị sai lệch thông tin hoặc chọn nhầm nhân vật.
- **llm_judge_accuracy**: Tỷ lệ câu hỏi vượt qua đánh giá ngữ nghĩa trên tổng số câu hỏi.

### Chỉ số Tổng hợp (Average Metrics)
Hiển thị ở cuối file kết quả và được tổng hợp bởi các script tiện ích.
- **Avg Recall@K** và **LLM Judge Accuracy** là thước đo sức mạnh tổng thể của Pipeline trên toàn bộ hội thoại.

---

## 3. Cấu trúc thư mục

```text
pipeline_eval/
├── core/
│   ├── pipeline.py       # Điều phối chính của đường ống đánh giá
│   ├── schema.py         # Định nghĩa cấu trúc dữ liệu State
│   └── state.py          # Quản lý trạng thái và bộ nhớ cache
├── nodes/
│   ├── boundary.py       # Nút Boundary Detection (HingeMem)
│   ├── tracker.py        # Nút State Tracker & Checker
│   ├── retriever.py      # Nút Vector Search + Safe Merge
│   └── rewriter.py       # Nút Controlled Rewrite
├── services/
│   ├── llm.py            # Khởi tạo mô hình LLM và các prompt
│   └── vector_db.py      # Quản lý cơ sở dữ liệu vector RAM in-memory
├── data/
│   └── ambiguous_queries.json  # Cơ sở dữ liệu câu hỏi mơ hồ đã sinh sẵn
├── eval_results/         # Thư mục chứa kết quả đánh giá chi tiết
└── evaluate_locomo.py    # Script chính để chạy đánh giá
```

---

## 4. Hướng dẫn Chạy Đánh giá

Vui lòng chạy script từ thư mục gốc của dự án để đảm bảo import đúng cấu trúc thư mục.

### Chạy đánh giá cho Conversation Index 2:
```bash
python -m pipeline_eval.evaluate_locomo --conversation_index 2 --use_qwen true
```

### Chạy giới hạn số câu hỏi (ví dụ: chỉ lấy 5 câu hỏi đầu tiên):
```bash
python -m pipeline_eval.evaluate_locomo --conversation_index 2 --limit 5 --use_qwen true
```

### Chạy thử nghiệm duy nhất một câu hỏi ở vị trí chỉ định để gỡ lỗi:
```bash
python -m pipeline_eval.evaluate_locomo --conversation_index 2 --single_qa 0 --use_qwen true
```

---

## 5. Các công cụ hỗ trợ Xuất và Tổng hợp kết quả

Sau khi chạy xong đánh giá (`evaluate_locomo.py`), bạn có thể chạy 2 script tiện ích dưới đây (chạy từ thư mục gốc của project):

### 1. Xuất file kết quả chi tiết từ JSON sang Excel
```bash
python pipeline_eval/eval_results/json_to_excel.py
```
*Tác dụng*: Đọc toàn bộ các tệp `.json` trong `eval_results/` và sinh ra tệp `.xlsx` tương ứng hiển thị chi tiết câu gốc, câu mơ hồ, câu viết lại, evidence, và kết quả đánh giá BM25/LLM.

### 2. Tính toán và Tổng hợp Metric Trung bình (Làm Báo Cáo)
```bash
python pipeline_eval/eval_results/calculate_average_metrics.py
```
*Tác dụng*:
- Tính toán tổng số lượng Hits, Passes và tính tỷ lệ trung bình.
- Xuất ra màn hình console bảng tóm tắt kết quả.
- Tự động tạo tệp `overall_metrics_report.md` và `overall_metrics_report.xlsx` hiển thị báo cáo tổng hợp và chi tiết từng Conversation.
