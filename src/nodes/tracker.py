import json
from src.core.schema import ConversationState, TrackerOutput
from src.services.llm import get_llm
from langchain_core.prompts import ChatPromptTemplate

TRACKER_PROMPT = """
Bạn là một AI State Tracker cho hệ thống RAG kế toán VAS (Vietnam Accounting Standards).
Nhiệm vụ của bạn là cập nhật trạng thái hội thoại (ConversationState) dựa trên câu hỏi mới của người dùng và trạng thái cũ.

Trạng thái cũ (JSON):
{old_state}

Câu hỏi mới:
"{query}"

Hướng dẫn cập nhật:
1. 'intent': Ý định hiện tại (ví dụ: "inquiry" - hỏi đáp, "compare" - so sánh, "list" - liệt kê).
2. 'entities': Các thực thể kế toán xuất hiện (Brand, Model, Chuẩn mực số, Tài sản, Doanh thu, Chi phí, Hàng tồn kho, Thuê tài sản...). Cập nhật các thực thể mới tìm thấy hoặc giữ các thực thể cũ nếu câu hỏi liên tục nói về chúng.
3. 'attributes': Các thuộc tính đi kèm (Màu sắc, Dung lượng, hoặc trong kế toán là các đặc tính cụ thể như: Giá gốc, Giá trị thanh lý, Khấu hao...).
4. 'constraints': Các giới hạn hoặc điều kiện ràng buộc (ví dụ: "giá trị > 20 triệu", "thời gian sử dụng hữu ích > 1 năm").
5. 'unresolved_references': Các đại từ thay thế hoặc tham chiếu mơ hồ chưa rõ nghĩa (ví dụ: "nó", "cái đó", "khoản đó", "điều kiện đó"). Hãy chỉ liệt kê những đại từ có trong câu hỏi mới mà chưa thể tự giải nghĩa từ câu hỏi mới đó.
6. 'need_retrieval': Xác định xem có thiếu thông tin quan trọng từ lịch sử để trả lời không (Ví dụ: có các 'unresolved_references' chưa thể tự giải nghĩa). Đặt là true nếu cần truy xuất dữ liệu quá khứ, ngược lại đặt là false.
7. 'confidence': Độ tin cậy của việc cập nhật (từ 0.0 đến 1.0).

Bạn PHẢI trả về kết quả theo định dạng JSON chứa cấu trúc phù hợp với schema sau:
{{
  "state": {{
    "intent": "inquiry",
    "entities": {{"key": "value"}},
    "attributes": {{"key": "value"}},
    "constraints": ["constraint1"],
    "unresolved_references": ["nó"]
  }},
  "need_retrieval": true,
  "confidence": 1.0
}}

Lưu ý: Chỉ trả về duy nhất chuỗi JSON hợp lệ, không bọc trong ```json...``` hay bất cứ lời dẫn nào khác.
"""

def state_tracker_node(query: str, old_state: ConversationState) -> TrackerOutput:
    """
    Node trích xuất thực thể, thuộc tính và cập nhật trạng thái hội thoại.
    """
    llm = get_llm(temperature=0.0)
    prompt = ChatPromptTemplate.from_template(TRACKER_PROMPT)
    
    # 1. Thử dùng with_structured_output của LangChain
    try:
        structured_llm = llm.with_structured_output(TrackerOutput)
        chain = prompt | structured_llm
        output = chain.invoke({"query": query, "old_state": old_state.model_dump_json()})
        print(f"[Tracker Node] Đã cập nhật State thành công bằng structured output. Need retrieval: {output.need_retrieval}")
        return output
    except Exception as e:
        print(f"[Tracker Node] Gặp lỗi structured output: {e}. Tiến hành fallback sang parse JSON thủ công...")
        
        # 2. Fallback thủ công nếu model local không hỗ trợ native tool calling / structured output
        from langchain_core.output_parsers import StrOutputParser
        chain = prompt | llm | StrOutputParser()
        res_str = chain.invoke({"query": query, "old_state": old_state.model_dump_json()}).strip()
        
        # Làm sạch chuỗi phản hồi
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
            print(f"[Tracker Node (Fallback)] Đã parse JSON thành công. Need retrieval: {output.need_retrieval}")
            return output
        except Exception as json_err:
            print(f"[Tracker Node] Thất bại hoàn toàn khi parse JSON: {json_err}. Raw output: {res_str}")
            # Trả về trạng thái cũ làm mặc định an toàn để không làm gãy pipeline
            return TrackerOutput(
                state=old_state,
                need_retrieval=False,
                confidence=0.5
            )