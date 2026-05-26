from src.core.schema import ConversationState
from src.services.llm import get_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

REWRITE_PROMPT = """
Bạn là một AI Query Rewriter cho hệ thống RAG kế toán VAS (Vietnam Accounting Standards).
Hãy sử dụng ngữ cảnh (chứa các thực thể, thuộc tính và ràng buộc hiện tại) để viết lại câu hỏi thô của người dùng thành một câu hỏi độc lập (Q_final) đầy đủ thực thể và ngữ nghĩa.
Câu hỏi được viết lại này phải sẵn sàng để truy xuất chính xác thông tin từ kho tài liệu chuẩn mực kế toán Việt Nam.

Ngữ cảnh hiện tại:
- Thực thể (Entities): {entities}
- Thuộc tính (Attributes): {attributes}
- Ràng buộc (Constraints): {constraints}

Câu hỏi thô của người dùng:
"{query}"

Lưu ý quan trọng:
1. Câu hỏi độc lập được viết lại PHẢI rõ ràng, mạch lạc, sử dụng các thuật ngữ chuyên môn kế toán chính xác, và KHÔNG chứa các đại từ thay thế mơ hồ ("nó", "khoản đó", "đối tượng đó", "điều kiện đó").
2. Đừng cố gắng tự trả lời câu hỏi, mục tiêu của bạn chỉ là viết lại câu hỏi thành dạng đầy đủ thông tin để đem đi tìm kiếm tài liệu.
3. Chỉ trả về duy nhất câu hỏi độc lập được viết lại, không viết thêm lời dẫn hay giải thích gì khác.
"""

def controlled_rewrite(query: str, state: ConversationState, retrieved_empty: bool) -> str:
    """
    Tái cấu trúc câu hỏi thô thành câu hỏi độc lập đầy đủ thông tin dựa trên trạng thái hội thoại.
    Nếu không tìm thấy thông tin bổ trợ trong quá khứ mà câu hỏi có đại từ mơ hồ -> Trả về câu hỏi làm rõ.
    """
    llm = get_llm(temperature=0.2)
    
    # Graceful Fallback: Nếu hệ thống cần thông tin cũ nhưng không tìm thấy gì trong Memo DB
    if retrieved_empty and state.unresolved_references:
        ref = state.unresolved_references[0]
        print(f"[Rewriter Node] Không tìm thấy ký ức tương ứng cho '{ref}'. Trả về Clarification Request.")
        return f"Hệ thống không tìm thấy thông tin hoặc ngữ cảnh cũ về '{ref}' mà bạn nhắc đến. Vui lòng cung cấp thêm thông tin chi tiết."

    prompt = ChatPromptTemplate.from_template(REWRITE_PROMPT)
    
    # Kết hợp các thành phần của State thành các tham số truyền vào Prompt
    entities_str = json_format(state.entities)
    attributes_str = json_format(state.attributes)
    constraints_str = ", ".join(state.constraints) if state.constraints else "Không có"
    
    chain = prompt | llm | StrOutputParser()
    try:
        res = chain.invoke({
            "query": query, 
            "entities": entities_str, 
            "attributes": attributes_str, 
            "constraints": constraints_str
        })
        q_final = res.strip()
        print(f"[Rewriter Node] Đã viết lại câu hỏi: '{query}' -> '{q_final}'")
        return q_final
    except Exception as e:
        print(f"[Rewriter Node] Lỗi khi viết lại câu hỏi: {e}. Trả về câu hỏi gốc làm fallback.")
        return query

def json_format(d) -> str:
    if not d:
        return "Không có"
    try:
        import json
        return json.dumps(d, ensure_ascii=False)
    except Exception:
        return str(d)