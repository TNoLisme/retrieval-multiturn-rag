from typing import List, Dict, Union
from src.services.llm import get_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

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

def fallback_slm(query: str, active_chat: List[Union[str, Dict[str, str]]]) -> str:
    """
    Sử dụng LLM/SLM để thẩm định ý định đổi chủ đề nếu logic rule-based nghi ngờ.
    """
    llm = get_llm(temperature=0.0)
    prompt = ChatPromptTemplate.from_template(FALLBACK_PROMPT)
    chain = prompt | llm | StrOutputParser()
    
    # Định dạng lịch sử hội thoại thành chuỗi ngữ cảnh sạch
    formatted_lines = []
    for turn in active_chat[-4:]:  # Lấy tối đa 4 lượt cuối để làm ngữ cảnh
        if isinstance(turn, dict):
            role = "Người dùng" if turn.get("role") == "user" else "Trợ lý"
            content = turn.get("content", "")
            formatted_lines.append(f"{role}: {content}")
        else:
            formatted_lines.append(str(turn))
    context_str = "\n".join(formatted_lines)
    
    try:
        response = chain.invoke({"query": query, "context": context_str}).strip().lower()
        if "hard_shift" in response:
            print("[Boundary Node] SLM phát hiện chuyển chủ đề (hard_shift).")
            return "hard_shift"
        print("[Boundary Node] SLM xác định tiếp tục chủ đề cũ (continue).")
        return "continue"
    except Exception as e:
        print(f"[Boundary Node] Lỗi trong fallback_slm: {e}. Trả về continue làm mặc định.")
        return "continue"

def hinge_mem_check(query: str, active_chat: List[Union[str, Dict[str, str]]]) -> str:
    """
    Điểm kiểm tra ranh giới: So sánh nhanh sự trùng lặp từ khóa (Jaccard) giữa câu hỏi mới và câu hỏi/câu trả lời trước đó.
    Nếu không có từ khóa nào trùng nhau -> Chuyển sang LLM (fallback_slm) để quyết định.
    """
    if not active_chat:
        return "continue"
    
    # Lấy văn bản từ lượt chat cuối cùng
    last_turn = active_chat[-1]
    if isinstance(last_turn, dict):
        last_text = last_turn.get("content", "")
    else:
        last_text = str(last_turn)
        
    # Chuẩn hóa và chuyển sang tập hợp từ
    words_q = set(query.lower().split())
    words_h = set(last_text.lower().split())
    
    # Loại bỏ các hư từ/từ dừng cơ bản trong tiếng Việt để tránh nhiễu (nếu cần, ở đây dùng Jaccard thuần túy)
    intersection = words_q.intersection(words_h)
    
    if len(intersection) == 0:
        print("[Boundary Node] Không có từ khóa trùng nhau. Gọi SLM để kiểm tra...")
        return fallback_slm(query, active_chat)
        
    print(f"[Boundary Node] Có {len(intersection)} từ khóa trùng nhau. Tiếp tục chủ đề cũ.")
    return "continue"