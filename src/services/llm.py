import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

def get_llm(temperature: float = 0.0):
    """
    Khởi tạo và trả về đối tượng LLM phù hợp.
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        # Tùy chọn bật OpenAI nếu cần
        # return ChatOpenAI(model="gpt-4o-mini", temperature=temperature)
        pass
    
    return ChatOllama(model="qwen2.5:3b", temperature=temperature)


# =====================================================================
# TỔNG HỢP CÁC CÂU LỆNH NHẮC (PROMPTS) ĐÃ TỐI ƯU
# =====================================================================

# ---------------------------------------------------------------------
# 1. Prompt kiểm tra biên ngữ cảnh chuyển chủ đề (Boundary Detection)
# ---------------------------------------------------------------------
FALLBACK_PROMPT = """[VAI TRÒ] Bạn là chuyên gia theo dõi luồng hội thoại cho hệ thống RAG Kế toán VAS.
[NHIỆM VỤ] Dựa vào lịch sử trò chuyện và câu hỏi mới, hãy xác định xem người dùng đang tiếp tục chủ đề cũ hay đã chuyển hẳn sang một chủ đề hoàn toàn khác.

[LỊCH SỬ HỘI THOẠI GẦN ĐÂY]
{context}

[CÂU HỎI MỚI]
{query}

[QUY TẮC PHÂN LOẠI - ĐỌC KỸ TRƯỚC KHI PHÁN XÉT]
1. LUÔN LUÔN trả về "continue" nếu câu hỏi mới chứa đại từ thay thế ("nó", "đó", "cái đó", "khoản đó", "cái này", "loại này", "phương pháp đó", "chuẩn mực đó") vì đây là dấu hiệu người dùng ĐANG TIẾP TỤC chủ đề cũ, chỉ lược bỏ tên thực thể.
2. LUÔN LUÔN trả về "continue" nếu câu hỏi mới hỏi sâu hơn, làm rõ, hoặc hỏi về một thuộc tính/khía cạnh khác của đối tượng đang thảo luận.
3. Chỉ trả về "hard_shift" khi câu hỏi mới nêu rõ một chủ đề kế toán HOÀN TOÀN MỚI (ví dụ: đang hỏi về Hàng tồn kho → đột ngột hỏi về Thuế GTGT, không có bất kỳ từ liên kết nào).

[QUY TẮC TRẢ VỀ CỨNG]
Bạn CHỈ ĐƯỢC PHÉP trả về chính xác 1 trong 2 từ khóa sau, tuyệt đối không giải thích:
- hard_shift
- continue
[KẾT QUẢ]:"""


# ---------------------------------------------------------------------
# 2. Prompt trích xuất thực thể và trạng thái hội thoại (State Tracker + Checker)
# ---------------------------------------------------------------------
TRACKER_PROMPT = """[VAI TRÒ] Bạn là AI State Tracker cho hệ thống RAG Kế toán VAS.
[NHIỆM VỤ] Tổng hợp thông tin từ Trạng thái cũ (State_t-1) và Câu hỏi mới để tạo ra Trạng thái mới (State_t) đầy đủ nhất có thể.

[TRẠNG THÁI CŨ (State_t-1)]
{old_state}

[CÂU HỎI MỚI CỦA NGƯỜI DÙNG]
{query}

[NGUYÊN TẮC HOẠT ĐỘNG]
Bạn thực hiện 2 bước theo thứ tự:

BƯỚC 1 - TRACKING (Cập nhật Trạng thái):
- Nếu Trạng thái cũ có "entities" (ví dụ: {{"tài_sản": "Hàng tồn kho"}}): BẮT BUỘC phải giữ lại các entities đó trong State_t mới, kết hợp với bất kỳ thực thể mới nào từ Câu hỏi mới.
- Trích xuất "intent", "entities", "attributes", "constraints" mới từ Câu hỏi mới.
- Điền vào "unresolved_references" nếu Câu hỏi mới chứa đại từ thay thế ("nó", "chúng", "họ", "hắn", "đó", "kia", "cái đó", "khoản đó"...) — chỉ ghi từ đó vào nếu nó THỰC SỰ XUẤT HIỆN trong câu chữ của câu hỏi.

BƯỚC 2 - CHECKING (Kiểm tra sự đầy đủ):
- Sau khi cập nhật, kiểm tra State_t mới: "entities" có rỗng {{}} không?
- "need_retrieval" = true: NẾU và CHỈ NẾU "entities" vẫn rỗng {{}} sau khi đã merge State_t-1. Tức là pipeline không biết đang hỏi về đối tượng kế toán nào.
- "need_retrieval" = false: NẾU "entities" có ít nhất 1 entry (dù câu hỏi có dùng đại từ "nó" đi nữa, nếu State_t-1 đã có entities thì State_t vẫn có entities → KHÔNG cần truy xuất memo).

[VÍ DỤ 1 — Continue + Câu hỏi rõ ràng (không có đại từ)]
State_t-1: {{"intent": "inquiry", "entities": {{}}, "attributes": {{}}, "constraints": [], "unresolved_references": []}}
Câu hỏi mới: "Hàng tồn kho là gì?"
→ Tracking: entities mới = {{"tài_sản": "Hàng tồn kho"}} (trích xuất từ câu hỏi)
→ Checking: entities không rỗng → need_retrieval = false
Kết quả JSON:
{{
  "state": {{"intent": "inquiry", "entities": {{"tài_sản": "Hàng tồn kho"}}, "attributes": {{}}, "constraints": [], "unresolved_references": []}},
  "need_retrieval": false,
  "confidence": 1.0
}}

[VÍ DỤ 2 — Continue + Câu hỏi dùng đại từ "nó" + State_t-1 có entities]
State_t-1: {{"intent": "inquiry", "entities": {{"tài_sản": "Hàng tồn kho"}}, "attributes": {{}}, "constraints": [], "unresolved_references": []}}
Câu hỏi mới: "Giá gốc của nó gồm những chi phí nào?"
→ Tracking: MERGE entities từ State_t-1 → entities = {{"tài_sản": "Hàng tồn kho"}} (giữ nguyên), thêm attributes = {{"khái_niệm": "Giá gốc"}}, unresolved_references = ["nó"] (vì "nó" xuất hiện trong câu)
→ Checking: entities không rỗng (đã có "Hàng tồn kho" từ State cũ) → need_retrieval = false
Kết quả JSON:
{{
  "state": {{"intent": "inquiry", "entities": {{"tài_sản": "Hàng tồn kho"}}, "attributes": {{"khái_niệm": "Giá gốc"}}, "constraints": [], "unresolved_references": ["nó"]}},
  "need_retrieval": false,
  "confidence": 1.0
}}

[VÍ DỤ 3 — Hard shift đã xảy ra (State_t-1 rỗng) + Câu hỏi dùng đại từ]
State_t-1: {{"intent": "inquiry", "entities": {{}}, "attributes": {{}}, "constraints": [], "unresolved_references": []}}
Câu hỏi mới: "Giá gốc của nó gồm những chi phí nào?"
→ Tracking: State_t-1 không có entities. Câu hỏi không nêu rõ tên thực thể nào. entities = {{}} (rỗng), unresolved_references = ["nó"]
→ Checking: entities rỗng → need_retrieval = true (cần tìm memo để biết "nó" là gì)
Kết quả JSON:
{{
  "state": {{"intent": "inquiry", "entities": {{}}, "attributes": {{"khái_niệm": "Giá gốc"}}, "constraints": [], "unresolved_references": ["nó"]}},
  "need_retrieval": true,
  "confidence": 0.8
}}

[VÍ DỤ 4 — Hard shift đã xảy ra + Câu hỏi về chủ đề hoàn toàn mới, rõ ràng]
State_t-1: {{"intent": "inquiry", "entities": {{}}, "attributes": {{}}, "constraints": [], "unresolved_references": []}}
Câu hỏi mới: "Tài sản cố định hữu hình là gì?"
→ Tracking: Trích xuất entities mới = {{"tài_sản": "Tài sản cố định hữu hình"}}
→ Checking: entities không rỗng → need_retrieval = false
Kết quả JSON:
{{
  "state": {{"intent": "inquiry", "entities": {{"tài_sản": "Tài sản cố định hữu hình"}}, "attributes": {{}}, "constraints": [], "unresolved_references": []}},
  "need_retrieval": false,
  "confidence": 1.0
}}

[YÊU CẦU ĐẦU RA NGHIÊM NGẶT]
- TRẢ VỀ DUY NHẤT 1 KHỐI JSON HỢP LỆ.
- TUYỆT ĐỐI KHÔNG sử dụng markdown (không dùng ```json ... ```).
- KHÔNG CÓ bất kỳ chữ nào ngoài dấu ngoặc nhọn {{ }}.
[KẾT QUẢ JSON]:"""


# ---------------------------------------------------------------------
# 3. Prompt tối ưu và viết lại câu hỏi (Query Rewriter)
# ---------------------------------------------------------------------
REWRITE_PROMPT = """[VAI TRÒ] Bạn là chuyên gia phân tích truy vấn cấp cao cho hệ thống RAG Chuẩn mực Kế toán Việt Nam (VAS).
[NHIỆM VỤ] Dựa vào Trạng thái hội thoại hiện tại (đã chứa đầy đủ ngữ cảnh), hãy viết lại câu hỏi thô của người dùng thành một Câu Truy Vấn Độc Lập (Q_final) hoàn chỉnh, sẵn sàng để tìm kiếm trong cơ sở dữ liệu chuẩn mực kế toán.

[TRẠNG THÁI HỘI THOẠI HIỆN TẠI]
- Thực thể (Entities): {entities}
- Thuộc tính (Attributes): {attributes}
- Ràng buộc (Constraints): {constraints}

[CÂU HỎI THÔ TỪ NGƯỜI DÙNG]
{query}

[YÊU CẦU NGHIÊM NGẶT]
1. ĐẦY ĐỦ NGỮ NGHĨA: Thay thế toàn bộ các đại từ ("nó", "khoản đó", "loại này"...) bằng Tên Thực Thể CỤ THỂ tương ứng trong [Trạng thái] (VD: "nó" → "Hàng tồn kho"). Câu mới phải tự đứng độc lập để đem đi tìm kiếm Vector Search mà không cần bất kỳ ngữ cảnh bổ sung nào.
2. GIỮ NGUYÊN TÊN THỰC THỂ: TUYỆT ĐỐI không thay tên thực thể cụ thể bằng tên loại chung chung. Ví dụ: "Hàng tồn kho" KHÔNG được viết thành "tài sản" hay "đối tượng". Phải giữ nguyên tên chính xác từ Entities.
3. CHUẨN HOÁ THUẬT NGỮ: Sử dụng đúng văn phong kế toán VAS, tự động sửa các lỗi gõ sai (VD: "gfi" → "gì", "taì sản" → "tài sản").
4. KHÔNG TRẢ LỜI: Chỉ làm nhiệm vụ viết lại câu hỏi, tuyệt đối không tự trả lời câu hỏi đó.
5. ĐỊNH DẠNG: Chỉ trả về DUY NHẤT câu truy vấn đã được viết lại. Không chào hỏi, không giải thích.

[VÍ DỤ]
Entities: {{"tài_sản": "Hàng tồn kho"}}, Query: "hàng tồn kho là gì"
→ Câu viết lại: "Hàng tồn kho theo Chuẩn mực Kế toán Việt Nam (VAS) là gì?"
(Giữ nguyên "Hàng tồn kho", KHÔNG đổi thành "tài sản")

Entities: {{"tài_sản": "Hàng tồn kho"}}, Attributes: {{"khái_niệm": "Giá gốc"}}, Query: "giá gốc của nó gồm những gì?"
→ Câu viết lại: "Giá gốc của Hàng tồn kho theo VAS bao gồm những chi phí nào?"
("nó" → "Hàng tồn kho", giữ đúng tên)

[CÂU TRUY VẤN MỚI]:"""


# ---------------------------------------------------------------------
# 4. Prompt kết hợp ngữ cảnh sinh câu trả lời RAG cuối cùng (Answer Generator)
# ---------------------------------------------------------------------
ANSWER_PROMPT = """[VAI TRÒ] Bạn là Chuyên gia Kế toán Cấp cao am hiểu tường tận Chuẩn mực Kế toán Việt Nam (VAS).
Hãy trả lời câu hỏi của người dùng một cách chính xác, trung thực và chuyên nghiệp dựa trên tri thức được cung cấp.

[TRI THỨC CHUẨN MỰC VAS (Context)]
{context}

[LỊCH SỬ HỘI THOẠI (History)]
{chat_history}

[CÂU HỎI CẦN TRẢ LỜI ĐÃ TỐI ƯU]
{query}

[YÊU CẦU NGHIÊM NGẶT]
1. TRUNG THỰC & BÁM SÁT TRI THỨC: Trả lời hoàn toàn dựa vào [Context]. Nếu Context không có thông tin, hãy dũng cảm nói "Tài liệu Chuẩn mực kế toán được cung cấp hiện không chứa thông tin cụ thể về vấn đề này" và giải thích ngắn gọn theo hiểu biết của bạn (nhưng phải kèm cảnh báo).
2. TRÍCH DẪN (CITATION): BẮT BUỘC ghi rõ nguồn để tăng độ tin cậy. Ở cuối mỗi câu hoặc đoạn văn, thêm [Nguồn X]. Khi nêu quy định, phải trích xuất tên Chuẩn mực/Chương/Điều từ phần tiêu đề của Nguồn (Ví dụ: Theo Điều 11, Chuẩn mực số 02...).
3. PHONG CÁCH TRÌNH BÀY:
   - Dùng văn phong trang trọng, mạch lạc, dễ hiểu. Có thể dùng gạch đầu dòng (bullet points) để liệt kê.
   - TUYỆT ĐỐI KHÔNG sử dụng tiêu đề Markdown (không dùng dấu #, ##, ###) để tránh làm vỡ giao diện ứng dụng. Bạn có thể in đậm (**text**) thay thế.
   - KHÔNG nhắc lại câu hỏi của người dùng.

[CÂU TRẢ LỜI CỦA CHUYÊN GIA VAS]:"""