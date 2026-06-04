from typing import List, Dict, Any
from src.core.schema import ConversationState

def safe_merge(current_state: ConversationState, retrieved_memos: List[Dict[str, Any]]) -> ConversationState:
    """
    Điền các thông tin còn thiếu (Gap Filling) từ các ký ức dài hạn (Memo) vào trạng thái hiện tại.
    Giải nghĩa các đại từ thay thế (như 'nó', 'khoản đó') bằng cách phục hồi entities + attributes từ memo.
    
    Nguyên tắc bất biến:
    - Chỉ điền vào các ô TRỐNG (không ghi đè entities/attributes người dùng vừa đặt trong turn hiện tại).
    - Sau khi merge: nếu entities không rỗng → xóa unresolved_references (coi như đã giải quyết).
    """
    if not retrieved_memos:
        return current_state
    
    # Lấy memo có điểm phù hợp cao nhất (đứng đầu danh sách)
    memo = retrieved_memos[0]
    
    # Gap-fill entities từ memo
    memo_entities = memo.get("entities", {})
    if isinstance(memo_entities, dict):
        for key, value in memo_entities.items():
            if key not in current_state.entities:
                current_state.entities[key] = value
                print(f"[Retriever Node] Gap-fill entities: '{key}' = '{value}' (từ Memo).")
    
    # Gap-fill attributes từ memo (nếu state hiện tại chưa có)
    memo_attributes = memo.get("attributes", {})
    if isinstance(memo_attributes, dict):
        for key, value in memo_attributes.items():
            if key not in current_state.attributes:
                current_state.attributes[key] = value
                print(f"[Retriever Node] Gap-fill attributes: '{key}' = '{value}' (từ Memo).")

    # Sau khi merge: nếu đã có entities → đánh dấu unresolved_references đã được giải quyết
    if current_state.entities:
        current_state.unresolved_references = []
        print(f"[Retriever Node] Safe Merge hoàn tất. Entities: {current_state.entities}")
        
    return current_state