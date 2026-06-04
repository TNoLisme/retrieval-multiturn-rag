import os
from typing import List, Dict, Any
from src.core.schema import ConversationState
from src.core.pipeline import run_pipeline
from src.core.state import load_state_from_redis
from src.services.llm import get_llm, ANSWER_PROMPT
from src.services.vector_db import query_vector_db
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

ORDERED_KEYS = ["Standard", "Chapter", "Section", "Article", "Point"]

def build_source_path(metadata):
    """
    Hàm định dạng đường dẫn tiêu đề từ metadata của chunk.
    """
    headings = str((metadata or {}).get("headings", "")).strip()
    if headings:
        return headings
    path_parts = [str(metadata.get(k)) for k in ORDERED_KEYS if metadata.get(k)]
    if path_parts:
        return " ➔ ".join(path_parts)
    return str(metadata.get("source") or metadata.get("chunk_file") or "N/A")

class VASRAGSystem:
    def __init__(self, db_path: str = None):
        self.db_path = db_path
        
        # Khởi tạo bộ máy tìm kiếm từ khóa BM25 từ toàn bộ tài liệu trong Vector DB
        from src.services.vector_db import get_vector_db
        from langchain_core.documents import Document
        from langchain_community.retrievers import BM25Retriever
        
        try:
            db = get_vector_db("vas_expert_db")
            all_data = db.get()
            if all_data and all_data.get('documents'):
                documents = [
                    Document(page_content=text, metadata=meta)
                    for text, meta in zip(all_data['documents'], all_data['metadatas'])
                ]
                self.bm25_retriever = BM25Retriever.from_documents(documents)
                self.bm25_retriever.k = 5
                print(f"[RAG System] Đã nạp thành công {len(documents)} chunks cho bộ máy tìm kiếm BM25.")
            else:
                self.bm25_retriever = None
                print("[RAG System] Không tìm thấy tài liệu nào trong database để xây dựng BM25.")
        except Exception as e:
            self.bm25_retriever = None
            print(f"[RAG System] Lỗi khởi tạo bộ máy BM25: {e}. Hệ thống sẽ chỉ sử dụng Vector Search làm mặc định.")

    def hybrid_retrieve(self, standalone: str, keywords: List[str], top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Thực hiện truy xuất lai (Hybrid Search) kết hợp Vector Search + BM25 Search + Reciprocal Rank Fusion (RRF)
        """
        from src.services.vector_db import get_vector_db
        
        # 1. Thực hiện Vector Search (k = 5)
        vec_docs = []
        try:
            db = get_vector_db("vas_expert_db")
            results = db.similarity_search_with_score(standalone, k=5)
            for doc, score in results:
                vec_docs.append(doc)
        except Exception as e:
            print(f"[RAG System] Lỗi truy xuất Vector Search: {e}")
            
        # 2. Thực hiện BM25 Search (k = 5)
        bm25_docs = []
        if self.bm25_retriever is not None and keywords:
            try:
                # Trích xuất chuỗi từ khóa để tìm kiếm bằng BM25
                kw_str = " ".join(keywords)
                bm25_docs = self.bm25_retriever.invoke(kw_str)[:5]
            except Exception as e:
                print(f"[RAG System] Lỗi truy xuất BM25: {e}")
                
        # Nếu cả 2 bộ máy tìm kiếm đều không hoạt động hoặc không tìm thấy gì
        if not vec_docs and not bm25_docs:
            return []
            
        # 3. Thuật toán Reciprocal Rank Fusion (RRF) để trộn và xếp hạng kết quả
        ranked_results = {}
        vector_weight = 1.0
        bm25_weight = 0.8  # Trọng số ưu tiên Vector Search cao hơn một chút về mặt ngữ cảnh
        
        # Duyệt qua kết quả Vector
        for i, doc in enumerate(vec_docs):
            content = doc.page_content
            score = vector_weight * (1.0 / (i + 1))
            ranked_results[content] = {"doc": doc, "score": score}
            
        # Duyệt qua kết quả BM25
        for i, doc in enumerate(bm25_docs):
            content = doc.page_content
            score = bm25_weight * (1.0 / (i + 1))
            if content in ranked_results:
                # Nếu trùng lặp: cộng dồn điểm số xếp hạng
                ranked_results[content]["score"] += score
            else:
                ranked_results[content] = {"doc": doc, "score": score}
                
        # Sắp xếp các tài liệu theo điểm RRF giảm dần
        sorted_results = sorted(ranked_results.values(), key=lambda x: x["score"], reverse=True)
        
        # Trích xuất và định dạng kết quả trả về
        ret = []
        for item in sorted_results[:top_k]:
            doc = item["doc"]
            ret.append({
                "content": doc.page_content,
                "metadata": doc.metadata
            })
        return ret
        
    def run(self, prompt: str, chat_history: List[Dict[str, str]], session_id: str) -> Dict[str, Any]:
        """
        Chạy toàn bộ RAG pipeline:
        1. Gọi query rewriter pipeline sinh Q_final
        2. Dùng Q_final để truy xuất lai (Hybrid Search)
        3. Kết hợp Context + History + Q_final để LLM sinh câu trả lời cuối cùng có trích dẫn
        """
        # 1. Chạy query rewriter pipeline
        q_final = run_pipeline(prompt, session_id)
        
        # Lấy state mới cập nhật để trích xuất thực thể/từ khóa hiển thị lên UI và chạy BM25
        current_state = load_state_from_redis(session_id) or ConversationState()
        keywords = list(current_state.entities.values()) + list(current_state.attributes.values())
        if not keywords:
            # Nếu state chưa trích xuất được từ khóa, dùng các từ của câu hỏi làm từ khóa mặc định
            keywords = [w for w in q_final.split() if len(w) > 2]
            
        # Kiểm tra xem q_final có phải câu hỏi làm rõ không
        is_clarification = q_final.startswith("Hệ thống không tìm thấy") or q_final.startswith("Xin lỗi")
        
        sources = []
        answer = ""
        
        if is_clarification:
            # Nếu là câu hỏi làm rõ, trả về luôn làm câu trả lời chính
            answer = q_final
        else:
            # 2. Truy xuất tài liệu lai (Hybrid Search: Vector + BM25)
            sources = self.hybrid_retrieve(q_final, keywords, top_k=3)
                 
            # 3. Tạo ngữ cảnh văn bản cho prompt
            context_str = ""
            if sources:
                context_chunks = []
                for idx, src in enumerate(sources):
                    path = build_source_path(src["metadata"])
                    context_chunks.append(f"--- Nguồn {idx+1} (Tiêu đề: {path}) ---\n{src['content']}")
                context_str = "\n\n".join(context_chunks)
            else:
                context_str = "Không có tài liệu chuẩn mực nào tìm thấy."
                
            # 4. Định dạng lịch sử trò chuyện (Chỉ lấy 2 tin gần nhất vì Q_final đã chứa đủ thực thể được phân tích)
            history_lines = []
            for msg in chat_history[-2:]: # Lấy 2 tin nhắn cuối
                role = "Người dùng" if msg["role"] == "user" else "Trợ lý"
                history_lines.append(f"{role}: {msg['content']}")
            history_str = "\n".join(history_lines) if history_lines else "Không có lịch sử hội thoại trước đó."
            
            # 5. Gọi LLM sinh câu trả lời
            llm = get_llm(temperature=0.2)
            prompt_template = ChatPromptTemplate.from_template(ANSWER_PROMPT)
            chain = prompt_template | llm | StrOutputParser()
            
            try:
                answer = chain.invoke({
                    "context": context_str,
                    "chat_history": history_str,
                    "query": q_final
                })
            except Exception as e:
                print(f"[RAG System] Lỗi gọi LLM sinh câu trả lời: {e}")
                answer = f"Lỗi gọi LLM sinh câu trả lời: {e}"
                
        return {
            "answer": answer,
            "sources": sources,
            "original_query": prompt,
            "standalone_query": q_final,
            "keywords": keywords
        }
