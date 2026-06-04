import os
import uuid
import json
import chromadb
from typing import List, Dict, Any
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document

# Bộ lưu trữ RAM (In-Memory) để lưu trữ các memos hội thoại cũ, tránh ghi đĩa SQLite/ChromaDB
# Định dạng: { session_id: [{"summary": str, "topic": str, "entities": dict}] }
SESSION_MEMOS: Dict[str, List[Dict[str, Any]]] = {}

# Biến toàn cục để cache kết nối database (Singleton Pattern)
_VECTOR_DB_INSTANCE = None

def get_embeddings():
    """
    Trả về bộ tạo vector hóa câu chữ (nomic-embed-text) thông qua Ollama.
    """
    return OllamaEmbeddings(model="nomic-embed-text")

def get_vector_db(collection_name: str = "vas_expert_db"):
    """
    Trả về kết nối tới cơ sở dữ liệu vector Chroma (Khởi tạo 1 lần duy nhất).
    """
    global _VECTOR_DB_INSTANCE
    if _VECTOR_DB_INSTANCE is not None:
        return _VECTOR_DB_INSTANCE
        
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Đi lên 3 cấp từ src/services/ để tới thư mục gốc chứa vas_vector_db/
    project_root = os.path.dirname(os.path.dirname(current_dir))
    persist_dir = os.path.join(project_root, "vas_vector_db")
    
    # Sử dụng PersistentClient để giữ kết nối ổn định và an toàn
    client = chromadb.PersistentClient(path=persist_dir)
    
    _VECTOR_DB_INSTANCE = Chroma(
        client=client,
        embedding_function=get_embeddings(),
        collection_name=collection_name,
        collection_metadata={"hnsw:sync_threshold": 10000}
    )
    return _VECTOR_DB_INSTANCE

def query_vector_db(query_text: str, collection_name: str = "vas_expert_db", top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Tìm kiếm thông tin trong cơ sở dữ liệu tài liệu (ví dụ: các chuẩn mực kế toán).
    Đã được bọc lỗi phòng thủ để tránh lỗi chỉ mục HNSW làm sập hệ thống.
    """
    try:
        db = get_vector_db(collection_name)
        results = db.similarity_search_with_score(query_text, k=top_k)
        
        ret = []
        for doc, score in results:
            ret.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score)
            })
        return ret
    except Exception as e:
        print(f"[VectorDB Service] ❌ Lỗi kết nối hoặc truy vấn ChromaDB ({collection_name}): {e}")
        print("[VectorDB Service] 👉 Đang kích hoạt cơ chế Graceful Fallback (Trả về kết quả trống).")
        return []

def search_memo_db(query_text: str, session_id: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Tìm kiếm các ký ức dài hạn (memos) trong RAM liên quan đến chủ đề trước của session_id hiện tại.
    Sử dụng so khớp từ khóa/Jaccard đơn giản giúp hoạt động độc lập không cần DB.
    """
    memos = SESSION_MEMOS.get(session_id, [])
    if not memos:
        return []
        
    try:
        # Tách tập hợp từ của câu hỏi hiện tại để so khớp Jaccard với topic/summary của memo
        query_words = set(query_text.lower().split())
        matched_memos = []
        
        for memo in memos:
            memo_text = f"{memo.get('topic', '')} {memo.get('summary', '')}"
            memo_words = set(memo_text.lower().split())
            intersection = query_words.intersection(memo_words)
            
            # Tính điểm số trùng khớp từ
            score = len(intersection)
            matched_memos.append((memo, score))
            
        # Sắp xếp các memos theo số lượng từ trùng khớp giảm dần
        matched_memos.sort(key=lambda x: x[1], reverse=True)
        
        # Chỉ trả về các memo có ít nhất 1 từ trùng khớp hoặc lấy mặc định nếu danh sách nhỏ
        results = [x[0] for x in matched_memos]
        print(f"[VectorDB Service (RAM)] Tìm thấy {len(results)} memos trong RAM cho session {session_id}.")
        return results[:top_k]
    except Exception as e:
        print(f"[VectorDB Service (RAM)] Lỗi truy vấn Memo trên RAM: {e}")
        return []

def add_memo_to_db(session_id: str, summary: str, topic: str, entities: Dict[str, Any]):
    """
    Lưu bối cảnh hội thoại cũ (Memo) trực tiếp vào bộ nhớ RAM của phiên hiện tại.
    """
    try:
        if session_id not in SESSION_MEMOS:
            SESSION_MEMOS[session_id] = []
            
        SESSION_MEMOS[session_id].append({
            "summary": summary,
            "topic": topic,
            "entities": entities
        })
        print(f"[VectorDB Service (RAM)] Đã ghi nhớ cuộc hội thoại cũ vào RAM cho phiên {session_id} - Topic: {topic}")
    except Exception as e:
        print(f"[VectorDB Service (RAM)] Lỗi lưu memo vào RAM: {e}")

def clear_memos_for_session(session_id: str):
    """
    Xóa tất cả các memos liên quan đến session_id trong bộ nhớ RAM.
    """
    try:
        if session_id in SESSION_MEMOS:
            SESSION_MEMOS[session_id] = []
            print(f"[VectorDB Service (RAM)] Đã xóa toàn bộ memos trong RAM của session: {session_id}")
    except Exception as e:
        print(f"[VectorDB Service (RAM)] Lỗi khi xóa memos trong RAM: {e}")
