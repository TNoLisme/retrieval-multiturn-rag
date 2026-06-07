# Báo cáo Tổng hợp Chỉ số Đánh giá (Evaluation Metrics)

## 1. Kết quả Trung bình Toàn cục (Global Averages)

- **Tổng số Samples (Conversations)**: 2
- **Tổng số câu QA (Total QA)**: 304
- **Tổng số câu đúng (LLM Judge Passes)**: 188

| Metric | Macro-Average (Trung bình các Sample) | Micro-Average (Tổng thể) |
|---|---|---|
| **BM25 Hit Rate @1** | 68.52% | 67.80% |
| **BM25 Hit Rate @3** | 82.82% | 82.63% |
| **BM25 Hit Rate @5** | 88.96% | 88.39% |
| **LLM Judge Accuracy** | 65.45% | 61.84% |

*Ghi chú:*

*- **Macro-Average**: Tính tỷ lệ cho từng Conversation, sau đó cộng lại chia đều.*
*- **Micro-Average**: Tính tổng số câu đúng trên tổng số câu hỏi của toàn bộ tập dữ liệu.*

## 2. Chi tiết từng Sample (Conversation)

| File | Conv Index | Total QA | Hits@1 | Hits@3 | Hits@5 | LLM Passes | Hit Rate@1 | Hit Rate@3 | Hit Rate@5 | LLM Accuracy |
|---|---|---|---|---|---|---|---|---|---|---|
| eval_conv_0.xlsx | 0 | 199 | 131.8 | 163.5 | 173.5 | 107 | 66.25% | 82.16% | 87.20% | 53.77% |
| eval_conv_1.xlsx | 1 | 105 | 74.3 | 87.7 | 95.2 | 81 | 70.79% | 83.49% | 90.71% | 77.14% |