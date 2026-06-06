import json
from typing import Dict, List, Any, Union
from src.core.schema import ConversationState
from src.services.llm import get_llm
from src.services.vector_db import add_memo_to_db, clear_memos_for_session
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Khởi tạo cache in-memory giả lập Redis
SESSION_STATES: Dict[str, ConversationState] = {}
SESSION_HISTORIES: Dict[str, List[Dict[str, str]]] = {}

def load_state_from_redis(session_id: str) -> ConversationState:
    """
    Nạp trạng thái hội thoại của phiên hiện tại từ Redis giả lập.
    """
    return SESSION_STATES.get(session_id)

def save_state_to_redis(session_id: str, state: ConversationState):
    """
    Lưu trạng thái hội thoại của phiên hiện tại vào Redis giả lập.
    """
    SESSION_STATES[session_id] = state

def load_history(session_id: str) -> List[Dict[str, str]]:
    """
    Nạp lịch sử hội thoại (Active Chat) của phiên hiện tại.
    """
    return SESSION_HISTORIES.get(session_id, [])

def save_history(session_id: str, query: str, response: str = None):
    """
    Lưu lượt trò chuyện mới vào lịch sử hội thoại.
    """
    if session_id not in SESSION_HISTORIES:
        SESSION_HISTORIES[session_id] = []
    
    SESSION_HISTORIES[session_id].append({"role": "user", "content": query})
    if response:
        SESSION_HISTORIES[session_id].append({"role": "assistant", "content": response})

def clear_session_cache(session_id: str):
    """
    Làm sạch dữ liệu của phiên hội thoại (phục vụ khi reset/hard_shift hoặc kết thúc phiên).
    """
    if session_id in SESSION_STATES:
        SESSION_STATES[session_id] = ConversationState()
    if session_id in SESSION_HISTORIES:
        SESSION_HISTORIES[session_id] = []
    
    # Xóa cả các memo lưu trong ChromaDB của session này
    clear_memos_for_session(session_id)


MEMO_SUMMARIZATION_PROMPT = """
Bạn là một trợ lý tóm tắt hội thoại kế toán.
Nhiệm vụ của bạn là đọc lịch sử hội thoại kế toán dưới đây và tóm tắt thành một chủ đề chính (Topic, dưới 10 từ) và một đoạn tóm tắt nội dung chính (Summary, dưới 50 từ).

Lịch sử hội thoại:
{chat_history}

Bạn BẮT BUỘC phải trả về kết quả theo định dạng JSON hợp lệ có dạng:
{{
  "topic": "Tên chủ đề ngắn gọn",
  "summary": "Đoạn tóm tắt nội dung chính đã trao đổi"
}}
"""

def archive_to_memo(session_id: str, active_chat: List[Union[str, Dict[str, str]]], old_state: ConversationState):
    """
    Tóm tắt lịch sử trò chuyện đang hoạt động của phiên hiện tại và lưu vào vector database.
    """
    if not active_chat:
        return
    
    # Chuẩn hóa lịch sử hội thoại sang dạng văn bản
    formatted_lines = []
    for turn in active_chat:
        if isinstance(turn, dict):
            role = "Người dùng" if turn.get("role") == "user" else "Trợ lý"
            content = turn.get("content", "")
            formatted_lines.append(f"{role}: {content}")
        else:
            formatted_lines.append(str(turn))
            
    chat_str = "\n".join(formatted_lines)
    
    # Gọi LLM thực hiện tóm tắt
    llm = get_llm(temperature=0.0)
    prompt = ChatPromptTemplate.from_template(MEMO_SUMMARIZATION_PROMPT)
    chain = prompt | llm | StrOutputParser()
    
    try:
        res_str = chain.invoke({"chat_history": chat_str}).strip()
        
        # Clean JSON markdown fences nếu có
        if res_str.startswith("```json"):
            res_str = res_str[7:]
        if res_str.endswith("```"):
            res_str = res_str[:-3]
        res_str = res_str.strip()
        
        data = json.loads(res_str)
        topic = data.get("topic", "Hội thoại Kế toán")
        summary = data.get("summary", "")
        
        # Lưu memo vào ChromaDB
        add_memo_to_db(
            session_id=session_id,
            summary=summary,
            topic=topic,
            entities=old_state.entities,
            attributes=old_state.attributes,
            history=active_chat
        )
        print(f"[State Service] Đã lưu lưu trữ cuộc hội thoại cũ thành Memo: Topic='{topic}'")
    except Exception as e:
        print(f"[State Service] Lỗi khi nén hội thoại cũ sang Memo: {e}. Sử dụng fallback tóm tắt thô.")
        # Fallback lưu trữ thô nếu LLM/JSON parsing lỗi
        try:
            add_memo_to_db(
                session_id=session_id,
                summary=f"Lịch sử hội thoại thô dài {len(formatted_lines)} lượt.",
                topic="Hội thoại cũ",
                entities=old_state.entities,
                attributes=old_state.attributes,
                history=active_chat
            )
        except Exception as add_err:
            print(f"[State Service] Thất bại hoàn toàn khi tạo Memo: {add_err}")
