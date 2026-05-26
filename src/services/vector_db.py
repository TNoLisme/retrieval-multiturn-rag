import os
import uuid
import json
from typing import List, Dict, Any
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document

def get_embeddings():
    """
    Trả về bộ tạo vector hóa câu chữ (nomic-embed-text) thông qua Ollama.
    """
    return OllamaEmbeddings(model="nomic-embed-text")

def get_vector_db(collection_name: str = "vas_expert_db"):
    """
    Trả về kết nối tới cơ sở dữ liệu vector Chroma.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Đi lên 3 cấp từ src/services/ để tới thư mục gốc chứa vas_vector_db/
    project_root = os.path.dirname(os.path.dirname(current_dir))
    persist_dir = os.path.join(project_root, "vas_vector_db")
    
    return Chroma(
        persist_directory=persist_dir,
        embedding_function=get_embeddings(),
        collection_name=collection_name
    )

def query_vector_db(query_text: str, collection_name: str = "vas_expert_db", top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Tìm kiếm thông tin trong cơ sở dữ liệu tài liệu (ví dụ: các chuẩn mực kế toán).
    """
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

def search_memo_db(query_text: str, session_id: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Tìm kiếm các ký ức dài hạn (memos) liên quan đến chủ đề trước của session_id hiện tại.
    """
    db = get_vector_db("vas_memo_db")
    
    try:
        # Sử dụng bộ lọc metadata để chỉ lấy các memos thuộc session_id này
        results = db.similarity_search(
            query_text,
            k=top_k,
            filter={"session_id": session_id}
        )
        
        memos = []
        for doc in results:
            entities = {}
            if "entities" in doc.metadata:
                try:
                    entities = json.loads(doc.metadata["entities"])
                except Exception:
                    pass
            memos.append({
                "summary": doc.page_content,
                "entities": entities,
                "topic": doc.metadata.get("topic", "")
            })
        return memos
    except Exception as e:
        print(f"[VectorDB Service] Lỗi khi truy vấn Memo DB: {e}")
        return []

def add_memo_to_db(session_id: str, summary: str, topic: str, entities: Dict[str, Any]):
    """
    Nén và lưu bối cảnh hội thoại cũ vào Memo DB để truy xuất sau này khi đổi chủ đề (hard_shift).
    """
    db = get_vector_db("vas_memo_db")
    
    doc = Document(
        page_content=f"Topic: {topic}\nSummary: {summary}",
        metadata={
            "session_id": session_id,
            "topic": topic,
            "entities": json.dumps(entities, ensure_ascii=False)
        }
    )
    
    # Sinh ID duy nhất cho tài liệu memo
    db.add_documents([doc], ids=[str(uuid.uuid4())])
    print(f"[VectorDB Service] Đã lưu memo thành công cho phiên {session_id} - Topic: {topic}")

def clear_memos_for_session(session_id: str):
    """
    Xóa tất cả các memos liên quan đến session_id trong Memo DB.
    """
    db = get_vector_db("vas_memo_db")
    try:
        db.delete(where={"session_id": session_id})
        print(f"[VectorDB Service] Đã xóa toàn bộ memos của session: {session_id}")
    except Exception as e:
        print(f"[VectorDB Service] Lỗi khi xóa memos của session: {e}")

