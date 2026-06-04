from src.core.schema import ConversationState
from src.services.llm import get_llm, REWRITE_PROMPT
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

def controlled_rewrite(query: str, state: ConversationState, retrieved_empty: bool) -> str:
    """
    Tái cấu trúc câu hỏi thô thành câu hỏi độc lập đầy đủ thông tin dựa trên trạng thái hội thoại.
    Nếu không tìm thấy thông tin bổ trợ trong quá khứ mà câu hỏi có đại từ mơ hồ -> Trả về câu hỏi làm rõ.
    """
    llm = get_llm(temperature=0.2)
    
    # Graceful Fallback: Nếu cần truy xuất memo (entities rỗng) nhưng không tìm thấy gì
    # → Pipeline không có đủ ngữ cảnh để rewrite → hỏi lại người dùng
    if retrieved_empty and not state.entities:
        ref_hint = state.unresolved_references[0] if state.unresolved_references else "đối tượng bạn đề cập"
        print(f"[Rewriter Node] Không tìm thấy ngữ cảnh phù hợp. Trả về Clarification Request (ref: '{ref_hint}').")
        return (
            f"Câu hỏi của bạn chưa rõ đang đề cập đến đối tượng kế toán nào "
            f"(có thể là '{ref_hint}'). Vui lòng nêu rõ tên cụ thể của tài sản, "
            f"chuẩn mực hoặc khoản mục kế toán bạn muốn hỏi."
        )

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