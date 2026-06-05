# Hướng dẫn Đánh giá Pipeline Rewrite bằng Dataset LoCoMo

Tài liệu này mô tả phương pháp thiết lập môi trường đánh giá (Evaluation Pipeline) cho module Rewrite (State-Centric) bằng cách tận dụng tối đa bộ dữ liệu **LoCoMo** mà **ít phải biến đổi dữ liệu gốc nhất**.

## 1. Mục tiêu
Chúng ta cần kiểm tra xem Pipeline của mình có khả năng nhớ lại các sự kiện trong quá khứ (Long-term memory) và viết lại các câu hỏi chứa đại từ (nó, anh ấy, chuyện đó...) thành một câu hỏi rõ ràng (Standalone Query) hay không.

LoCoMo là một benchmark lý tưởng vì nó có sẵn:
1. `conversation`: Lịch sử chat dài (nhiều session).
2. `qa`: Tập câu hỏi và đáp án để test trí nhớ. **Đặc biệt, trường `question` trong `qa` luôn là một câu hỏi đầy đủ, rõ nghĩa (Ground Truth).**
3. `evidence`: Trỏ thẳng đến câu chat chứa thông tin trả lời.

## 2. Cách tận dụng LoCoMo (Ít biến đổi nhất)

Vấn đề duy nhất là mảng `qa` của LoCoMo chứa các câu hỏi *đã rõ ràng*, trong khi Rewriter của chúng ta cần đầu vào là một câu hỏi *lấp lửng/mơ hồ* (chứa đại từ) để test khả năng viết lại. 

Giải pháp tận dụng tối đa cấu trúc gốc của LoCoMo:
**Thay vì tự gõ tay tạo dataset mới, ta chỉ thêm 1 bước Tiền xử lý (Preprocessing) duy nhất: Biến câu hỏi rõ ràng thành câu hỏi lấp lửng.**

### Bước 1: Trích xuất Dữ liệu
- Quét qua mảng `qa` trong `locomo10.json`.
- Với mỗi câu hỏi (Ground Truth Query - ví dụ: *"When did Caroline go to the park?"*):
  - Tìm thời điểm câu hỏi này nên được hỏi dựa vào trường `evidence` (ví dụ `D2:4` nghĩa là ở Session 2, lượt thoại 4).

### Bước 2: Sinh câu hỏi mơ hồ (Ambiguous Query Generation)
- Cần **1 biến đổi duy nhất**: Thay thế danh từ chính trong Ground Truth Query bằng đại từ.
  - *Ví dụ:* "When did **Caroline** go to the park?" $\rightarrow$ "When did **she** go to the park?" (Ambiguous Query).
- Bước này có thể dùng một đoạn mã NLP đơn giản hoặc gọi LLM (Zero-shot) tạo hàng loạt trước khi chạy đánh giá.

### Bước 3: Nạp lịch sử (Session Injection)
- Không cần sửa đổi cấu trúc JSON.
- Đọc mảng `conversation` của LoCoMo, nạp từng lượt thoại vào **State Tracker** và **Boundary Node** của Pipeline giống hệt như cách User đang chat thật.
- Nạp cho đến ngay trước cái mốc `evidence` tìm được ở Bước 1. (Việc này giúp Pipeline xây dựng được các Memos dài hạn trong Vector DB).

### Bước 4: Chạy Evaluation Pipeline
- Ném **Ambiguous Query** (câu hỏi mơ hồ) vào Pipeline.
- Đợi Pipeline chạy qua Boundary $\rightarrow$ State Tracker $\rightarrow$ Memo Retrieval $\rightarrow$ Rewriter.
- Output sinh ra là **$Q_{final}$** (câu hỏi đã được viết lại).

## 5. Tiêu chí Đánh giá (Metrics)

Cách đánh giá tận dụng trọn vẹn dữ liệu gốc mà không cần chạy mô hình LLM khổng lồ:

### Cách 1: Đánh giá bằng LLM-as-a-Judge (Semantic Equivalence)
- Đưa **$Q_{final}$** và câu **Ground Truth Query** (từ trường `question` gốc của `qa`) vào cho LLM Judge.
- Đặt câu hỏi: *"Hai câu này có hỏi về cùng một đối tượng và cùng một sự kiện hay không?"*
- Trả về 1 (Pass) hoặc 0 (Fail). 
- *Ưu điểm:* Đo lường chuẩn xác khả năng hiểu ngữ cảnh của Rewriter.

### Cách 2: Đánh giá bằng Retrieval Recall (Không tốn LLM)
- Dùng **$Q_{final}$** ném vào thuật toán BM25 hoặc Vector Search để tìm kiếm lại trên chính đoạn văn bản hội thoại (mảng `conversation`).
- Lấy ra Top-5 câu thoại liên quan nhất.
- Kiểm tra xem ID của các câu thoại này có chứa cái ID nằm trong trường `evidence` gốc của LoCoMo hay không.
- *Ưu điểm:* Đánh giá thẳng vào mục đích cuối cùng của RAG (khả năng tìm đúng nguồn). Rất nhanh và tự động hóa 100%.
