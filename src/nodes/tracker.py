import json
from src.core.schema import ConversationState, TrackerOutput
from src.services.llm import get_llm, TRACKER_PROMPT
from langchain_core.prompts import ChatPromptTemplate

# Đại từ thay thế tiếng Việt cần theo dõi (đồng bộ với boundary.py)
VIETNAMESE_PRONOUNS = {
    # Số ít
    "nó", "hắn", "y",
    # Số nhiều
    "chúng", "họ", "bọn đó", "chúng nó",
    # Chỉ định thay thế
    "đó", "kia", "ấy", "cái đó", "khoản đó", "loại này", "cái này",
    "phương pháp đó", "chuẩn mực đó", "đối tượng này", "mục này",
    "loại đó", "khoản này", "hạng mục này", "phần đó",
    "điều đó", "điều này", "vấn đề đó", "trường hợp đó",
    "chúng đó", "những đó", "các đó",
}

def _sanitize_output(query: str, state: ConversationState, need_retrieval_from_llm: bool) -> TrackerOutput:
    """
    Post-processing bắt buộc sau khi LLM trả về kết quả:
    1. Lọc unresolved_references: chỉ giữ các từ THỰC SỰ xuất hiện trong câu hỏi.
    2. Tính lại need_retrieval dựa trên logic đúng: entities rỗng = cần truy xuất.
       (Không dùng giá trị need_retrieval của LLM vì model nhỏ hay sai)
    """
    query_lower = query.lower()
    
    # Lọc unresolved_references: chỉ giữ lại từ/cụm từ có trong query thực tế
    validated_refs = [
        ref for ref in state.unresolved_references
        if ref.lower() in query_lower
    ]
    state.unresolved_references = validated_refs
    
    # Tính lại need_retrieval theo logic đúng: True ↔ entities rỗng
    actual_need_retrieval = len(state.entities) == 0
    
    return TrackerOutput(
        state=state,
        need_retrieval=actual_need_retrieval,
        confidence=1.0 if not actual_need_retrieval else 0.8
    )

def state_tracker_node(query: str, old_state: ConversationState) -> TrackerOutput:
    """
    Node trích xuất thực thể, thuộc tính và cập nhật trạng thái hội thoại.
    Sau khi LLM trả về, áp dụng post-processing để đảm bảo logic đúng.
    """
    import os
    llm = get_llm(temperature=0.0)
    prompt = ChatPromptTemplate.from_template(TRACKER_PROMPT)
    
    openai_key = os.getenv("OPENAI_API_KEY")
    
    # 1. Chỉ sử dụng structured output của LangChain nếu có API Key của OpenAI
    if openai_key:
        try:
            structured_llm = llm.with_structured_output(TrackerOutput)
            chain = prompt | structured_llm
            output = chain.invoke({"query": query, "old_state": old_state.model_dump_json()})
            output = _sanitize_output(query, output.state, output.need_retrieval)
            print(f"[Tracker Node] Đã cập nhật State (OpenAI). Need retrieval: {output.need_retrieval}")
            return output
        except Exception as e:
            print(f"[Tracker Node] Gặp lỗi structured output OpenAI: {e}. Fallback sang parse JSON...")
            
    # 2. Sử dụng sinh chuỗi JSON thuần túy (cho mô hình local Ollama hoặc khi fallback)
    from langchain_core.output_parsers import StrOutputParser
    import re
    chain = prompt | llm | StrOutputParser()
    res_str = chain.invoke({"query": query, "old_state": old_state.model_dump_json()}).strip()
    
    # Làm sạch chuỗi phản hồi bằng Regex để trích xuất JSON nằm giữa { và }
    match = re.search(r'\{.*\}', res_str, re.DOTALL)
    if match:
        res_str = match.group(0)
    else:
        if res_str.startswith("```json"):
            res_str = res_str[7:]
        if res_str.endswith("```"):
            res_str = res_str[:-3]
        res_str = res_str.strip()
    
    try:
        data = json.loads(res_str)
        state_data = data.get("state", {})
        state = ConversationState(
            intent=state_data.get("intent", "inquiry"),
            entities=state_data.get("entities", {}),
            attributes=state_data.get("attributes", {}),
            constraints=state_data.get("constraints", []),
            unresolved_references=state_data.get("unresolved_references", [])
        )
        # Áp dụng post-processing để đảm bảo logic đúng
        output = _sanitize_output(query, state, bool(data.get("need_retrieval", False)))
        print(f"[Tracker Node (Local/Fallback)] Đã parse JSON thành công. Need retrieval: {output.need_retrieval}")
        return output
    except Exception as json_err:
        print(f"[Tracker Node] Thất bại hoàn toàn khi parse JSON: {json_err}. Raw output: {res_str}")
        # Trả về trạng thái cũ làm mặc định an toàn để không làm gãy pipeline
        return TrackerOutput(
            state=old_state,
            need_retrieval=len(old_state.entities) == 0,
            confidence=0.5
        )