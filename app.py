import streamlit as st
import os
import uuid
from dotenv import load_dotenv
from src.core.rag_system import VASRAGSystem, build_source_path
from src.modules.chat_manager import ChatManager

# Nạp các biến môi trường
load_dotenv()

st.set_page_config(page_title="VAS Expert RAG", page_icon="📑", layout="wide")

chat_manager = ChatManager()

def clean_source_text(raw_text):
    """
    Làm sạch nội dung chunk hiển thị, bỏ tiền tố NGỮ CẢNH nếu có.
    """
    content = str(raw_text or "").strip()
    return content.split("NỘI DUNG:", 1)[-1].strip() if "NỘI DUNG:" in content else content

def render_sources(sources):
    """
    Hiển thị danh sách các nguồn chuẩn mực kế toán VAS được trích dẫn dưới dạng expander.
    """
    st.write("### Cơ sở tri thức tìm thấy")
    if not sources:
        st.info("Không có chunk nào được truy xuất từ cơ sở tri thức.")
        return
    for idx, src in enumerate(sources, start=1):
        meta = src.get("metadata", {}) or {}
        path = build_source_path(meta)
        details = []
        if meta.get("chunk_index") is not None:
            details.append(f"chunk_index={meta.get('chunk_index')}")
        if meta.get("source"):
            details.append(f"file={meta.get('source')}")
            
        title = f"📍 Nguồn {idx}: {path}"
        if details:
            title += f" ({', '.join(details)})"
            
        with st.expander(title, expanded=False):
            st.info(clean_source_text(src.get("content", "")))

# Khởi tạo trạng thái phiên trò chuyện Streamlit
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# Sidebar giao diện
with st.sidebar:
    st.header("📑 VAS RAG")
    
    # Nút tạo hội thoại mới
    if st.button("➕ Tạo cuộc trò chuyện mới", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

    st.divider()
    st.subheader("⚙️ Chế độ hoạt động")
    st.info("🤖 **Local RAG (Qwen-2.5 3B)**\nModel chạy trực tiếp qua Ollama trên máy của bạn.")

    st.divider()
    st.subheader("🕒 Lịch sử trò chuyện")
    
    # Hiển thị danh sách hội thoại cũ từ file JSON
    past_chats = chat_manager.list_chats()
    for chat in past_chats:
        with st.container():
            col_main, col_del = st.columns([0.8, 0.2])
            
            with col_main:
                # Bấm để tải lại hội thoại cũ
                if st.button(f"💬 {chat['title']}", key=f"msg_{chat['id']}", use_container_width=True):
                    loaded_data = chat_manager.load_chat(chat['id'])
                    if loaded_data:
                        st.session_state.messages = loaded_data['messages']
                        st.session_state.session_id = loaded_data['session_id']
                        st.rerun()
            
            with col_del:
                # Bấm để xóa hội thoại cũ
                if st.button("❌", key=f"del_{chat['id']}", help="Xóa cuộc trò chuyện này"):
                    chat_manager.delete_chat(chat['id'])
                    if st.session_state.session_id == chat['id']:
                        st.session_state.messages = []
                        st.session_state.session_id = str(uuid.uuid4())
                    st.rerun()

@st.cache_resource
def load_bot():
    """
    Khởi tạo duy nhất một đối tượng VAS RAG Engine và cache lại để tăng tốc độ phản hồi.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, "vas_vector_db")
    return VASRAGSystem(db_path)

bot = load_bot()

# Khu vực chính của màn hình
st.title("📑 Trợ lý Kế toán (VAS RAG)")
st.caption("Chế độ hiện tại: Local RAG (Qwen-2.5 3B)")

# Hiển thị các tin nhắn trong phiên trò chuyện hiện tại
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        if m["role"] == "assistant" and m.get("sources"):
            render_sources(m.get("sources", []))
        st.markdown(m["content"])

# Xử lý nhập tin nhắn mới
if prompt := st.chat_input("Hỏi về VAS..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # Trạng thái đang xử lý hiển thị các bước trung gian của pipeline tối ưu hóa
        with st.status("Hệ thống đang xử lý...", expanded=False):
            result = bot.run(prompt, st.session_state.messages[:-1], st.session_state.session_id)
            
            st.write(f"**Câu hỏi gốc:** {result.get('original_query', prompt)}")
            st.write(f"**Truy vấn độc lập ($Q_{{final}}$):** {result.get('standalone_query', '')}")
            st.write(f"**Thực thể trích xuất:** {', '.join(result.get('keywords', []))}")
            
        st.divider()
        
        # Hiển thị nguồn trích dẫn từ ChromaDB
        render_sources(result.get("sources", []))
        
        # Hiển thị câu trả lời chính
        st.markdown(result["answer"])
        
        # Lưu câu trả lời của trợ lý kèm theo nguồn trích dẫn
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": result["answer"],
                "sources": result.get("sources", []),
            }
        )
        
        # Đồng bộ lưu cuộc trò chuyện vào file JSON
        chat_manager.save_chat(st.session_state.session_id, st.session_state.messages, "Local RAG")
        
        # Tự động reload để sidebar cập nhật tiêu đề cuộc trò chuyện ngay sau câu hỏi đầu tiên
        # if len(st.session_state.messages) <= 2:
        #     st.rerun()
