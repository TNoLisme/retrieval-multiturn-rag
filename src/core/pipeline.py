from src.core.schema import ConversationState
from src.nodes.boundary import hinge_mem_check
from src.nodes.tracker import state_tracker_node
from src.nodes.retriever import safe_merge
from src.nodes.rewriter import controlled_rewrite
from src.core.state import (
    load_state_from_redis, 
    save_state_to_redis, 
    load_history, 
    save_history, 
    archive_to_memo,
    clear_session_cache
)
from src.services.vector_db import search_memo_db

def vector_db_search(state: ConversationState, session_id: str, query: str = ""):
    """
    Tìm kiếm ký ức cũ (memos) trong Memo DB.
    Ưu tiên dùng entity values để tìm kiếm, fallback về attributes rồi câu hỏi gốc.
    KHÔNG dùng unresolved_references (đại từ như 'nó') làm query — vì pronoun
    không có nghĩa trong vector search.
    """
    if state.entities:
        query_term = " ".join(state.entities.values())
    elif state.attributes:
        query_term = " ".join(state.attributes.values())
    elif query:
        query_term = query
    else:
        query_term = "Kế toán VAS"
        
    print(f"[3. Retrieval & Fusion (Retrieve Memo)] Đang tìm kiếm ký ức trong Memo DB cho từ khóa: '{query_term}'...")
    return search_memo_db(query_term, session_id)

def run_pipeline(user_query: str, session_id: str) -> str:
    """
    Đầu vào: Câu hỏi thô của người dùng tại lượt t và session_id
    Đầu ra: Câu truy vấn độc lập hoàn chỉnh Q_final (hoặc câu hỏi làm rõ)
    """
    print(f"\n⚡ Khởi chạy State-Centric Adaptive Pipeline cho Session '{session_id}'")
    
    # 1. Nạp trạng thái cũ và lịch sử từ bộ nhớ đệm
    old_state = load_state_from_redis(session_id) or ConversationState()
    active_chat = load_history(session_id)
    
    print(f"   ├─ Query_t (Câu hỏi gốc): '{user_query}'")
    print(f"   ├─ Active Chat (Lịch sử ngắn): {len(active_chat)} lượt")
    print(f"   └─ State_t-1 (Trạng thái cũ): Entities={old_state.entities}, Unresolved={old_state.unresolved_references}")

    # 2. Lớp Phân tích Biên ngữ cảnh (Boundary Detection Layer)
    print("[1. Boundary Detection (HingeMem)] Đang kiểm tra biên hội thoại...")
    boundary = hinge_mem_check(user_query, active_chat)
    print(f"[1. Boundary Detection (HingeMem)] Kết quả phân tích biên: {boundary.upper()}")
    
    if boundary == "hard_shift":
        print("[1. Boundary Detection (HingeMem / Reset)] Phát hiện ĐỔI CHỦ ĐỀ. Đang nén lịch sử cũ vào Memo DB và Reset State...")
        archive_to_memo(session_id, active_chat, old_state)
        old_state = ConversationState()  # Khởi tạo lại trạng thái mới
        active_chat = []  # Làm sạch lịch sử ngắn hạn
        clear_session_cache(session_id)

    # 3. Lớp Quản lý Trạng thái (State Management Layer)
    print("[2. State Management (State Tracker + Checker)] Đang phân tích và cập nhật trạng thái...")
    tracker_out = state_tracker_node(user_query, old_state)
    new_state = tracker_out.state
    print(f"[2. State Management (State Tracker + Checker)] Trạng thái mới (State_t): Entities={new_state.entities}, Unresolved={new_state.unresolved_references}")
    print(f"[2. State Management (State Tracker + Checker)] Yêu cầu truy xuất (need_retrieval): {tracker_out.need_retrieval}")
    
    # 4. Lớp Truy xuất & Hợp nhất (Retrieval & Fusion Layer)
    retrieved_empty = False
    if tracker_out.need_retrieval:
        print("[3. Retrieval & Fusion (Retrieve Memo)] State chưa đủ thông tin (entities rỗng). Cần truy xuất ký ức quá khứ từ Memo DB...")
        memos = vector_db_search(new_state, session_id, query=user_query)
        if not memos:
            print("[3. Retrieval & Fusion (Retrieve Memo)] Kết quả: Không tìm thấy ký ức nào phù hợp (retrieved_empty = True).")
            retrieved_empty = True
        else:
            print(f"[3. Retrieval & Fusion (Retrieve Memo)] Kết quả: Tìm thấy {len(memos)} memo phù hợp.")
            print("[3. Retrieval & Fusion (Memory Fusion / Safe Merge)] Đang thực hiện Safe Merge ký ức vào trạng thái...")
            new_state = safe_merge(new_state, memos)
            print(f"[3. Retrieval & Fusion (Memory Fusion / Safe Merge)] Trạng thái sau Safe Merge: Entities={new_state.entities}")
    else:
        print("[3. Retrieval & Fusion] Bỏ qua bước truy xuất ký ức (State đã đủ thông tin — entities không rỗng).")

    # 5. Lớp Tái cấu trúc & Đầu ra (Generation Layer)
    print("[4. Generation Layer (Controlled Rewrite)] Đang sinh câu hỏi độc lập ($Q_final$)...")
    q_final = controlled_rewrite(user_query, new_state, retrieved_empty)
    print(f"[4. Generation Layer (Controlled Rewrite)] Đã viết lại câu hỏi: '{user_query}' ➔ '{q_final}'")
    
    # 6. Lưu trữ trạng thái và lịch sử cho lượt kế tiếp
    save_state_to_redis(session_id, new_state)
    save_history(session_id, user_query, q_final)
    
    return q_final
