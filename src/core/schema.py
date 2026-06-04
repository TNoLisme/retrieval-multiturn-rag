from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class ConversationState(BaseModel):
    intent: str = Field(default="inquiry", description="Ý định của người dùng (inquiry, compare, list...)")
    entities: Dict[str, str] = Field(default_factory=dict, description="Các thực thể kế toán đang được thảo luận (VD: {\"tài_sản\": \"Hàng tồn kho\"}). Đây là trường cốt lõi quyết định need_retrieval.")
    attributes: Dict[str, str] = Field(default_factory=dict, description="Thuộc tính/khía cạnh của thực thể đang được hỏi (VD: {\"khái_niệm\": \"Giá gốc\"})")
    constraints: List[str] = Field(default_factory=list, description="Các điều kiện giới hạn (VD: [\"áp dụng cho doanh nghiệp vừa và nhỏ\"])")
    unresolved_references: List[str] = Field(default_factory=list, description="Các đại từ thay thế ('nó', 'đó', 'cái đó'...) THỰC SỰ XUẤT HIỆN trong câu hỏi mới. Trường này chỉ mang tính ghi nhận, KHÔNG dùng để quyết định need_retrieval. Để trống [] nếu câu hỏi không chứa đại từ.")

class TrackerOutput(BaseModel):
    state: ConversationState
    need_retrieval: bool = Field(
        description="True NẾU VÀ CHỈ NẾU state.entities rỗng {} sau khi Tracker đã merge State_t-1 + Query_t. "
                    "Tức là: pipeline không biết đang hỏi về đối tượng kế toán nào → cần search Memo DB. "
                    "False nếu state.entities có ít nhất 1 entry (kể cả khi câu hỏi có dùng đại từ 'nó')."
    )
    confidence: float