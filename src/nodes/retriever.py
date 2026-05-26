from typing import List, Dict, Any
from src.core.schema import ConversationState

def safe_merge(current_state: ConversationState, retrieved_memos: List[Dict[str, Any]]) -> ConversationState:
    """
    Điền các thông tin thực thể còn thiếu (Gap Filling) từ các ký ức dài hạn (Memo) vào trạng thái hiện tại.
    Giúp giải nghĩa các đại từ thay thế (như 'nó', 'khoản đó') dựa trên ngữ cảnh đã tìm thấy.
    """
    if not retrieved_memos:
        return current_state
    
    # Lấy memo có độ tương đồng cao nhất (đầu tiên trong danh sách)
    memo = retrieved_memos[0] 
    
    # Chỉ điền thông tin vào các ô trống (không ghi đè các thực thể mới người dùng vừa cập nhật)
    memo_entities = memo.get("entities", {})
    if isinstance(memo_entities, dict):
        for key, value in memo_entities.items():
            if key not in current_state.entities:
                current_state.entities[key] = value
                print(f"[Retriever Node] Đã điền thêm thực thể '{key}': '{value}' từ Memo.")
            
    # Xóa danh sách đại từ mơ hồ vì đã giải quyết/hợp nhất xong ngữ cảnh
    if current_state.entities:
        current_state.unresolved_references = []
        
    return current_state