from typing import List, Dict, Union
from src.services.llm import get_llm, FALLBACK_PROMPT
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Hư từ / Từ dừng tiếng Việt phổ biến — không dùng để so khớp ngữ nghĩa
VIETNAMESE_STOP_WORDS = {
    "là", "gì", "có", "của", "và", "trong", "theo", "các", "một", "hay",
    "để", "cho", "với", "từ", "về", "tại", "khi", "thì", "mà", "nên",
    "được", "đã", "sẽ", "đang", "bị", "ra", "vào", "lên", "xuống",
    "này", "đó", "kia", "ấy", "rằng", "như", "vì", "nếu", "nhưng",
    "còn", "cũng", "đều", "rất", "quá", "hơn", "hết", "nhiều", "ít",
    "những", "hãy", "phải", "cần", "đến", "qua", "sau", "trước",
    "không", "chưa", "chỉ", "thế", "vậy", "nào", "đây", "khoản",
    "cái", "loại", "dạng", "kiểu", "phần", "mức", "số", "lần",
    "?", ".", ",", "!", ":", ";", "(", ")", "[", "]"
}

# Đại từ thay thế tiếng Việt — LUÔN chỉ đến ngữ cảnh cũ → LUÔN là continue
# (Không bao giờ là hard_shift vì đại từ không thể mở đầu chủ đề hoàn toàn mới)
VIETNAMESE_REFERRING_PRONOUNS = {
    # Đại từ ngôi 3 số ít
    "nó", "hắn", "y",
    # Đại từ ngôi 3 số nhiều
    "chúng", "họ", "bọn đó", "bọn họ", "chúng nó",
    # Đại từ chỉ định thay thế vật/khái niệm
    "đó", "kia", "ấy", "khoản đó", "cái đó", "loại đó", "phần đó",
    "mục đó", "hạng mục đó", "chuẩn mực đó", "phương pháp đó",
    "điều đó", "điều này", "vấn đề đó", "trường hợp đó",
    # Đại từ chỉ định thay thế số nhiều / nhóm
    "chúng đó", "các đó", "những đó", "loại này", "khoản này",
    "mục này", "hạng mục này",
}

import re

def _clean_and_tokenize(text: str) -> list:
    """Thay thế các ký tự đặc biệt/dấu câu bằng khoảng trắng để tránh dính chữ và chia thành danh sách từ."""
    cleaned = re.sub(r'[^\w\s\d]', ' ', text.lower())
    return cleaned.split()

def _contains_referring_pronoun(query: str) -> str | None:
    """Kiểm tra câu hỏi có chứa đại từ thay thế không (dưới dạng từ/cụm từ độc lập)."""
    q_tokens = _clean_and_tokenize(query)
    if not q_tokens:
        return None
    
    q_str = " " + " ".join(q_tokens) + " "
    
    for pronoun in VIETNAMESE_REFERRING_PRONOUNS:
        p_tokens = _clean_and_tokenize(pronoun)
        if not p_tokens:
            continue
        p_str = " " + " ".join(p_tokens) + " "
        if p_str in q_str:
            return pronoun
    return None

def _content_words(text: str) -> set:
    """Tách từ và loại bỏ stop words để chỉ giữ lại từ mang nội dung."""
    words = set(text.lower().split())
    return words - VIETNAMESE_STOP_WORDS

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
    Điểm kiểm tra ranh giới dựa trên Event Segmentation Theory (HingeMem).
    
    3 lớp kiểm tra theo thứ tự ưu tiên:
    [LAYER 0] Rule-based: Query có đại từ thay thế? → LUÔN continue (đại từ không mở chủ đề mới)
    [LAYER 1] Rule-based: Content-word Jaccard ≥ 2 từ trùng? → continue
    [LAYER 2] SLM fallback: Gọi LLM để phán xét ngữ nghĩa khi không chắc
    """
    if not active_chat:
        return "continue"
    
    # --- [LAYER 0] Pronoun Pre-check (Rule-based, không tốn inference) ---
    # Lý thuyết HingeMem: đại từ thay thế LUÔN chỉ đến ngữ cảnh cũ → không thể là hard_shift
    found_pronoun = _contains_referring_pronoun(query)
    if found_pronoun:
        print(f"[Boundary Node] Phát hiện đại từ thay thế '{found_pronoun}' → CONTINUE (tham chiếu ngữ cảnh cũ).")
        return "continue"
    
    # --- [LAYER 1] Content-word Jaccard ---
    # Lấy văn bản từ lượt chat cuối cùng
    last_turn = active_chat[-1]
    if isinstance(last_turn, dict):
        last_text = last_turn.get("content", "")
    else:
        last_text = str(last_turn)
        
    # Chỉ so sánh các từ nội dung (đã lọc stop words) để tránh false positive
    content_q = _content_words(query)
    content_h = _content_words(last_text)
    
    # Nếu sau khi lọc, một trong hai là rỗng → không thể so sánh → gọi SLM
    if not content_q or not content_h:
        print("[Boundary Node] Không đủ từ nội dung để so sánh. Gọi SLM để kiểm tra...")
        return fallback_slm(query, active_chat)

    intersection = content_q.intersection(content_h)
    
    if len(intersection) == 0:
        print("[Boundary Node] Không có từ khóa nội dung trùng nhau. Gọi SLM để kiểm tra...")
        return fallback_slm(query, active_chat)
    
    if len(intersection) == 1:
        # Chỉ 1 từ trùng có thể là ngẫu nhiên — gọi SLM để xác nhận
        print(f"[Boundary Node] Chỉ có 1 từ nội dung trùng nhau ({intersection}). Gọi SLM để xác nhận...")
        return fallback_slm(query, active_chat)
        
    print(f"[Boundary Node] Có {len(intersection)} từ khóa nội dung trùng nhau ({intersection}). Tiếp tục chủ đề cũ.")
    return "continue"