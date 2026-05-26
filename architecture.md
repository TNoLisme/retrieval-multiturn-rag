


# TÀI LIỆU ĐẶC TẢ KIẾN TRÚC HOÀN CHỈNH: STATE-CENTRIC ADAPTIVE PIPELINE
DỰA VÀO PIPELINE CỦA ẢNH pipeline.png

### 1. Khối Dữ liệu Đầu vào (Input Block)

* **Mục đích:** Cung cấp toàn bộ nguyên liệu thô và bối cảnh hiện thời để hệ thống bắt đầu xử lý.
* **Thành phần dữ liệu:**
* `Query_t`: Câu hỏi gốc của người dùng tại thời điểm $t$.
* `Active Chat`: Lịch sử hội thoại ngắn hạn (thường là $N$ lượt chat gần nhất).
* `State_t-1`: Trạng thái hội thoại từ phiên trước, được nạp trực tiếp từ bộ nhớ đệm (Redis/Session).
* `Memo DB`: Cơ sở dữ liệu Vector chứa các ký ức dài hạn.



---

### 2. Lớp Phân tích Biên ngữ cảnh (Boundary Detection Layer)

#### 2.1. HingeMem (Rule-based)

* **Mục đích:** Phân loại nhanh ý định chuyển đổi chủ đề của người dùng.
* **Đầu vào:** `Query_t`, `Active Chat`.
* **Đầu ra:** Điều hướng luồng (hard_shift, uncertain, continue).

#### 2.2. Fallback (Tiny Model)

* **Mục đích:** Thẩm định lại các trường hợp HingeMem trả về `uncertain`.
* **Quy trình:** Sử dụng SLM đọc hiểu ngữ nghĩa để đưa ra quyết định cuối cùng là `hard_shift` hay `continue`.

#### 2.3. Memo Creation & State Reset (Xử lý Hard Shift)

* **Mục đích:** Nén bối cảnh cũ, dọn dẹp không gian làm việc cho chủ đề mới.
* **Đầu vào:** Kích hoạt khi có tín hiệu `hard_shift` từ 2.1 hoặc 2.2.
* **Quy trình xử lý (Logic):**
1. **Nén:** Tổng hợp `Active Chat` thành "Memo" (Topic + Summary) và đẩy vào `Vector DB`.
2. **Reset:** **Xóa/Làm mới hoàn toàn `State_t-1**` (Clear State). Điều này đảm bảo hệ thống không mang các thực thể và ràng buộc của chủ đề cũ (ví dụ: đang nói chuyện mua xe, chuyển sang hỏi thời tiết) vào chủ đề mới, tránh hiện tượng "râu ông nọ cắm cằm bà kia".



---

### 3. Lớp Quản lý Trạng thái (State Management Layer)

#### 3.1. Cấu trúc State Schema (Định nghĩa Dữ liệu)

Trạng thái hội thoại được lưu trữ chuẩn hóa dưới dạng JSON với 5 thành phần cốt lõi:

* `Intent` (Ý định): Mục tiêu hiện tại của người dùng (VD: So sánh, hỏi giá, tìm kiếm).
* `Entities` (Thực thể): Đối tượng chính đang được thảo luận (VD: Brand: Apple, Model: iPhone 15).
* `Attributes` (Thuộc tính): Các đặc tính đi kèm của thực thể (VD: Dung lượng 256GB).
* `Constraints` (Ràng buộc): Giới hạn tìm kiếm của người dùng (VD: Giá < 20 triệu, màu đen).
* `Unresolved_References` (Tham chiếu chưa giải quyết): Các đại từ ẩn danh (VD: "nó", "cái cũ", "dòng kia").

#### 3.2. State Tracker + Checker (LLM)

* **Quy trình xử lý (Logic):**
* **Tracking:** Đối chiếu `Query_t` với `State_t-1` để trích xuất và cập nhật các trường trong Schema trên. Tạo ra `State_t` (tạm thời).
* **Checking:** Kiểm tra `State_t`. Nếu trường `Unresolved_References` có dữ liệu, hoặc một `Intent` yêu cầu so sánh nhưng thiếu `Entities` đối chứng $\rightarrow$ Bật cờ `need_retrieval = True`. Ngược lại là `False`.



#### 3.3. State Persistence (Tính liên tục của Trạng thái)

* **Hành động:** Ngay sau khi `State_t` được chốt (sau bước Safe Merge hoặc khi kết thúc Pipeline), hệ thống sẽ **lưu `State_t` này vào bộ nhớ đệm (Redis/In-memory Session)**. Trạng thái này sẽ trở thành `State_t-1` để phục vụ trực tiếp cho lượt chat $t+1$.

---

### 4. Lớp Truy xuất & Hợp nhất (Retrieval & Fusion Layer)

#### 4.1. Retrieve Memo (top-k)

* **Đầu vào:** `need_retrieval == True`.
* **Quy trình:** Dùng vector của `State_t` (hoặc `Query_t`) để search trong `Memo DB`.
* **Đầu ra:** * Tìm thấy $\rightarrow$ Chuyển tới Memory Fusion.
* Không tìm thấy $\rightarrow$ Bật cờ `retrieved_empty = True` và chuyển thẳng tới Generation Layer.



#### 4.2. Memory Fusion (Safe Merge)

* **Quy trình xử lý:** Chỉ sử dụng dữ liệu từ Memo để lấp đầy các ô trống trong `Entities` và giải quyết các giá trị trong `Unresolved_References`. Tuyệt đối giữ nguyên các `Constraints` mới nhất mà người dùng vừa thiết lập.

---

### 5. Lớp Tái cấu trúc & Đầu ra (Generation Layer)

#### 5.1. Context Selection

* **Mục đích:** Sắp xếp và lọc bỏ các thông tin nhiễu từ State và Memos, tạo ra bộ ngữ cảnh sạch (`Refined Context`).

#### 5.2. Controlled Rewrite [Qfinal Generation] & Graceful Fallback

* **Đầu vào:** `Query_t`, `Refined Context`, và các cờ trạng thái (`need_retrieval`, `retrieved_empty`).
* **Quy trình xử lý đặc biệt (Handling Empty Retrieval):**
* **Trường hợp Bình thường:** Sử dụng thông tin trong State để viết lại `Query_t` thành một câu hỏi độc lập ($Q_{final}$) đầy đủ ngữ cảnh.
* **Trường hợp Thiếu thông tin (Góc chết):** Nếu `need_retrieval == True` nhưng `retrieved_empty == True` (Tức là hệ thống biết bị thiếu thông tin, nhưng lục tìm lịch sử DB lại không có).
* *Hành động:* Hệ thống sẽ **không cố gắng ảo giác (hallucinate)** để viết câu hỏi. Thay vào đó, nó tạo ra một truy vấn mang tính xác nhận/hỏi lại người dùng (Clarification Request).
* *Ví dụ Output:* "Hệ thống không tìm thấy thông tin về 'sản phẩm cũ' mà bạn nhắc đến. Vui lòng cung cấp tên sản phẩm để tôi có thể so sánh".


* **Đầu ra:** $Q_{final}$ - Câu truy vấn hoàn hảo, an toàn, sẵn sàng gửi cho kho tài liệu RAG.

---

