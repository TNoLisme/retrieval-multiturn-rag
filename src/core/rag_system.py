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
        
    def run(self, prompt: str, chat_history: List[Dict[str, str]], session_id: str) -> Dict[str, Any]:
        """
        Chạy toàn bộ RAG pipeline:
        1. Gọi query rewriter pipeline sinh Q_final
        2. Dùng Q_final để query ChromaDB (vas_expert_db)
        3. Kết hợp Context + History + Q_final để LLM sinh câu trả lời cuối cùng có trích dẫn
        """
        # 1. Chạy query rewriter pipeline
        q_final = run_pipeline(prompt, session_id)
        
        # Lấy state mới cập nhật để trích xuất thực thể/từ khóa hiển thị lên UI
        current_state = load_state_from_redis(session_id) or ConversationState()
        keywords = list(current_state.entities.keys()) + list(current_state.attributes.keys())
        if not keywords:
            keywords = ["Kế toán VAS"]
            
        # Kiểm tra xem q_final có phải câu hỏi làm rõ không
        is_clarification = q_final.startswith("Hệ thống không tìm thấy") or q_final.startswith("Xin lỗi")
        
        sources = []
        answer = ""
        
        if is_clarification:
            # Nếu là câu hỏi làm rõ, trả về luôn làm câu trả lời chính
            answer = q_final
        else:
            # 2. Truy xuất tài liệu từ ChromaDB
            try:
                doc_results = query_vector_db(q_final, collection_name="vas_expert_db", top_k=3)
                for doc in doc_results:
                    sources.append({
                        "content": doc["content"],
                        "metadata": doc["metadata"]
                    })
            except Exception as e:
                print(f"[RAG System] Lỗi truy xuất vector DB: {e}")
                
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
