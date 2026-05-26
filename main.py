import sys
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
from src.services.vector_db import query_vector_db, search_memo_db

def vector_db_search(state: ConversationState, session_id: str):
    """
    Tìm kiếm ký ức cũ (memos) trong Memo DB dựa trên các thực thể hoặc đại từ chưa giải quyết.
    """
    # Sử dụng các đại từ chưa giải quyết hoặc thực thể để tìm kiếm
    query_term = ""
    if state.unresolved_references:
        query_term = " ".join(state.unresolved_references)
    elif state.entities:
        query_term = " ".join(state.entities.values())
    else:
        query_term = "Kế toán VAS"
        
    print(f"[Pipeline] Đang tìm kiếm ký ức trong Memo DB cho từ khóa: '{query_term}'...")
    return search_memo_db(query_term, session_id)

def run_pipeline(user_query: str, session_id: str) -> str:
    """
    Đầu vào: Câu hỏi thô của người dùng tại lượt t và session_id
    Đầu ra: Câu truy vấn độc lập hoàn chỉnh Q_final (hoặc câu hỏi làm rõ)
    """
    print(f"\n⚡ Chạy pipeline cho Session '{session_id}' - Query: '{user_query}'")
    
    # 1. Nạp trạng thái cũ và lịch sử từ bộ nhớ đệm
    old_state = load_state_from_redis(session_id) or ConversationState()
    active_chat = load_history(session_id)
    
    print(f"[Pipeline] State cũ: Entities={old_state.entities}, Unresolved={old_state.unresolved_references}")
    print(f"[Pipeline] Số lượt chat trong lịch sử: {len(active_chat)}")

    # 2. Kiểm tra biên hội thoại (Boundary Check)
    boundary = hinge_mem_check(user_query, active_chat)
    if boundary == "hard_shift":
        print("[Pipeline] Phát hiện ĐỔI CHỦ ĐỀ. Đang nén lịch sử cũ vào Memo DB và Reset State...")
        archive_to_memo(session_id, active_chat, old_state)
        old_state = ConversationState()  # Khởi tạo lại trạng thái mới
        active_chat = []  # Làm sạch lịch sử ngắn hạn
        clear_session_cache(session_id)

    # 3. Theo dõi trạng thái hội thoại (State Tracking)
    tracker_out = state_tracker_node(user_query, old_state)
    new_state = tracker_out.state
    print(f"[Pipeline] State mới cập nhật: Entities={new_state.entities}, Unresolved={new_state.unresolved_references}")
    
    # 4. Truy xuất và Hợp nhất ký ức cũ (Retrieval & Fusion)
    retrieved_empty = False
    if tracker_out.need_retrieval:
        print("[Pipeline] Cần truy xuất ký ức quá khứ...")
        memos = vector_db_search(new_state, session_id)
        if not memos:
            print("[Pipeline] Không tìm thấy ký ức nào phù hợp trong Memo DB.")
            retrieved_empty = True
        else:
            print(f"[Pipeline] Tìm thấy {len(memos)} memo phù hợp. Đang thực hiện Safe Merge...")
            new_state = safe_merge(new_state, memos)
            print(f"[Pipeline] State sau Safe Merge: Entities={new_state.entities}, Unresolved={new_state.unresolved_references}")

    # 5. Viết lại truy vấn cuối cùng (Final Rewrite)
    q_final = controlled_rewrite(user_query, new_state, retrieved_empty)
    
    # 6. Lưu trữ trạng thái và lịch sử cho lượt kế tiếp
    save_state_to_redis(session_id, new_state)
    save_history(session_id, user_query, q_final)
    
    return q_final

if __name__ == "__main__":
    # Thiết lập encoding xuất ra terminal hỗ trợ tiếng Việt trên Windows
    if sys.platform.startswith('win'):
        import os
        os.system('chcp 65001 > nul')
        
    print("=" * 60)
    print(" HỆ THỐNG TỐI ƯU TRUY VẤN RAG MULTI-TURN - KẾ TOÁN VAS")
    print(" Giao diện CLI tương tác (Nhập 'exit' để thoát, 'reset' để làm mới session)")
    print("=" * 60)
    
    session_id = "test_cli_session"
    # Đảm bảo dọn dẹp sạch cache khi khởi động CLI
    clear_session_cache(session_id)
    
    while True:
        try:
            user_input = input("\n👤 Người dùng: ").strip()
            if not user_input:
                continue
            if user_input.lower() == 'exit':
                print("👋 Tạm biệt!")
                break
            if user_input.lower() == 'reset':
                clear_session_cache(session_id)
                print("🔄 Đã làm mới session hiện tại.")
                continue
                
            # Chạy pipeline để sinh câu truy vấn tối ưu Q_final
            q_final = run_pipeline(user_input, session_id)
            print(f"\n🔍 [Q_final] Câu hỏi tối ưu: {q_final}")
            
            # Nếu không phải là câu hỏi làm rõ, tiến hành thử truy xuất tri thức thật từ vas_vector_db
            is_clarification = q_final.startswith("Hệ thống không tìm thấy") or q_final.startswith("Xin lỗi")
            if not is_clarification:
                print("\n📖 [RAG] Đang truy xuất tài liệu chuẩn mực kế toán VAS...")
                doc_results = query_vector_db(q_final, collection_name="vas_expert_db", top_k=1)
                if doc_results:
                    best_match = doc_results[0]
                    metadata = best_match["metadata"]
                    source = metadata.get("source", "Không rõ")
                    chapter = metadata.get("Chapter", "Không rõ")
                    article = metadata.get("Article", "Không rõ")
                    print(f"📍 Nguồn tài liệu: {source} ➔ {chapter} ➔ {article}")
                    print(f"📄 Nội dung trích dẫn:")
                    print("-" * 50)
                    print(best_match["content"])
                    print("-" * 50)
                    print(f"📊 Score tương đồng: {best_match['score']:.4f}")
                else:
                    print("❌ Không tìm thấy tài liệu nào tương ứng trong cơ sở dữ liệu tri thức.")
            else:
                # Nếu là câu hỏi làm rõ, hiển thị cho người dùng biết
                print(f"💬 Phản hồi làm rõ: {q_final}")
                
        except KeyboardInterrupt:
            print("\n👋 Thoát chương trình.")
            break
        except Exception as e:
            print(f"\n❌ Lỗi hệ thống: {e}")