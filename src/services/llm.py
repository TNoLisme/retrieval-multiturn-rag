import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

# Nạp các biến môi trường từ file .env
load_dotenv()

def get_llm(temperature: float = 0.0):
    """
    Khởi tạo và trả về đối tượng LLM phù hợp.
    Nếu có biến môi trường OPENAI_API_KEY, hệ thống sẽ sử dụng ChatOpenAI (gpt-4o-mini).
    Ngược lại, hệ thống sẽ sử dụng ChatOllama với mô hình local 'qwen2.5:3b'.
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    # if openai_key:
    #     print("[LLM Service] Sử dụng OpenAI GPT-4o-mini.")
    #     return ChatOpenAI(model="gpt-4o-mini", temperature=temperature)
    # else:
    #     print("[LLM Service] Không tìm thấy OPENAI_API_KEY. Sử dụng local model 'qwen2.5:3b' qua Ollama.")
    #     return ChatOllama(model="qwen2.5:3b", temperature=temperature)
    return ChatOllama(model="qwen2.5:3b", temperature=temperature)



# =====================================================================
# TỔNG HỢP CÁC CÂU LỆNH NHẮC (PROMPTS) CHO LLM TRONG DỰ ÁN
# =====================================================================

# 1. Prompt kiểm tra biên ngữ cảnh chuyển chủ đề (Boundary Detection)
FALLBACK_PROMPT = """
Bạn là một trợ lý kiểm tra biên hội thoại (Boundary Detection) cho RAG Kế toán VAS.
Dưới đây là lịch sử hội thoại gần đây và một câu hỏi mới của người dùng.
Nhiệm vụ của bạn là xác định xem câu hỏi mới có chuyển sang một chủ đề hoàn toàn khác không liên quan (hard_shift) hay tiếp tục/đào sâu chủ đề hiện tại (continue).

Lịch sử hội thoại:
{context}

Câu hỏi mới:
"{query}"

Hãy trả lời chính xác bằng một trong hai từ dưới đây (không viết gì thêm):
- hard_shift (nếu câu hỏi chuyển sang chủ đề hoàn toàn khác)
- continue (nếu câu hỏi tiếp tục làm rõ hoặc hỏi tiếp chủ đề cũ)
"""

# 2. Prompt trích xuất thực thể và trạng thái hội thoại (State Tracker)
TRACKER_PROMPT = """
Bạn là một AI State Tracker cho hệ thống RAG kế toán VAS (Vietnam Accounting Standards).
Nhiệm vụ của bạn là phân tích câu hỏi mới của người dùng và trạng thái cũ để cập nhật trạng thái hội thoại (ConversationState) dưới dạng JSON.

Trạng thái cũ (JSON):
{old_state}

Câu hỏi mới:
"{query}"

Định nghĩa các trường trong JSON kết quả:
1. 'intent': Ý định hiện tại (ví dụ: "inquiry" - hỏi đáp/định nghĩa, "compare" - so sánh, "list" - liệt kê).
2. 'entities': Các thực thể kế toán quan trọng xuất hiện dưới dạng Key-Value (ví dụ: {{"chuẩn_mực": "Chuẩn mực số 02"}}, {{"tài_sản": "Hàng tồn kho"}}, {{"khái_niệm": "Giá gốc"}}). Cập nhật thực thể mới hoặc giữ thực thể cũ nếu người dùng vẫn tiếp tục thảo luận đối tượng đó.
   * LƯU Ý: Giá trị thực thể phải là danh từ chỉ đối tượng cụ thể, KHÔNG ĐƯỢC chứa các từ dùng để hỏi (ví dụ: "gì", "gfi", "nào", "sao").
3. 'attributes': Các thuộc tính đi kèm của thực thể (ví dụ: {{"đặc_tính": "Khấu hao"}}, {{"phương_pháp": "Tính giá gốc"}}).
4. 'constraints': Các giới hạn hoặc điều kiện ràng buộc (ví dụ: ["giá trị > 20 triệu", "thời gian sử dụng hữu ích > 1 năm"]).
5. 'unresolved_references': Các đại từ thay thế mơ hồ xuất hiện trong câu hỏi mới mà chưa thể tự giải nghĩa. BẮT BUỘC phải để là danh sách rỗng [] trừ khi câu hỏi mới chứa các từ cụ thể như: 'nó', 'cái đó', 'khoản đó', 'điều kiện đó', 'phương pháp đó', 'đối tượng đó'. Nếu câu hỏi không chứa một trong các từ cụ thể này, bạn KHÔNG ĐƯỢC thêm bất cứ từ nào vào danh sách.
6. 'need_retrieval': BẮT BUỘC đặt là true nếu danh sách 'unresolved_references' không rỗng. BẮT BUỘC đặt là false nếu danh sách 'unresolved_references' rỗng `[]` (câu hỏi rõ ràng, không cần tra cứu lịch sử cũ).
7. 'confidence': Độ tin cậy của việc cập nhật (từ 0.0 đến 1.0).

---
VÍ DỤ 1 (Câu hỏi mới rõ ràng, không có đại từ thay thế mơ hồ):
- Trạng thái cũ: {{}}
- Câu hỏi mới: "hàng tồn kho là gfi"
- JSON kết quả:
{{
  "state": {{
    "intent": "inquiry",
    "entities": {{"tài_sản": "Hàng tồn kho"}},
    "attributes": {{}},
    "constraints": [],
    "unresolved_references": []
  }},
  "need_retrieval": false,
  "confidence": 1.0
}}

VÍ DỤ 2 (Câu hỏi mới chứa đại từ mơ hồ "nó" cần tra cứu lịch sử):
- Trạng thái cũ: {{"intent": "inquiry", "entities": {{"tài_sản": "Hàng tồn kho"}}, "attributes": {{}}, "constraints": [], "unresolved_references": []}}
- Câu hỏi mới: "Giá gốc của nó gồm những chi phí nào?"
- JSON kết quả:
{{
  "state": {{
    "intent": "inquiry",
    "entities": {{"tài_sản": "Hàng tồn kho"}},
    "attributes": {{"phương_pháp": "Tính giá gốc"}},
    "constraints": [],
    "unresolved_references": ["nó"]
  }},
  "need_retrieval": true,
  "confidence": 1.0
}}

LƯU Ý: Chỉ trả về duy nhất chuỗi JSON hợp lệ theo cấu trúc ví dụ, không bọc trong ```json...``` hay bất cứ lời dẫn/giải thích nào khác.
"""

# 3. Prompt tối ưu và viết lại câu hỏi (Query Rewriter)
REWRITE_PROMPT = """
Bạn là một AI Query Rewriter cho hệ thống RAG kế toán VAS (Vietnam Accounting Standards).
Hãy sử dụng ngữ cảnh (chứa các thực thể, thuộc tính và ràng buộc hiện tại) để viết lại câu hỏi thô của người dùng thành một câu hỏi độc lập (Q_final) đầy đủ thực thể và rõ ràng về ngữ nghĩa.
Câu hỏi được viết lại này phải sẵn sàng để truy xuất chính xác thông tin từ kho tài liệu chuẩn mực kế toán Việt Nam.

Ngữ cảnh hiện tại:
- Thực thể (Entities): {entities}
- Thuộc tính (Attributes): {attributes}
- Ràng buộc (Constraints): {constraints}

Câu hỏi thô của người dùng:
"{query}"

Lưu ý quan trọng:
1. Câu hỏi độc lập được viết lại PHẢI rõ ràng, mạch lạc, sử dụng các thuật ngữ chuyên môn kế toán chính xác, và KHÔNG chứa các đại từ thay thế mơ hồ ("nó", "cái đó", "khoản đó", "điều kiện đó").
2. TỰ ĐỘNG SỬA LỖI CHÍNH TẢ: Nếu câu hỏi thô của người dùng chứa các lỗi chính tả gõ phím tiếng Việt rõ ràng (ví dụ: "gfi" ➔ "gì", "taì sản" ➔ "tài sản", "doah thu" ➔ "doanh thu"), bạn BẮT BUỘC phải sửa lại cho đúng chính tả tiếng Việt chuẩn khi viết câu hỏi mới.
3. Đừng cố gắng tự trả lời câu hỏi, mục tiêu của bạn chỉ là viết lại câu hỏi thành dạng đầy đủ thông tin để đem đi tìm kiếm tài liệu.
4. Chỉ trả về duy nhất câu hỏi độc lập được viết lại, không viết thêm lời dẫn hay giải thích gì khác.
"""

# 4. Prompt kết hợp ngữ cảnh sinh câu trả lời RAG cuối cùng (Answer Generator)
ANSWER_PROMPT = """
Bạn là một Trợ lý Kế toán chuyên nghiệp về Chuẩn mực Kế toán Việt Nam (VAS).
Dưới đây là tài liệu chuẩn mực liên quan tìm thấy từ cơ sở tri thức (Context), lịch sử hội thoại (History), và câu hỏi hiện tại đã tối ưu của người dùng.
Hãy sử dụng thông tin từ tài liệu để trả lời câu hỏi một cách chính xác, chi tiết, trung thực và chuyên nghiệp nhất.

Ngữ cảnh từ Chuẩn mực Kế toán VAS (Context):
{context}

Lịch sử hội thoại (History):
{chat_history}

Câu hỏi hiện tại của người dùng (đã tối ưu hóa):
"{query}"

Yêu cầu khi trả lời:
1. Trích dẫn nguồn cụ thể trong câu trả lời bằng cách chèn số thứ tự nguồn tương ứng ở dạng [Nguồn 1], [Nguồn 2], [Nguồn 3] ở cuối các câu hoặc mệnh đề có thông tin tham chiếu tới.
2. Trích dẫn rõ ràng tên Chuẩn mực, Chương, Điều, Khoản tương ứng (ví dụ: Chuẩn mực số 02, Điều 11) dựa trên thông tin tiêu đề đi kèm với mỗi nguồn.
3. Nếu câu hỏi không được giải quyết hoặc không có thông tin trong Context, hãy nêu rõ rằng "Tài liệu Chuẩn mực kế toán cung cấp không chứa thông tin này" và trả lời dựa trên kiến thức của bạn nhưng có cảnh báo rõ ràng.
4. Trả lời bằng tiếng Việt, giọng văn trang trọng, chuẩn nghiệp vụ kế toán Việt Nam.
"""
