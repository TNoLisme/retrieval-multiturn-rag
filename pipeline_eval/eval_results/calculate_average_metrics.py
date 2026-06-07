import os
import sys
import glob
import pandas as pd

if sys.platform.startswith('win'):
    os.system('chcp 65001 > nul')
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

def calculate_averages(results_dir):
    # Tìm tất cả các file excel eval (ngoại trừ file tổng hợp chung nếu có)
    excel_files = glob.glob(os.path.join(results_dir, "eval_conv_*.xlsx"))
    
    if not excel_files:
        print("Không tìm thấy file eval_conv_*.xlsx nào.")
        return

    summary_list = []

    for file in excel_files:
        df = pd.read_excel(file, sheet_name='Evaluation Results')
        if len(df) == 0:
            continue
            
        # Lấy row đầu tiên vì các cột Summary được gán cho mọi dòng
        first_row = df.iloc[0]
        
        summary_list.append({
            "File": os.path.basename(file),
            "Conversation": first_row.get("Summary_conversation_index", "N/A"),
            "Total QA": first_row.get("Summary_total_qa", 0),
            "BM25 Hits": first_row.get("Summary_bm25_hits", 0),
            "LLM Judge Passes": first_row.get("Summary_llm_judge_passes", 0),
            "BM25 Hit Rate": first_row.get("Summary_bm25_hit_rate", 0),
            "LLM Judge Accuracy": first_row.get("Summary_llm_judge_accuracy", 0)
        })

    if not summary_list:
        print("Không có dữ liệu hợp lệ trong các file Excel.")
        return

    # Chuyển thành DataFrame để tính toán
    df_summaries = pd.DataFrame(summary_list)
    
    # Tính tổng (Micro-average)
    global_total_qa = df_summaries["Total QA"].sum()
    global_bm25_hits = df_summaries["BM25 Hits"].sum()
    global_llm_passes = df_summaries["LLM Judge Passes"].sum()
    
    global_bm25_hit_rate = global_bm25_hits / global_total_qa if global_total_qa > 0 else 0
    global_llm_judge_accuracy = global_llm_passes / global_total_qa if global_total_qa > 0 else 0
    
    # Macro-average (Trung bình của các tỷ lệ)
    macro_bm25_hit_rate = df_summaries["BM25 Hit Rate"].mean()
    macro_llm_judge_accuracy = df_summaries["LLM Judge Accuracy"].mean()

    # Tạo nội dung báo cáo Markdown
    report_lines = []
    report_lines.append("# Báo cáo Tổng hợp Chỉ số Đánh giá (Evaluation Metrics)\n")
    
    report_lines.append("## 1. Kết quả Trung bình Toàn cục (Global Averages)\n")
    report_lines.append(f"- **Tổng số Samples (Conversations)**: {len(df_summaries)}")
    report_lines.append(f"- **Tổng số câu QA (Total QA)**: {global_total_qa}")
    report_lines.append(f"- **Tổng BM25 Hits**: {global_bm25_hits}")
    report_lines.append(f"- **Tổng LLM Judge Passes**: {global_llm_passes}")
    report_lines.append("")
    report_lines.append("| Metric | Macro-Average (Trung bình các Sample) | Micro-Average (Tổng thể) |")
    report_lines.append("|---|---|---|")
    report_lines.append(f"| **BM25 Hit Rate** | {macro_bm25_hit_rate:.2%} | {global_bm25_hit_rate:.2%} |")
    report_lines.append(f"| **LLM Judge Accuracy** | {macro_llm_judge_accuracy:.2%} | {global_llm_judge_accuracy:.2%} |")
    report_lines.append("\n*Ghi chú:*\n")
    report_lines.append("*- **Macro-Average**: Tính tỷ lệ cho từng Conversation, sau đó cộng lại chia đều.*")
    report_lines.append("*- **Micro-Average**: Tính tổng số câu đúng trên tổng số câu hỏi của toàn bộ tập dữ liệu.*")
    
    report_lines.append("\n## 2. Chi tiết từng Sample (Conversation)\n")
    report_lines.append("| File | Conv Index | Total QA | BM25 Hits | LLM Passes | BM25 Hit Rate | LLM Accuracy |")
    report_lines.append("|---|---|---|---|---|---|---|")
    
    for _, row in df_summaries.iterrows():
        report_lines.append(
            f"| {row['File']} | {row['Conversation']} | {row['Total QA']} | "
            f"{row['BM25 Hits']} | {row['LLM Judge Passes']} | "
            f"{row['BM25 Hit Rate']:.2%} | {row['LLM Judge Accuracy']:.2%} |"
        )

    report_content = "\n".join(report_lines)
    
    # In ra console
    print(report_content)
    
    # -------------------------------------------------------------
    # GHI RA EXCEL
    # -------------------------------------------------------------
    excel_report_path = os.path.join(results_dir, "overall_metrics_report.xlsx")
    writer = pd.ExcelWriter(excel_report_path, engine='openpyxl')
    
    # Sheet 1: Global Averages
    df_global = pd.DataFrame([{
        "Tổng số Samples": len(df_summaries),
        "Tổng số câu QA": global_total_qa,
        "Tổng BM25 Hits": global_bm25_hits,
        "Tổng LLM Passes": global_llm_passes,
        "Macro-Average BM25 Hit Rate": macro_bm25_hit_rate,
        "Macro-Average LLM Accuracy": macro_llm_judge_accuracy,
        "Micro-Average BM25 Hit Rate": global_bm25_hit_rate,
        "Micro-Average LLM Accuracy": global_llm_judge_accuracy
    }])
    df_global.to_excel(writer, sheet_name='Global Averages', index=False)
    
    # Sheet 2: Chi tiết từng Conversation
    # Đổi tên cột cho đẹp
    df_detail = df_summaries.rename(columns={
        "File": "Tên File",
        "Conversation": "Conv Index"
    })
    df_detail.to_excel(writer, sheet_name='Chi tiết từng Sample', index=False)
    
    # Tự động điều chỉnh độ rộng cột
    for sheet_name in writer.sheets:
        worksheet = writer.sheets[sheet_name]
        for col in worksheet.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min((max_length + 2), 50)
            worksheet.column_dimensions[column].width = adjusted_width
            
    writer.close()
    
    # Lưu ra file markdown (tùy chọn phụ)
    report_path = os.path.join(results_dir, "overall_metrics_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
        
    print(f"\n[OK] Đã lưu bảng tổng hợp Excel tại: {excel_report_path}")
    print(f"[OK] Đã lưu báo cáo markdown tại: {report_path}")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    calculate_averages(current_dir)
