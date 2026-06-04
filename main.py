import sys
import os
import uuid
from src.core.rag_system import VASRAGSystem, build_source_path
from src.core.state import clear_session_cache, load_history
from src.modules.chat_manager import ChatManager

# Tắt warning socket của pydantic nếu có
import warnings
warnings.filterwarnings("ignore", category=ResourceWarning)

def clean_source_text(raw_text):
    content = str(raw_text or "").strip()
    return content.split("NỘI DUNG:", 1)[-1].strip() if "NỘI DUNG:" in content else content

if __name__ == "__main__":
    # Thiết lập encoding xuất ra terminal hỗ trợ tiếng Việt trên Windows
    if sys.platform.startswith('win'):
        os.system('chcp 65001 > nul')
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
        
    print("=" * 60)
    print(" HỆ THỐNG TRUY VẤN RAG MULTI-TURN - KẾ TOÁN VAS (CLI RUNNER)")
    print(" (Mô phỏng hoàn toàn hoạt động của app.py)")
    print("=" * 60)
    
    session_id = str(uuid.uuid4())
    clear_session_cache(session_id)
    chat_manager = ChatManager()
    
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vas_vector_db")
    bot = VASRAGSystem(db_path)
    
    print(f"🔄 Đã tạo phiên làm việc mới: {session_id}")
    
    while True:
        try:
            user_input = input("\n👤 Người dùng: ").strip()
            if not user_input:
                continue
            if user_input.lower() == 'exit':
                print("👋 Tạm biệt!")
                break
            if user_input.lower() == 'reset':
                session_id = str(uuid.uuid4())
                clear_session_cache(session_id)
                print(f"🔄 Đã làm mới session. Tạo phiên làm việc mới: {session_id}")
                continue
                
            # 1. Nạp lịch sử ngắn hạn
            history = load_history(session_id)
            
            # 2. Chạy RAG system (Q_final rewriter + retrieval + generation)
            print("\n⚙️ Hệ thống đang xử lý...")
            result = bot.run(user_input, history, session_id)
            
            # 3. Hiển thị các bước trung gian của pipeline
            print(f"  └─ Câu hỏi gốc: '{result.get('original_query')}'")
            print(f"  └─ Truy vấn tối ưu ($Q_final$): '{result.get('standalone_query')}'")
            print(f"  └─ Từ khóa/Thực thể: {', '.join(result.get('keywords', []))}")
            print("-" * 50)
            
            # 4. Hiển thị nguồn trích dẫn
            sources = result.get("sources", [])
            if sources:
                print("📖 Cơ sở tri thức tìm thấy:")
                for idx, src in enumerate(sources, start=1):
                    meta = src.get("metadata", {})
                    path = build_source_path(meta)
                    print(f"  📍 Nguồn {idx}: {path}")
                    snippet = clean_source_text(src.get("content", ""))[:150].replace("\n", " ").strip() + "..."
                    print(f"     Nội dung: {snippet}")
                print("-" * 50)
            else:
                print("⚠️ Không có chunk nào được truy xuất từ cơ sở tri thức.")
                print("-" * 50)
                
            # 5. Hiển thị câu trả lời chính
            print(f"🤖 Trợ lý: {result['answer']}")
            print("=" * 60)
            
            # 6. Lưu chat sử dụng ChatManager
            # Tạo lịch sử dạng tin nhắn giống st.session_state.messages
            history.append({"role": "user", "content": user_input})
            history.append({
                "role": "assistant",
                "content": result["answer"],
                "sources": sources
            })
            chat_manager.save_chat(session_id, history, "Local RAG")
            
        except KeyboardInterrupt:
            print("\n👋 Thoát chương trình.")
            break
        except Exception as e:
            print(f"\n❌ Lỗi hệ thống: {e}")
