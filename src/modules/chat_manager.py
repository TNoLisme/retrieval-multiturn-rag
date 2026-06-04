import os
import json
from typing import List, Dict, Any
from datetime import datetime

class ChatManager:
    def __init__(self, storage_dir="data/chat_history"):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)
        
    def _get_file_path(self, chat_id: str) -> str:
        return os.path.join(self.storage_dir, f"{chat_id}.json")
        
    def list_chats(self) -> List[Dict[str, Any]]:
        """
        Liệt kê danh sách các cuộc hội thoại cũ đã lưu.
        """
        chats = []
        if not os.path.exists(self.storage_dir):
            return chats
            
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json"):
                chat_id = filename[:-5]
                file_path = self._get_file_path(chat_id)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    # Lấy tiêu đề từ câu hỏi đầu tiên của người dùng
                    title = "Cuộc trò chuyện mới"
                    messages = data.get("messages", [])
                    if messages:
                        for msg in messages:
                            if msg["role"] == "user":
                                title = msg["content"][:25] + ("..." if len(msg["content"]) > 25 else "")
                                break
                                
                    chats.append({
                        "id": chat_id,
                        "title": title,
                        "timestamp": data.get("timestamp", ""),
                        "mode": data.get("mode", "Local RAG")
                    })
                except Exception as e:
                    print(f"[ChatManager] Lỗi đọc metadata của file {filename}: {e}")
                    
        # Sắp xếp cuộc trò chuyện theo thời gian mới nhất lên trên
        chats.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return chats
        
    def load_chat(self, chat_id: str) -> Dict[str, Any]:
        """
        Tải nội dung chi tiết của một cuộc trò chuyện từ file JSON.
        """
        file_path = self._get_file_path(chat_id)
        if not os.path.exists(file_path):
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[ChatManager] Lỗi đọc cuộc trò chuyện {chat_id}: {e}")
            return None
            
    def save_chat(self, chat_id: str, messages: List[Dict[str, Any]], mode: str):
        """
        Lưu trữ cuộc trò chuyện hiện tại.
        """
        file_path = self._get_file_path(chat_id)
        data = {
            "session_id": chat_id,
            "messages": messages,
            "mode": mode,
            "timestamp": datetime.now().isoformat()
        }
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ChatManager] Lỗi lưu cuộc trò chuyện {chat_id}: {e}")
            
    def delete_chat(self, chat_id: str):
        """
        Xóa cuộc trò chuyện khỏi ổ cứng.
        """
        file_path = self._get_file_path(chat_id)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"[ChatManager] Đã xóa cuộc trò chuyện: {chat_id}")
            except Exception as e:
                print(f"[ChatManager] Lỗi xóa cuộc trò chuyện {chat_id}: {e}")
