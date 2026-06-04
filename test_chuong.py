# -*- coding: utf-8 -*-
"""
Test case cụ thể từ user: câu hỏi "chúng" bị classify sai thành hard_shift
"""
import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.core.pipeline import run_pipeline

SESSION = "test-chuong-001"

def test(label, query):
    print("\n" + "="*60)
    print(f"TEST: {label}")
    print(f"Query: {query}")
    print("="*60)
    result = run_pipeline(query, SESSION)
    print(f"\n>>> Q_final: {result}\n")

# Turn 1: Câu hỏi rõ ràng
test("1 - Query rõ ràng", "hàng tồn kho là gì")

# Turn 2: Câu hỏi với "chúng" — PHẢI là CONTINUE (không phải hard_shift)
# Kỳ vọng: [LAYER 0] Phát hiện đại từ 'chúng' → CONTINUE ngay, không gọi SLM
test(
    "2 - Follow-up với đại từ 'chúng' (PHẢI là CONTINUE)",
    "Thế nếu chúng bị hư hỏng hoặc lỗi thời, dẫn đến giá trị giảm xuống thấp hơn giá gốc thì doanh nghiệp phải làm sao?"
)

# Turn 3: Tiếp tục hỏi sâu hơn
test("3 - Hỏi thêm về chủ đề", "phương pháp tính giá gốc của hàng tồn kho gồm những gì?")
