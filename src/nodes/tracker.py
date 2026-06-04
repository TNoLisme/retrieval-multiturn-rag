import json
from src.core.schema import ConversationState, TrackerOutput
from src.services.llm import get_llm, TRACKER_PROMPT
from langchain_core.prompts import ChatPromptTemplate

def state_tracker_node(query: str, old_state: ConversationState) -> TrackerOutput:
    """
    Node trích xuất thực thể, thuộc tính và cập nhật trạng thái hội thoại.
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
            print(f"[Tracker Node] Đã cập nhật State thành công bằng structured output OpenAI. Need retrieval: {output.need_retrieval}")
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
        output = TrackerOutput(
            state=state,
            need_retrieval=bool(data.get("need_retrieval", False)),
            confidence=float(data.get("confidence", 1.0))
        )
        print(f"[Tracker Node (Local/Fallback)] Đã parse JSON thành công. Need retrieval: {output.need_retrieval}")
        return output
    except Exception as json_err:
        print(f"[Tracker Node] Thất bại hoàn toàn khi parse JSON: {json_err}. Raw output: {res_str}")
        # Trả về trạng thái cũ làm mặc định an toàn để không làm gãy pipeline
        return TrackerOutput(
            state=old_state,
            need_retrieval=False,
            confidence=0.5
        )