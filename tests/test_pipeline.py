import os
import json
import pandas as pd
import unittest
from main import run_pipeline, clear_session_cache
from src.core.state import SESSION_HISTORIES, save_history, save_state_to_redis
from src.core.schema import ConversationState

class TestMultiTurnRAGPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = "d:/school/Các vấn đề/retrieval-multiturn-rag"
        cls.dataset_path = os.path.join(cls.project_root, "data", "test_dataset.xlsx")
        
        if not os.path.exists(cls.dataset_path):
            raise FileNotFoundError(f"Không tìm thấy file dataset kiểm thử tại: {cls.dataset_path}")
            
        cls.df = pd.read_excel(cls.dataset_path)
        cls.results = []

    def test_run_all_dataset_cases(self):
        print(f"\n===== BẮT ĐẦU ĐÁNH GIÁ PIPELINE TRÊN {len(self.df)} CÂU HỎI KIỂM THỬ =====")
        
        correct_rewrites = 0
        
        for idx, row in self.df.iterrows():
            case_id = row['ID']
            session_id = f"test_session_{case_id}"
            q_type = row['Type']
            raw_question = row['Question']
            history_json = row['History']
            gt_query = row['Ground_Truth_Query']
            gt_metadata = row['Ground_Truth_Metadata']
            
            print(f"\n[Test Case {case_id}] Type: {q_type} | Question: '{raw_question}'")
            clear_session_cache(session_id)
            
            # Giả lập lịch sử hội thoại từ dataset để dựng trạng thái
            if pd.notna(history_json) and history_json.strip():
                try:
                    history_turns = json.loads(history_json)
                    # Chạy lần lượt các lượt cũ qua pipeline để sinh state tự nhiên nhất
                    # hoặc nạp trực tiếp lịch sử thô vào cache để node boundary và tracker đọc trực tiếp.
                    # Ở đây ta nạp trực tiếp lịch sử trò chuyện chuẩn của dataset vào cache
                    SESSION_HISTORIES[session_id] = history_turns
                    
                    # Đồng thời dựng sơ bộ state cũ bằng cách chạy state tracker trên câu user cuối cùng trong history
                    # để đảm bảo state có chứa một số thực thể cũ trước khi chạy câu hỏi hiện tại.
                    user_turns = [t for t in history_turns if t["role"] == "user"]
                    if user_turns:
                        temp_state = ConversationState()
                        from src.nodes.tracker import state_tracker_node
                        for ut in user_turns:
                            tracker_out = state_tracker_node(ut["content"], temp_state)
                            temp_state = tracker_out.state
                        save_state_to_redis(session_id, temp_state)
                        
                except Exception as e:
                    print(f"  ⚠️ Lỗi khi dựng lịch sử kiểm thử: {e}")
            
            # Chạy câu hỏi hiện tại qua pipeline
            try:
                q_final = run_pipeline(raw_question, session_id)
            except Exception as e:
                print(f"  ❌ Lỗi khi chạy pipeline: {e}")
                q_final = f"ERROR: {e}"
            
            # Đánh giá độ chính xác (So sánh từ khóa chính/độ dài tương đồng)
            # Vì LLM có thể diễn đạt khác một chút so với Ground Truth, ta đánh giá qua mức độ trùng lặp từ khóa
            words_gt = set(gt_query.lower().replace("?", "").split())
            words_generated = set(q_final.lower().replace("?", "").split())
            
            # Loại bỏ một số hư từ phổ biến
            stopwords = {"về", "trong", "của", "là", "và", "các", "những", "cho", "có", "sao", "thế", "nào", "gì", "được", "kế", "toán", "vas"}
            words_gt_clean = words_gt - stopwords
            words_generated_clean = words_generated - stopwords
            
            overlap = words_gt_clean.intersection(words_generated_clean)
            keyword_accuracy = len(overlap) / len(words_gt_clean) if words_gt_clean else 1.0
            
            # Nếu trùng khớp > 50% từ khóa chính, coi như đạt yêu cầu tối ưu hóa ngữ cảnh
            is_passed = keyword_accuracy >= 0.50
            if is_passed:
                correct_rewrites += 1
                status = "PASSED"
            else:
                status = "FAILED"
                
            print(f"  Ground Truth: '{gt_query}'")
            print(f"  Generated   : '{q_final}'")
            print(f"  Độ khớp từ khóa chính: {keyword_accuracy*100:.1f}% ➔ Kết quả: {status}")
            
            self.results.append({
                "ID": case_id,
                "Type": q_type,
                "Question": raw_question,
                "Ground_Truth_Query": gt_query,
                "Generated_Query": q_final,
                "Keyword_Overlap_Pct": keyword_accuracy * 100,
                "Status": status,
                "Metadata": gt_metadata
            })
            
        success_rate = (correct_rewrites / len(self.df)) * 100
        print(f"\n==========================================")
        print(f" ĐÁNH GIÁ HOÀN TẤT: Tỷ lệ viết lại đạt chuẩn: {success_rate:.2f}% ({correct_rewrites}/{len(self.df)})")
        print(f"==========================================")
        
        # Xuất kết quả đánh giá ra file Excel để người dùng xem
        df_results = pd.DataFrame(self.results)
        output_excel = os.path.join(self.project_root, "data", "evaluation_results.xlsx")
        df_results.to_excel(output_excel, index=False)
        print(f"📊 Đã xuất báo cáo đánh giá chi tiết ra file Excel: {output_excel}")

if __name__ == "__main__":
    unittest.main()
