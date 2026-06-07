# Báo cáo Tổng hợp Chỉ số Đánh giá (Evaluation Metrics)

## 1. Kết quả Trung bình Toàn cục (Global Averages)

- **Tổng số Samples (Conversations)**: 2
- **Tổng số câu QA (Total QA)**: 304
- **Tổng BM25 Hits**: 0
- **Tổng LLM Judge Passes**: 188

| Metric | Macro-Average (Trung bình các Sample) | Micro-Average (Tổng thể) |
|---|---|---|
| **BM25 Hit Rate** | 0.00% | 0.00% |
| **LLM Judge Accuracy** | 65.45% | 61.84% |

*Ghi chú:*

*- **Macro-Average**: Tính tỷ lệ cho từng Conversation, sau đó cộng lại chia đều.*
*- **Micro-Average**: Tính tổng số câu đúng trên tổng số câu hỏi của toàn bộ tập dữ liệu.*

## 2. Chi tiết từng Sample (Conversation)

| File | Conv Index | Total QA | BM25 Hits | LLM Passes | BM25 Hit Rate | LLM Accuracy |
|---|---|---|---|---|---|---|
| eval_conv_0.xlsx | 0 | 199 | 0 | 107 | 0.00% | 53.77% |
| eval_conv_1.xlsx | 1 | 105 | 0 | 81 | 0.00% | 77.14% |