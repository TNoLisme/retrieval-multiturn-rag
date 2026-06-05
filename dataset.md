# Cấu trúc Bộ Dữ liệu LoCoMo (Long-term Conversation Memory)

Bộ dữ liệu LoCoMo (đại diện là file `locomo10.json`) được thiết kế đặc biệt để làm benchmark đánh giá khả năng **Ghi nhớ dài hạn (Long-term Memory)** của các mô hình hội thoại AI (Conversational Agents) qua nhiều phiên trò chuyện (sessions) diễn ra trong một thời gian dài.

Mỗi phần tử trong file JSON đại diện cho một mẫu dữ liệu (một cuộc đời/hành trình trò chuyện giữa 2 người dùng). Dưới đây là phân tích chi tiết về các thành phần cốt lõi trong mỗi mẫu:

---

## 1. Mảng `qa` (Question-Answer)
Đây là bộ câu hỏi dùng để **kiểm tra trí nhớ** của AI. AI sẽ phải đọc toàn bộ lịch sử (conversation) và trả lời các câu hỏi này.

Các trường trong mỗi object của `qa`:
- **`question`**: Câu hỏi đánh giá (VD: *"Caroline đã nộp đơn xin nhận con nuôi vào lúc nào?"*). Câu hỏi thường đòi hỏi AI phải xâu chuỗi thông tin hoặc giải quyết sự mơ hồ (coreference resolution).
- **`answer`**: Đáp án đúng (Ground Truth).
- **`evidence`**: Mảng chứa các ID của lượt thoại chứng minh cho câu trả lời. VD: `["D2:8", "D13:1"]`. Chữ 'D' là Dialogue, số đầu tiên là Session, số sau dấu `:` là số thứ tự lượt thoại.
- **`category`**: Loại câu hỏi. Các category thường được phân loại theo độ khó (Ví dụ: truy xuất sự kiện tĩnh, truy xuất sự kiện có thay đổi theo thời gian, suy luận logic dựa trên sự kiện, v.v.).
- **`adversarial_answer`**: (Chỉ có ở một số category nâng cao) Chứa câu trả lời bẫy hoặc gây nhiễu, dùng để test xem AI có bị nhầm lẫn với các sự kiện tương tự nhưng sai ngữ cảnh hay không.

---

## 2. Đối tượng `conversation` (Lịch sử Hội thoại)
Nơi chứa toàn bộ dữ liệu hội thoại thô, được chia nhỏ thành các phiên (sessions) có thời gian cụ thể. Đây là phần dữ liệu chính sẽ được nạp vào Memory/State Tracker của AI để xử lý.

Các thành phần:
- **`speaker_a` / `speaker_b`**: Tên của hai người tham gia trò chuyện.
- **`session_X_date_time`**: Mốc thời gian của từng phiên chat (VD: *"1:56 pm on 8 May, 2023"*). AI cần dựa vào thời gian này để hiểu tiến trình sự kiện (timeline).
- **`session_X`**: Mảng chứa chi tiết từng lượt thoại trong phiên đó.
  - **`speaker`**: Người đang nói ở lượt này.
  - **`dia_id`**: Mã định danh câu nói (VD: `"D1:1"`). Định danh này liên kết trực tiếp với trường `evidence` của mảng `qa`.
  - **`text`**: Nội dung văn bản của lượt thoại.
  - *Dữ liệu đa phương thức (Multimodal)*: Nếu lượt thoại có chứa ảnh, sẽ có thêm các trường như `img_url` (đường dẫn ảnh), `blip_caption` (mô tả nội dung ảnh), và `query` (chủ đề của ảnh).

---

## 3. Đối tượng `observation` (Quan sát Sự kiện)
Chứa các sự kiện, sở thích, thông tin cá nhân cụ thể được chắt lọc (extract) sẵn từ hội thoại. 

Các thành phần:
- Tổ chức theo từng session: `session_1_observation`, `session_2_observation`...
- Trong mỗi session, thông tin được phân loại theo từng người nói (`Caroline`, `Melanie`).
- Mỗi quan sát là một mảng gồm 2 phần tử:
  1. **Nội dung sự kiện**: Ví dụ *"Melanie vừa mới chạy giải marathon từ thiện vào thứ Bảy tuần trước."*
  2. **Evidence ID**: Mã định danh câu chat sinh ra sự kiện này (VD: `"D2:1"`).
- **Tác dụng**: Phần này giống như "Ground Truth" cho các thuật toán State Tracking hoặc Entity Extraction. Bạn có thể dùng nó để kiểm tra xem hệ thống HingeMem/State Tracker của mình có trích xuất đúng và đủ các thông tin cá nhân của User từ câu chat hay không.

---

## 4. Đối tượng `session_summary` (Tóm tắt Phiên chat)
Cung cấp một đoạn văn tóm tắt lại toàn bộ diễn biến chính của từng phiên chat.

Các thành phần:
- **`session_1_summary`**, **`session_2_summary`**...: Chứa chuỗi string (văn bản) dài mô tả ngắn gọn nội dung cuộc trò chuyện, thái độ của các nhân vật, và các quyết định quan trọng.
- **Tác dụng**: Trong các hệ thống RAG hội thoại, nếu lưu trữ toàn bộ từng câu chat (Raw Chat History) sẽ làm tràn Context Window. Thay vào đó, nhiều kiến trúc chọn lưu trữ các đoạn `session_summary` này vào bộ nhớ (Vector DB / Memo). Bộ LoCoMo cung cấp sẵn Summary này giúp các nhà nghiên cứu test các thuật toán Memory dựa trên Tóm tắt (Summary-based Memory) mà không tốn chi phí gọi LLM để tự tạo tóm tắt lại.
