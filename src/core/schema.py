from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class ConversationState(BaseModel):
    intent: str = Field(default="inquiry", description="Ý định của người dùng")
    entities: Dict[str, str] = Field(default_factory=dict, description="Các thực thể như Brand, Model, User")
    attributes: Dict[str, str] = Field(default_factory=dict, description="Thuộc tính như Màu sắc, Dung lượng")
    constraints: List[str] = Field(default_factory=list, description="Giới hạn như giá cả, khoảng cách")
    unresolved_references: List[str] = Field(default_factory=list, description="Danh sách các đại từ thay thế chưa rõ nghĩa (như 'nó', 'cái đó') xuất hiện trong câu hỏi mới. BẮT BUỘC để trống [] nếu câu hỏi không chứa đại từ thay thế nào.")

class TrackerOutput(BaseModel):
    state: ConversationState
    need_retrieval: bool = Field(description="Đặt là true nếu câu hỏi mới chứa đại từ thay thế chưa rõ nghĩa, ngược lại luôn là false.")
    confidence: float