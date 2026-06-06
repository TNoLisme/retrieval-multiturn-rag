# Query Rewriter Pipeline Evaluation (LoCoMo)

Thư mục này chứa môi trường và mã nguồn dùng để **đánh giá tự động (Automated Evaluation)** cho *State-Centric Query Rewriting Pipeline* sử dụng bộ dữ liệu **LoCoMo** (Long-Context Multi-Turn RAG).

## Mục tiêu đánh giá
Mục tiêu chính là kiểm tra xem hệ thống có khả năng **tìm kiếm lại ký ức dài hạn (Memo)** và **sử dụng nó để làm rõ các câu truy vấn mơ hồ (Ambiguous Queries)** hay không. Quá trình đánh giá được thiết kế theo "Hard Mode": cố tình để trạng thái bộ nhớ ngắn hạn rỗng, ép hệ thống phải sử dụng tính năng Retrieval (truy xuất Memo) để phục hồi ngữ cảnh.

---

## Kiến trúc Đánh giá (4-Phase Evaluation Strategy)

File chính thực thi đánh giá là `evaluate_locomo.py`. Quá trình đánh giá trên mỗi Conversation trong LoCoMo diễn ra qua 4 giai đoạn:

### Giai đoạn 1: Memo Injection & Corpus Building
- Đọc file dữ liệu `locomo10.json`.
- **Memo DB:** Trích xuất thông tin tóm tắt từng phiên chat từ khóa `event_summary` (đặc biệt là cấu trúc `events_session_X` chứa các sự kiện theo từng nhân vật). Tạo thành các `Memo` chứa `summary` (tóm tắt), `metadata` (chứa entities), và `history` (toàn bộ nội dung hội thoại gốc). Inject toàn bộ vào RAM Memo DB (`SESSION_MEMOS`).
- Lưu các Memo này dưới dạng JSON vào thư mục gốc `memo_chat_db/` để dễ dàng kiểm tra.
- **BM25 Corpus:** Tạo một Index BM25 bao gồm toàn bộ các lượt chat gốc trong toàn bộ các phiên hội thoại để làm "Kho kiến thức" (Downstream Knowledge Base).

### Giai đoạn 2: Batch Ambiguator (Tạo câu hỏi mơ hồ)
- Gửi toàn bộ các câu hỏi nguyên gốc (rõ nghĩa) trong danh sách QA của LoCoMo tới một LLM (mặc định là `Qwen 2.5 3B` qua Ollama).
- Yêu cầu LLM biến đổi câu hỏi thành **câu hỏi mơ hồ**, cụ thể là thay thế các tên riêng (Proper Names) bằng đại từ nhân xưng (VD: "Caroline" -> "she", "he", "it"). 
- Kết quả thu được là một tập `Ambiguous Queries`.

### Giai đoạn 3: Pipeline Execution ("Hard Mode")
Đưa từng `Ambiguous Query` chạy qua đường ống State-Centric:
- **Ép State rỗng:** Hệ thống cố tình truyền vào `State_t-1` trống rỗng.
- **Boundary Detection:** Nhận diện việc tiếp tục ngữ cảnh cũ (vì câu hỏi có đại từ thay thế).
- **State Tracker:** Vì State cũ trống rỗng nên Entities = `{}`, do đó kích hoạt cờ `need_retrieval = True`.
- **Memo Retrieval:** Hệ thống tìm kiếm các Memo tương đồng dựa trên từ khóa hoặc đại từ chưa rõ nghĩa.
- **Safe Merge:** Điền các `Entities` bị thiếu (như tên nhân vật) từ Memo đã tìm được vào State hiện tại.
- **Controlled Rewrite:** Viết lại câu truy vấn mơ hồ thành câu Standalone (Q_final) có đầy đủ tên riêng dựa vào State đã được cập nhật.

### Giai đoạn 4: Metric Scoring (Đo lường)
Hệ thống sử dụng hai thang đo để đánh giá chất lượng của `Q_final`:
1. **BM25 Hit-Rate @ 3**: Dùng `Q_final` để tìm kiếm top 3 lượt chat trong BM25 Corpus. Kiểm tra xem ID của lượt chat kết quả (dia_id) có chứa ID của lượt chat bằng chứng (ground truth evidence) của câu QA đó không. Trả về True/False.
2. **LLM-as-a-Judge**: Dùng LLM (mặc định là GPT-4o-mini hoặc Qwen 2.5 3B) so sánh ngữ nghĩa giữa `Q_final` và `Original Question`. Trả về PASS (1) nếu 2 câu hỏi hỏi về cùng một thứ, hoặc FAIL (0) nếu sai khác.

Tất cả kết quả của 4 giai đoạn, cùng các điểm số, sẽ được lưu vào file JSON bên trong thư mục `eval_results/`.

---

## Cấu trúc thư mục

```text
pipeline_eval/
├── core/
│   ├── pipeline.py       # Orchestrator đường ống chính cho đánh giá
│   ├── schema.py         # Cấu trúc dữ liệu State
│   └── state.py          # State Manager (In-Memory Redis Mock)
├── nodes/
│   ├── boundary.py       # Nút HingeMem
│   ├── retriever.py      # Nút Vector Search + Safe Merge
│   ├── rewriter.py       # Nút Controlled Rewrite
│   └── tracker.py        # Nút State Tracker
├── services/
│   ├── llm.py            # Chứa các prompt đánh giá và LLM Factory
│   └── vector_db.py      # RAM Vector DB (In-memory storage)
├── eval_results/         # Chứa kết quả đánh giá (ví dụ: eval_conv_0.json)
└── evaluate_locomo.py    # Script chạy quy trình đánh giá 4 giai đoạn
```

## Cách chạy đánh giá

Vui lòng chạy script từ thư mục gốc của project (để đảm bảo import đúng thư mục `locomo/`).

Chạy đánh giá cho Conversation Index 0:
```bash
python -m pipeline_eval.evaluate_locomo --conversation_index 0
```

Chạy đánh giá và giới hạn chỉ lấy 5 câu QA đầu tiên:
```bash
python -m pipeline_eval.evaluate_locomo --conversation_index 0 --limit 5
```

Chỉ test duy nhất câu QA ở vị trí 0 (để debug):
```bash
python -m pipeline_eval.evaluate_locomo --conversation_index 0 --single_qa 0
```
